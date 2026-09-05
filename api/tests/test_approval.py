import pytest

from app.approval import NotReviewable, approve, reject
from app.db.models import Repair, RepairStatus, SavedQuery

GOOD_QUERY = "select count(*) as n from sandbox.customers"


def _make(session, status):
    # A repair in whatever state the test needs. Removed again by the session fixture.
    repair = Repair(
        intent="count the customers",
        broken_query="select count(*) from sandbox.customer",
        fixed_query=GOOD_QUERY,
        status=status,
    )
    session.add(repair)
    session.commit()
    return repair


def test_approve_runs_the_query_and_saves_it(session):
    repair = _make(session, RepairStatus.needs_review)

    saved = approve(repair, session)

    assert repair.status is RepairStatus.approved
    assert saved.sql == GOOD_QUERY
    assert saved.result_preview          # rows came back, so it really ran


def test_approve_refuses_a_repair_that_is_not_ready(session):
    repair = _make(session, RepairStatus.queued)

    with pytest.raises(NotReviewable):
        approve(repair, session)


def test_reject_records_the_reason_and_writes_nothing(session):
    repair = _make(session, RepairStatus.needs_review)
    before = session.query(SavedQuery).count()

    reject(repair, session, "Counts every order line, not every order.")

    assert repair.status is RepairStatus.rejected
    assert repair.rejection_reason == "Counts every order line, not every order."
    assert session.query(SavedQuery).count() == before   # nothing was saved


def test_reject_needs_a_reason(session):
    repair = _make(session, RepairStatus.needs_review)

    with pytest.raises(NotReviewable):
        reject(repair, session, "   ")


def test_reject_refuses_a_repair_that_is_not_ready(session):
    # Already approved — the decision was made, it can't be re-decided.
    repair = _make(session, RepairStatus.approved)

    with pytest.raises(NotReviewable):
        reject(repair, session, "too late")
