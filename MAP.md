# Map — what exists and how it connects

Plain English, one line per piece. **This is the file to re-read.** Not the code.

Updated at the end of every deliverable. If something isn't here, it doesn't exist yet.

---

## The path a repair takes

1. You paste a broken query and what it was meant to do → **Submit page**.
2. **`POST /repairs`** writes a row, puts a message on the queue, and answers immediately.
3. The **queue** holds the message until a worker picks it up.
4. The **worker** loads the repair and runs the repair loop.
5. The **repair loop** asks the agent for a fix, checks it, and retries up to 3 times with the
   failure fed back in.
   - The **agent** talks to Gemini. It can call one tool, `run_sql`, to look at the database.
   - The **verifier** decides pass or fail. The agent never grades itself.
6. The worker saves the result, writes **one trace row**, and sets the status.
7. The **Queue page** polls every 3 seconds and the status flips on its own.

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
- `app/verifier.py` — pass or fail, as a pure function.
- `app/sandbox.py` — the two logins, side by side.
- `app/approval.py` — the review gate: `approve` runs and saves, `reject` records why. *(v3)*
- `app/review.py` — reads only: regroups the attempts, previews the rows. *(v3)*
- `app/db/models.py` — the tables as Python.
- `web/src/App.tsx` — the queue, the submit form, the routes.
- `web/src/Repair.tsx` — the review screen: diff, rows, attempts, approve and reject. *(v3)*

## Where it runs

- Locally: Postgres in Docker, API on your machine.
- Deployed: two Lambdas from one image (API and worker), Neon for the database, CloudFront for the
  page. Terraform builds it; GitHub Actions deploys it.

---

## Not built yet

- Everything in v4: the eval, the Runs page
