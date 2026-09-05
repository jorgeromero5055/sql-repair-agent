"""Break correct queries on purpose, to make eval cases.

Every break is deterministic: the same query in gives the same broken query out, so two eval runs
score the same case set and their numbers can be compared.

A break that doesn't apply to a query returns None and is skipped, so the case set is up to five
per query rather than exactly five.

Every candidate is then run and compared against the query it came from. A break that leaves the
result unchanged is dropped — with this little data, a genuinely wrong join can still return the
right rows by coincidence, and that would be a case the agent passes without doing anything.
"""

import re

from app.evaluation.cases import CASES
from app.evaluation.oracle import compare

# Real column names paired with a plausible misremembering of each.
_COLUMN_TYPOS = {
    "customer_id": "customerid",
    "product_id": "productid",
    "order_id": "orderid",
    "placed_at": "placed_on",
    "signed_up": "signup_date",
    "quantity": "quantities",
    "status": "state",
    "price": "prices",
    "city": "town",
    "name": "title",
}

_AGGREGATE_SWAPS = [("COUNT(", "SUM("), ("AVG(", "SUM("), ("SUM(", "COUNT(")]


def wrong_table(sql: str) -> str | None:
    """Drop the s off the first table name. All four sandbox tables are plural."""
    match = re.search(r"sandbox\.(\w+)", sql)
    if not match or not match.group(1).endswith("s"):
        return None
    return sql.replace(match.group(0), f"sandbox.{match.group(1)[:-1]}", 1)


def wrong_column(sql: str) -> str | None:
    """Misremember one column name, everywhere it appears."""
    for real, typo in _COLUMN_TYPOS.items():
        if re.search(rf"\b{real}\b", sql):
            return re.sub(rf"\b{real}\b", typo, sql)
    return None


def wrong_join_key(sql: str) -> str | None:
    """Join on the wrong column — a foreign key swapped for the primary key."""
    match = re.search(r"ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)", sql)
    if not match:
        return None

    left_alias, left_col, right_alias, right_col = match.groups()
    if right_col == "id" and left_col == "id":
        return None

    # Whichever side names a foreign key, point it at id instead.
    if right_col != "id":
        broken = f"ON {left_alias}.{left_col} = {right_alias}.id"
    else:
        broken = f"ON {left_alias}.id = {right_alias}.{right_col}"

    return sql.replace(match.group(0), broken, 1)


def dropped_filter(sql: str) -> str | None:
    """Lose the WHERE or HAVING clause, the way an edit loses one."""
    for keyword in ("WHERE", "HAVING"):
        pattern = rf"\s+{keyword}\b.*?(?=\s+(?:GROUP|ORDER|HAVING|LIMIT)\b|\s*$)"
        if re.search(pattern, sql, flags=re.S):
            return re.sub(pattern, "", sql, count=1, flags=re.S)
    return None


def wrong_aggregate(sql: str) -> str | None:
    """Use the wrong aggregate, or flip a comparison."""
    for real, wrong in _AGGREGATE_SWAPS:
        if real in sql.upper():
            index = sql.upper().index(real)
            return sql[:index] + wrong + sql[index + len(real):]

    if "<" in sql:
        return sql.replace("<", ">", 1)
    if ">" in sql:
        return sql.replace(">", "<", 1)
    return None


BREAKS = {
    "wrong_table": wrong_table,
    "wrong_column": wrong_column,
    "wrong_join_key": wrong_join_key,
    "dropped_filter": dropped_filter,
    "wrong_aggregate": wrong_aggregate,
}


def generate(cases=CASES) -> list[dict]:
    """Every case that is genuinely broken. Up to five per query.

    Runs each candidate against the database, so this needs a live sandbox.
    """
    generated = []

    for case in cases:
        for name, break_it in BREAKS.items():
            broken = break_it(case["sql"])
            if broken is None or broken.strip() == case["sql"].strip():
                continue

            # Still returns the right rows? Then it isn't a case.
            if compare(broken, case["sql"])["passed"]:
                continue

            generated.append(
                {
                    "id": f"{case['id']}__{name}",
                    "case_id": case["id"],
                    "break_type": name,
                    "intent": case["intent"],
                    "broken_sql": broken,
                    "reference_sql": case["sql"],
                }
            )

    return generated
