from app.db.models import Repair, RepairStatus, Trace
from app.review import group_attempts, preview_rows


def test_group_attempts_nests_the_flat_statements():
    trace = Trace(
        statements=[
            {"attempt": 1, "attempt_passed": False, "attempt_reason": "no rows",
             "sql": "select 1", "ok": True},
            {"attempt": 1, "attempt_passed": False, "attempt_reason": "no rows",
             "sql": "select 2", "ok": False},
            {"attempt": 2, "attempt_passed": True, "attempt_reason": "ok",
             "sql": "select 3", "ok": True},
        ]
    )

    attempts = group_attempts(trace)

    assert [a["attempt"] for a in attempts] == [1, 2]
    assert len(attempts[0]["statements"]) == 2
    assert attempts[1]["passed"] is True


def test_group_attempts_handles_no_trace():
    assert group_attempts(None) == []


def test_preview_is_nothing_when_there_is_no_fixed_query():
    repair = Repair(
        intent="x", broken_query="select 1",
        fixed_query=None, status=RepairStatus.failed,
    )
    assert preview_rows(repair) is None


def test_preview_returns_rows_for_a_working_query():
    repair = Repair(
        intent="count the customers",
        broken_query="select count(*) from sandbox.customer",
        fixed_query="select count(*) as n from sandbox.customers",
        status=RepairStatus.needs_review,
    )
    rows = preview_rows(repair)
    assert rows and "n" in rows[0]


def test_preview_is_nothing_when_the_query_is_broken():
    repair = Repair(
        intent="x", broken_query="select 1",
        fixed_query="select * from sandbox.nope",
        status=RepairStatus.needs_review,
    )
    assert preview_rows(repair) is None
