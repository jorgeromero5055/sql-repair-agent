# Map — what exists and how it connects

Four lists. **This is the file to re-read.** Not the code.

---

## 1. How the whole thing is meant to work

The finished story, whether or not it's built yet.

1. You paste a broken SQL query and say what it was supposed to do.
2. You get a job id back straight away. Closing the tab loses nothing.
3. An agent looks at the query, runs it against a copy of the database it can't damage, and works
   out what's wrong. No error message is handed to it — it finds the failure itself.
4. A verifier checks the agent's answer. If it fails, the reason goes back to the agent and it
   tries again, up to three times.
5. You open the finished job, see what changed, see the rows it returns, see what it tried.
6. You approve it — it runs for real and is saved — or you reject it with a reason.
7. Separately, an evaluation runs the agent over a set of known-broken queries and reports how
   often it's right, how many attempts it takes, and what it costs.
8. The whole thing is documented well enough that someone who wasn't here can follow it.

## 2. What's built

- Steps 1 and 2 — submit, queue, statuses, one trace row per run. *(v1)*
- Steps 3 and 4 — the agent, the read-only sandbox, the verifier, the retry loop. *(v2)*
- Steps 5 and 6 — the review screen, approve, reject. *(v3, deployed)*
- Step 7 — the eval: 20 reference queries, 66 generated cases, the runner, the Runs page. *(v4)*

## 3. The version we're in

**v3 — review and approve. Done and deployed.**

**v3.5 — clean up before the eval. Done.** Three things that either get worse with time or would
corrupt what v4 measures.

| Deliverable | What it's for |
|---|---|
| Tests clean up after themselves | Stops the database filling with junk repairs before v4 starts creating them in bulk. |
| Tell an unreachable database apart from a bad query | The verifier currently feeds connection errors back to the model, which can't fix them. In v4 every blip would count as the agent failing. |
| A styling pass | The app is still on the Vite starter CSS. Doing it before v4 means the Runs page gets built into a styled app rather than restyled after. |

**v4 — evaluate the agent. Done. First run: 66 cases, pass@1 97%, $0.0155 at paid rates.** Its story: before trusting the next diff, know how
often the agent is right first try, how often it gets there after repairing, and what it costs.

What each part of v4 will be for — so when you're mid-build and wondering why you're making
something, it's here:

| Deliverable | What it's for |
|---|---|
| ~20 reference queries | The known-correct answers. Everything else is measured against these. |
| A corruption generator, 5 break types | Turns each correct query into broken ones automatically, so no case is hand-labelled. |
| The eval runner | Runs the agent over every generated case, with a cap on spend. |
| The oracle | Decides pass or fail by comparing result sets, never query text. |
| The Runs page | Shows pass rate, attempts, latency and cost. |
| A slice in CI | Fails a pull request visibly when accuracy drops. |

**v5 — write it up. ← here.** README, the decisions written up properly, a data-flow and failure trace.

## 4. Open gaps

Things that don't work. The second column is whether that's expected and what changes it, so you
can tell "I broke something" from "this was always going to be like this."

| What you'll see | Why, and when it changes |
|---|---|
| A job submitted **locally** sits at `queued` and never moves. | Expected. No worker runs locally — the message goes to the real AWS queue and the deployed worker can't see your local database. Trigger it yourself with `POST /events` and the repair id. Not assigned to a deliverable. |
| A job sits at `queued` forever **in production**. | A gap. The worker crashed three times and the message parked in the dead-letter queue, but nothing sets the row to `failed`. Not assigned — small, and `failed` already exists for it. |
| The local queue fills with repairs called "count the customers". | A gap. The tests insert them and never clean up. **Assigned: v3.5 d1.** |
| Repairs stop working partway through a session. | Expected. The Gemini free tier is about 20 requests a day and one repair costs 5 to 24. Unsolved, and it blocks v4, which needs over a thousand calls. |
| The agent burns all three attempts on a query that was fine. | A gap. The verifier can't tell "your query is wrong" from "the database is unreachable", so it feeds an infrastructure error back to the model, which can't fix it. Found in production on v3's first live run. **Assigned: v3.5 d2.** |
| A prompt change makes the agent worse. | Caught, but only if `GEMINI_API_KEY` is added to the repository secrets — the eval slice can't run without it. |
| A broken change reaches production. | Expected. Tests run on the pull request, deploy runs on push to main — nothing gates one on the other except you merging a green PR. It's a branch protection setting, not code. |

---

## The two logins

- **`agent_ro`** — can only read, only in the `sandbox` schema. Everything the agent does uses it.
- **The app login** — unrestricted. Used for repairs, traces, and (from v3) running an approved
  query.

The agent cannot write. That is enforced by the login, not by the prompt.

## The statuses

`queued` → `running` → `needs_review` → `approved` or `rejected`.
`failed` is the end of the line: three attempts, none passed.

## The tables

- **`repairs`** — the job: intent, broken query, fixed query, explanation, status, rejection reason.
- **`traces`** — one row per run: attempts, turns, tokens, every SQL statement, latency, why it failed.
  Returned by `GET /repairs/{id}` since v3 d4.
- **`saved_queries`** — one row per approved query, with the rows it returned. *(v3)*
- **`sandbox.*`** — fake store data: customers, products, orders, order_items. The only thing the
  agent can see.

## Where the code lives

- `app/main.py` — the endpoints. Thin: find the thing, hand it over, translate the answer.
- `app/worker.py` — what runs when a queue message arrives.
- `app/repair.py` — the retry loop.
- `app/agent/` — the model conversation and the `run_sql` tool.
- `app/verifier.py` — does this query run. Used in the repair loop.
- `app/sandbox.py` — the two logins, side by side.
- `app/evaluation/` — the eval. `cases.py` the 20 correct queries, `corrupt.py` breaks them into 66 cases, `oracle.py` decides pass or fail, `runner.py` drives all 66 cases, `stats.py` turns results into numbers. *(v4)*
- `app/approval.py` — the review gate: `approve` runs and saves, `reject` records why. *(v3)*
- `app/review.py` — reads only: regroups the attempts, previews the rows. *(v3)*
- `app/db/models.py` — the tables as Python.
- `web/src/App.tsx` — the queue, the submit form, the routes.
- `web/src/Repair.tsx` — the review screen: diff, rows, attempts, approve and reject. *(v3)*
- `web/src/Runs.tsx` — the eval results: pass rates per run, broken down by kind of bug. *(v4)*

## Where it runs

- Locally: Postgres in Docker, API on your machine.
- Deployed: two Lambdas from one image (API and worker), Neon for the database, CloudFront for the
  page. Terraform builds it; GitHub Actions deploys it.

---
