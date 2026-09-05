import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED = (
    "DATABASE_URL",
    "AGENT_DATABASE_URL",
    "QUEUE_URL",
    "GEMINI_API_KEY",
)


def _check() -> None:
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Set them in api/.env locally, in infra/terraform.tfvars for "
            + "deployment, and in .github/workflows/test.yml for CI."
        )


_check()

DATABASE_URL = os.environ["DATABASE_URL"]
AGENT_DATABASE_URL = os.environ["AGENT_DATABASE_URL"]
QUEUE_URL = os.environ["QUEUE_URL"]

# Local only. When this is on, POST /repairs runs the worker in the background instead of
# sending to SQS — the deployed worker reads Neon and would never find a local repair.
# It is not a queue: nothing survives a restart and nothing is retried.
RUN_WORKER_LOCALLY = os.environ.get("RUN_WORKER_LOCALLY", "").lower() == "true"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]