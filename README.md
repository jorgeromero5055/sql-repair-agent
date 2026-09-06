# SQL Repair Agent

**[Live demo](https://d2ikqw86csxqqd.cloudfront.net/)**

Paste a broken SQL query and what it was supposed to do. An agent finds the bug by running the
query itself, fixes it, and checks its own work. You review the diff and the rows it returns, then
approve or reject. Nothing reaches the database without a human saying yes.

## How good is it

Measured over **66 broken queries with known-correct answers**, generated automatically:

| | |
|---|---|
| Correct first try (pass@1) | **97%** |
| Correct within 3 attempts (pass@3) | **97%** |
| Cost | $0.0155 for the full run |
| Model | `gemini-3.5-flash-lite` |

Both failures were the same thing: the agent found the right column and then kept the broken
query's name as an alias — `SELECT status AS state`. Right rows, wrong heading. The oracle counts
that as wrong, because a repaired query that renames its output isn't a drop-in replacement.

Two things that number doesn't say. **39 of the 66 cases are a wrong table or column name** — the
kind you catch by running the query once — so the case mix flatters it. And **pass@1 and pass@3 are
identical because nothing ever retried**: the retry loop is driven by whether the query *runs*, and
both failures ran fine. Retries can rescue a query that breaks, never one that's quietly wrong.

The Runs page shows the same number split by kind of bug, which is the version worth acting on.

## What it does

1. You paste a broken query and a sentence describing what it should return.
2. You get a job id straight away. Closing the tab loses nothing.
3. An agent inspects the database and works out what's wrong. **It is never given the error
   message** — finding the failure is the job.
4. A verifier runs the agent's answer. If it fails, the reason goes back and the agent tries again,
   up to three times.
5. You open the finished job: the diff, the rows it returns now, and every SQL statement it tried.
6. Approve and it runs for real and is saved. Reject and it records why, and writes nothing.

## How it works

```
React ──▶ FastAPI ──▶ SQS ──▶ worker Lambda ──▶ Gemini
                │                    │              │
                │                    │              └── run_sql, read-only login
                ▼                    ▼
            Postgres            verifier: does it run?
                                     │
                                     └── retry with the failure, up to 3
```

**Two database logins, and that's the security model.** The agent uses `agent_ro`, which can only
`SELECT`, and only in the `sandbox` schema. It cannot write, regardless of what it produces —
enforced by the login, not by the prompt. Approving runs the same query through the app's own
login. That's the only place an unrestricted connection is opened, and reaching it requires an
approved repair.

**The agent doesn't grade its own work.** A separate verifier decides pass or fail. In the eval, a
separate oracle compares result sets against the original query — which the agent never sees.

**Work outlives the request.** Submitting returns immediately and the repair happens in a worker
behind a queue, with a dead-letter queue for messages that fail three times.

## Running it locally

Requires Docker, [uv](https://docs.astral.sh/uv/), and Node 20+.

```bash
docker compose up -d db adminer
```

```bash
cd api && cp .env.example .env   # then add your GEMINI_API_KEY
```

```bash
cd api && uv sync && uv run alembic upgrade head
```

```bash
cd api && uv run uvicorn app.main:app --reload
```

```bash
cd web && npm install && npm run dev
```

Set `RUN_WORKER_LOCALLY=true` in `api/.env` — locally there's no queue, so the API runs the worker
itself after replying. It isn't a queue: it dies with the server and never retries, which is
exactly what SQS is buying in production.

The database viewer is at `localhost:8080` — server `db`, user and password `postgres`, database
`sqlrepair`.

**The tests** cover the read-only login, the approval gate, the verifier, the case generator and
the oracle:

```bash
cd api && uv run pytest
```

**The eval** takes about half an hour and around 230 model requests. It paces itself under the free
tier's limit, stops at a request budget, and can be resumed:

```bash
cd api && uv run python -m app.evaluation.runner --note "a run"
```

## Stack

Python · FastAPI · SQLAlchemy · Alembic · React · TypeScript · Vite · Postgres · Docker ·
Terraform · AWS Lambda, SQS, S3, CloudFront · GitHub Actions · Gemini

Deployed as two Lambdas from one image, with Neon for the database and CloudFront for the page.
Terraform builds the infrastructure; GitHub Actions runs the tests on every pull request and
deploys on merge.

**Deliberately not chosen.** Kubernetes, a vector database, a framework like LangChain. The agent
loop is about eighty lines and reads more clearly than a framework's abstraction over it.

**Cost.** It runs at $0 — free tiers throughout, plus a few cents of S3 and CloudFront. The eval's
$0.0155 is what the tokens would cost at paid rates, not what was spent.

## What it doesn't do

- **`SELECT` queries only.** No `INSERT`, `UPDATE` or `DELETE`. The verifier decides "is this
  fixed?" by comparing returned rows, which only means anything for reads.
- **It can't tell you a query is wrong in production**, only that it runs. There's no correct query
  to compare against — if there were, you wouldn't need the agent. That's why the approval step
  exists.
- **A hard Lambda kill leaves a job showing `running`.** The message reaches the dead-letter queue,
  so nothing is lost, but nothing marks the row failed.
- **The free tier is about 20 model requests a day**, which is why the eval is 66 cases and not a
  thousand — and why the live demo may run out of quota. Everything else on it still works; the
  queue, an existing repair, the review screen and the eval results are all there to look at.

## More

- [Decisions](docs/decisions.md) — why it's built this way, and the three things that went wrong.
- [How a repair moves, and how it breaks](docs/trace.md) — the data flow and every failure mode.
