import pytest

from app.approval import NotReviewable, approve, reject
from app.db.models import Repair, RepairStatus, SavedQuery
from app.db.session import SessionLocal

GOOD_QUERY = "select count(*) as n from sandbox.customers"


def _make(session, status):
    repair = Repair(
        intent="count the customers",
        broken_query="select count(*) from sandbox.customer",
        fixed_query=GOOD_QUERY,
        status=status,
    )
    session.add(repair)
    session.commit()
    return repair


def test_approve_runs_the_query_and_saves_it():
    session = SessionLocal()
    repair = _make(session, RepairStatus.needs_review)

    saved = approve(repair, session)

    assert repair.status is RepairStatus.approved
    assert saved.sql == GOOD_QUERY
    assert saved.result_preview          # rows came back, so it really ran
    session.close()


def test_approve_refuses_a_repair_that_is_not_ready():
    session = SessionLocal()
    repair = _make(session, RepairStatus.queued)

    with pytest.raises(NotReviewable):
        approve(repair, session)

    session.close()


def test_reject_records_the_reason_and_writes_nothing():
    session = SessionLocal()
    repair = _make(session, RepairStatus.needs_review)
    before = session.query(SavedQuery).count()

    reject(repair, session, "Counts every order line, not every order.")

    assert repair.status is RepairStatus.rejected
    assert repair.rejection_reason == "Counts every order line, not every order."
    assert session.query(SavedQuery).count() == before   # nothing was saved
    session.close()


def test_reject_needs_a_reason():
    session = SessionLocal()
    repair = _make(session, RepairStatus.needs_review)

    with pytest.raises(NotReviewable):
        reject(repair, session, "   ")

    session.close()


def test_reject_refuses_a_repair_that_is_not_ready():
    session = SessionLocal()
    repair = _make(session, RepairStatus.approved)

    with pytest.raises(NotReviewable):
        reject(repair, session, "too late")

    session.close()
