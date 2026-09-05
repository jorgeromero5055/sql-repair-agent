import pytest
from sqlalchemy import create_engine

from app.sandbox import DatabaseUnreachable, _run, run_sql


def test_a_broken_query_comes_back_as_a_failure():
    # The database answered — it just rejected the SQL. The agent can act on this.
    result = run_sql("select * from sandbox.does_not_exist")

    assert result["ok"] is False
    assert "error" in result


def test_an_unreachable_database_raises():
    # Nothing is listening on this port, so the connection itself fails.
    nowhere = create_engine("postgresql+psycopg://nobody@localhost:1/nothing")

    with pytest.raises(DatabaseUnreachable):
        _run(nowhere, "select 1")
