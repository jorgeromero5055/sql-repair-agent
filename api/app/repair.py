from app.agent.loop import repair as run_agent
from app.verifier import check

MAX_ATTEMPTS = 3


def repair_with_retries(intent: str, broken_query: str) -> dict:
    """Run the agent, verify its answer, retry with feedback if it fails."""
    feedback = None
    attempts = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = run_agent(intent, broken_query, feedback=feedback)

        if result["fixed_query"]:
            verdict = check(result["fixed_query"])
        else:
            verdict = {"passed": False, "reason": "The agent produced no query."}

        attempts.append(
            {
                "attempt": attempt,
                "turns": result["turns"],
                "tokens": result["tokens"],
                "statements": result["statements"],
                "passed": verdict["passed"],
                "reason": verdict["reason"],
            }
        )

        if verdict["passed"]:
            return {
                "passed": True,
                "fixed_query": result["fixed_query"],
                "explanation": result["explanation"],
                "attempts": attempts,
            }

        feedback = verdict["reason"]

    return {
        "passed": False,
        "fixed_query": result["fixed_query"],
        "explanation": result["explanation"],
        "attempts": attempts,
    }