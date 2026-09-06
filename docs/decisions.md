# Decisions

Why this project is built the way it is.

Each record says what was chosen, why, what the alternatives were, what the choice costs, and when
it would be worth revisiting. They were written when the decisions were made, not reconstructed
afterwards.

Nothing here is deleted. A decision that stops being true gets a **Superseded** status and a
pointer to whatever replaced it.

---

## 1. The agent repairs SELECT queries only

**Status:** accepted · v2

**Chosen.** No `INSERT`, `UPDATE` or `DELETE`. Read queries only.

**Why.** The verifier decides "is this fixed?" by comparing the rows a query returns. That only
means anything for queries that return rows. The read-only sandbox connection follows from the same
choice.

**The alternative.** Support writes, by running the repaired statement inside a transaction and
rolling it back. Rejected because it's a different design rather than an extension of this one —
the verifier would need to compare side effects instead of results.

**What it costs.** A whole category of broken SQL is out of scope. The README says so rather than
overclaiming.

**Revisit when.** Never, in this project.

---

## 2. Approving runs the query under a second database login

**Status:** accepted · v3

**Chosen.** Approving executes the same query against the same tables, but through the app's own
login rather than the agent's read-only one, and stores the rows it returned.

**Why.** There is one database here, so "runs it for real" has to mean something. It means a
restricted identity wrote the query and an unrestricted one ran it, only after a human said yes.
The privilege boundary is between logins, not between databases.

**The alternatives.** Save the query without executing it — rejected, because it deletes the only
moment the boundary is crossed and the gate stops guarding anything. Or stand up a second
"production" schema — rejected as a migration and a seed script for a distinction one sentence can
make.

**What it costs.** The rows come back identical either way, so the difference is the boundary being
crossed, not the output.

**Revisit when.** A real production database exists — at which point it's a different URL, not a
different design.

---

## 3. Two functions, not one function with a privilege argument

**Status:** accepted · v3

**Chosen.** `run_sql` keeps the agent's read-only login and is untouched. A separate
`run_sql_as_app` opens the app's login, and only the approval gate imports it.

**Why.** With one function the privilege level is an argument decided at runtime — and the agent's
loop already calls that exact function. One wrong argument from full access. Two functions means
the agent was never handed the second one.

**The alternative.** `run_sql(sql, as_app=True)`. Rejected for the reason above: it makes a
structural guarantee into a runtime one.

**What it costs.** A little duplication between the two.

**Revisit when.** Never for this shape.

---

## 4. A renamed output column counts as wrong

**Status:** accepted · v4

**Chosen.** The oracle compares column names as well as values. A query returning the right rows
under different headings fails.

**Why.** The promise is a drop-in replacement for the broken query. Something downstream reads
`status`; a query returning it as `state` breaks that, so it isn't a fix.

**The alternative.** Compare values only. Rejected because it would score a query that can't
actually be swapped in.

**What it costs.** Both failures in the first full eval run are exactly this — the agent found the
right column and kept the broken name as an alias. Under the looser rule the headline number would
be 100% instead of 97%.

**Revisit when.** Never for this project.

---

## 5. The eval calls the agent directly, not through the queue

**Status:** accepted · v4

**Chosen.** The eval runner calls the repair loop in process. No SQS, no Lambda.

**Why.** The eval measures the agent's accuracy. Putting the queue in the path adds hundreds of
Lambda invocations and polling waits, and turns every infrastructure hiccup into a wrong answer.

**The alternative.** Run every case through the real pipeline. Rejected because it tests more and
measures worse.

**What it costs.** The eval doesn't exercise the production path. Using the app covers that.

**Revisit when.** Never for accuracy. Load testing would be a different tool.

---

## 6. Infrastructure is applied by hand; only app deploys are automated

**Status:** accepted · v0

**Chosen.** `terraform apply` runs from a laptop. The pipeline only builds the image, runs
migrations and updates the Lambdas.

**Why.** Infrastructure changes are rare and can delete a database. App deploys are frequent and
their worst case is bad code.

**The alternative.** Terraform in the pipeline. Rejected because the blast radius of an automated
mistake is the whole environment.

**What it costs.** A human has to remember to apply infrastructure changes.

**Revisit when.** More than one person needs to change infrastructure.

---

## 7. GitHub authenticates by OIDC, not stored access keys

**Status:** accepted · v0

**Chosen.** A trust relationship between GitHub and AWS, issuing short-lived tokens per run.

**Why.** The repo is public and a stored access key is permanent. A leaked OIDC token expired
minutes ago.

**The alternative.** An access key in repository secrets. Rejected — that's the thing OIDC exists
to replace.

**What it costs.** About twenty minutes of setup and one more IAM concept to hold.

**Revisit when.** Never.

---

# Course corrections

Decisions that went to plan are easy to write down. These are the ones that didn't.

## Two free tiers ran out in one day

Gemini's free tier caps at about twenty requests a day — roughly three agent runs. Hours later Neon
refused all connections: the data transfer quota was gone, because every local test and script had
been querying the cloud database over the internet since v1.

The database half was fixed by pointing local development at the Postgres container that had been
sitting unused in `compose.yml` since v0. Neon now serves the deployed Lambdas only.

The thing that made that fix cheap: not one line of application code changed. Configuration came
from the environment and schema came from migrations, both decided in v1, so an entire database was
rebuilt from files — including the read-only role — by editing one file.

The model half is still open. It's why the eval is 66 cases and not a thousand.

## A constraint that was asserted and never checked

The build stalled on the claim that Gemini can't combine structured output with tool calling in one
request. Two workarounds were designed around it. Both were wrong: a thirty-second test proved the
two work together fine.

The cost was a day and two reverted designs. The rule that came out of it — run the smallest check
before designing around a limitation — is the one that later found the `channel_binding=requiree`
typo in production, in about a minute.

## One image couldn't call a Python function

The worker Lambda was configured to run `app.worker.handler` directly and failed with
`Runtime.InvalidEntrypoint` on every message. The image uses the AWS Lambda Web Adapter, which only
speaks HTTP — it has no way to invoke a Python function.

The worker now runs the same uvicorn command as the API, and the adapter forwards queue events to a
`POST /events` route. The alternative was a second image on AWS's Lambda base, which would have been
cleaner at runtime but discarded the one-image decision and doubled the build.

Accepted knowingly. The worker boots the whole app and holds configuration it never uses.
