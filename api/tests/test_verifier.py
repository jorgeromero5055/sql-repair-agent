from app.evaluation.oracle import compare
from app.verifier import check

GOOD = """
select customers.name, sum(order_items.quantity) as total
from sandbox.customers
join sandbox.orders on customers.id = orders.customer_id
join sandbox.order_items on orders.id = order_items.order_id
group by customers.name
"""


def test_check_passes_a_working_query():
    assert check(GOOD)["passed"] is True


def test_check_fails_broken_sql():
    result = check("select * from sandbox.nope")
    assert result["passed"] is False
    assert "does not exist" in result["reason"]

def test_check_passes_empty_result():
    result = check("select * from sandbox.customers where city = 'nowhere'")
    assert result["passed"] is True

def test_compare_matches_itself():
    assert compare(GOOD, GOOD)["passed"] is True


def test_compare_ignores_row_order():
    ordered = GOOD + " order by customers.name desc"
    assert compare(ordered, GOOD)["passed"] is True


def test_compare_fails_wrong_values():
    wrong = "select name, 0 as total from sandbox.customers"
    result = compare(wrong, GOOD)
    assert result["passed"] is False
    assert "Rows differ" in result["reason"]


def test_compare_fails_wrong_column_names():
    renamed = GOOD.replace("as total", "as qty")
    result = compare(renamed, GOOD)
    assert result["passed"] is False
    assert "Column names differ" in result["reason"]