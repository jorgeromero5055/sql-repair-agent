import pytest

from app.evaluation.cases import CASES
from app.sandbox import run_sql


def test_every_case_has_a_unique_id():
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))


def test_there_are_twenty_cases():
    assert len(CASES) == 20


# One test per case, named by its id, so a broken reference query fails by name.
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_reference_query_runs_and_returns_rows(case):
    result = run_sql(case["sql"])

    assert result["ok"], f"{case['id']} failed: {result.get('error')}"
    assert result["rows"], f"{case['id']} returned no rows"
