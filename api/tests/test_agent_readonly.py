import pytest

from app.agent.tools import run_sql

def test_can_read_sandbox():
    result = run_sql("select count(*) as n from sandbox.customers")
    assert result["ok"] is True
    assert result["rows"][0]["n"] > 0


def test_cannot_read_application_tables():
    result = run_sql("select count(*) from public.repairs")
    assert result["ok"] is False
    assert "permission denied" in result["error"].lower()


@pytest.mark.parametrize(
    "sql",
    [
        "drop table sandbox.orders",
        "insert into sandbox.customers (id, name, city, signed_up) values (99, 'x', 'y', '2024-01-01')",
        "update sandbox.customers set city = 'nowhere'",
    ],
)
def test_cannot_write(sql):
    result = run_sql(sql)
    assert result["ok"] is False