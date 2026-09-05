import pytest

from app.db.models import Repair
from app.db.session import SessionLocal


@pytest.fixture
def session():
    """A database session that removes whatever the test created.

    Traces and saved queries go with the repair on their own — the foreign keys cascade.
    """
    session = SessionLocal()
    before = {row.id for row in session.query(Repair.id).all()}

    yield session

    # Runs even when the test failed partway through.
    session.rollback()
    for repair in session.query(Repair).all():
        if repair.id not in before:
            session.delete(repair)
    session.commit()
    session.close()
