# How a repair moves, and how it breaks

Two halves: the path a successful repair takes, and every way that path fails.

---

# The success path

## 1. You submit

A broken query and a sentence saying what it was supposed to do.

`POST /repairs` checks both against a length limit and rejects anything empty. Nothing else is
validated — the query is meant to be broken.

**Written:** one row in `repairs`, status `queued`.

## 2. The API replies immediately

It puts a message on the queue carrying only the repair's id, and returns. However long the work
takes, this request doesn't wait for it.

Locally there is no queue. With `RUN_WORKER_LOCALLY=true` the API runs the worker itself, after the
response has been sent.

**Written:** nothing further.

## 3. The worker picks it up

SQS wakes the worker Lambda. It loads the repair by id.

**Written:** status → `running`.

## 4. The agent looks at the problem

It gets the intent and the broken query. **It is never given an error message** — finding the
failure is its job.

It has one tool, `run_sql`, which runs a query against the `sandbox` schema through the `agent_ro`
login. That login can only read, and only there. Up to 8 turns.

**Written:** nothing yet. Every statement is held in memory for the trace.

## 5. The verifier checks the answer

The agent hands back a fixed query and an explanation. The verifier runs it and asks one question:
does it run?

It does not ask whether the answer is right. Nothing in production can — there is no correct query
to compare against. Only the eval has one.

## 6. It retries, or it stops

If the query didn't run, the reason goes back into the conversation and the agent tries again. Up
to 3 attempts. Each attempt starts a fresh conversation carrying only the feedback.

**Written:** on the way out — the fixed query, the explanation, the status, and one `traces` row
holding attempts, turns, tokens, latency, and every statement the agent ran in order.

Status → `needs_review` if the query runs, `failed` if three attempts didn't produce one.

## 7. The queue page notices

It polls every 3 seconds while anything is `queued` or `running`, and stops when nothing is.

## 8. You open it

`GET /repairs/{id}` returns the repair, the trace, the attempts regrouped one entry per attempt,
and a preview: the rows the fixed query returns **right now**, read through `agent_ro`.

The preview is worked out on every request and never stored. What you approve has to be what you
saw.

## 9. You decide

**Approve.** The repair must be in `needs_review`. The query runs again — this time through the
app's login, not the agent's — and the rows it returned are saved with it.

**Written:** one row in `saved_queries` with the query and its rows, status → `approved`. Both in
one commit, so there can never be one without the other.

**Reject.** A reason is required, and enforced twice: on the request, and again inside the
function for anything that skips the web.

**Written:** the reason and status → `rejected` on the repair. Nothing in `saved_queries`.

---

# Where the data lives

| Table | One row per | Written by |
|---|---|---|
| `repairs` | job | the API on submit, the worker on finish, the gate on decision |
| `traces` | run | the worker, once, on the way out — even when it failed |
| `saved_queries` | approved query | the approval gate only |
| `eval_runs` | eval run | the eval runner |
| `eval_results` | case in a run | the eval runner |
| `sandbox.*` | fake store data | migrations. The only thing the agent can see. |

---

# How it breaks

| What you'd see | What happened | What the system does |
|---|---|---|
| `422` on submit | Empty intent or query, or over the length limit | Rejected at the boundary. Nothing written. |
| Status `failed`, trace shows 3 attempts | The agent's query never ran. Each failure was fed back and it tried again. | Expected. The trace shows every statement it tried and why each attempt failed. |
| Status `failed`, trace shows 1 attempt and a connection error | The database was unreachable | The sandbox raises rather than returning a failure, so the loop stops immediately instead of asking the model to fix a connection string. |
| A repair marked `needs_review` whose query is subtly wrong | The query runs, so the verifier passed it | **Not caught, by design.** In production there is no correct query to compare against. That's what the human review step is for, and what the eval measures offline. |
| Status `failed` with no trace detail | The worker raised on its third delivery | The worker sets `failed` before re-raising, so the row and the queue agree. |
| Status stuck at `running` forever | The worker was killed without raising — a Lambda timeout, or out of memory | **Not handled.** See limitations. |
| A repair that never appears | The message named an id the worker couldn't find | Logged and dropped. Usually means a locally created repair reached the deployed worker, which reads a different database. |
| `404` on approve or reject | No repair with that id | Nothing written. |
| `409` on approve or reject | The repair isn't in `needs_review` — already decided, still running, or failed | Nothing written. The screen shows the server's own message. |
| `409` on approve saying the query no longer runs | It passed the verifier earlier, but the data moved | Nothing written. Verified again at the moment of approval, on purpose. |
| Repairs stop working mid-session | The model's free tier is exhausted — about 20 requests a day | The request fails and the worker retries via the queue. Nothing recovers this but waiting. |

---

# Known limitations

**A hard Lambda kill leaves the row at `running`.** The worker marks a repair `failed` on its third
failed delivery — but only when Python raises. A timeout or an out-of-memory kills the process
before that runs. The message still reaches the dead-letter queue, so nothing is lost, but the
database keeps saying `running`. Fixing it means a second Lambda triggered by the dead-letter queue
whose only job is to mark those rows. Not built: it needs a timeout or an out-of-memory to happen.

**A query that runs but is wrong is not detected in production.** There is no reference query to
compare against — if there were, you wouldn't need the agent. The approval gate exists precisely
because this can't be automated.

**Retries only rescue queries that fail to run.** The retry loop is driven by the verifier, and the
verifier only asks whether the query executes. A query that runs and returns wrong rows ends the
loop as a success. In the first full eval run this is why pass@1 and pass@3 are the same number.

**The local worker is not a queue.** With `RUN_WORKER_LOCALLY=true` the work runs in the API
process after the response is sent. It dies with the server and never retries — which is exactly
what SQS is buying in production.

**Writes are out of scope.** `INSERT`, `UPDATE` and `DELETE` are not repaired. See decision 1.
