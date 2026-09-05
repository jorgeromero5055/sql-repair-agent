from app.evaluation.corrupt import BREAKS, generate
from app.evaluation.oracle import compare

GENERATED = generate()


def test_it_produces_a_useful_number_of_cases():
    # Up to 100. Well under 60 would mean breaks are silently not applying.
    assert 60 <= len(GENERATED) <= 100


def test_every_break_type_is_represented():
    used = {case["break_type"] for case in GENERATED}
    assert used == set(BREAKS)


def test_it_is_deterministic():
    assert [c["id"] for c in generate()] == [c["id"] for c in GENERATED]


def test_every_case_is_actually_broken():
    # Either the query errors, or it returns something different from the original.
    # A "broken" query that still returns the right rows is a free pass for the agent.
    still_correct = [
        case["id"]
        for case in GENERATED
        if compare(case["broken_sql"], case["reference_sql"])["passed"]
    ]
    assert not still_correct, f"these are not broken: {still_correct}"
