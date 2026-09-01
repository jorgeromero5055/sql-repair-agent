from sqlalchemy.orm import Session

from app.db.models import Repair, RepairStatus, SavedQuery
from app.sandbox import run_sql_as_app


class NotReviewable(Exception):
    """This repair isn't in a state where reviewing it makes sense."""


def approve(repair: Repair, session: Session) -> SavedQuery:
    if repair.status is not RepairStatus.needs_review:
        raise NotReviewable(f"Repair is {repair.status.value}, not needs_review.")

    result = run_sql_as_app(repair.fixed_query)
    if not result["ok"]:
        # It passed the verifier earlier, but data moves underneath you.
        raise NotReviewable(f"The query no longer runs: {result['error']}")

    saved = SavedQuery(
        repair_id=repair.id,
        sql=repair.fixed_query,
        result_preview=result["rows"],
    )
    repair.status = RepairStatus.approved

    session.add(saved)
    session.commit()      # both changes land together, or neither does
    session.refresh(saved)
    return saved


def reject(repair: Repair, session: Session, reason: str) -> Repair:
    if repair.status is not RepairStatus.needs_review:
        raise NotReviewable(f"Repair is {repair.status.value}, not needs_review.")

    reason = reason.strip()
    if not reason:
        # Also enforced on the request shape — this guard is for callers that skip the web.
        raise NotReviewable("A rejection needs a reason.")

    repair.rejection_reason = reason
    repair.status = RepairStatus.rejected

    session.commit()
    session.refresh(repair)
    return repair
