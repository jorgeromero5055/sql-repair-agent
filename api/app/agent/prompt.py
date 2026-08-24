MODEL = "gemini-3.5-flash"

SCHEMA = """
sandbox.customers    (id int, name text, city text, signed_up date)
sandbox.products     (id int, name text, price numeric)
sandbox.orders       (id int, customer_id int, placed_at date, status text)
sandbox.order_items  (id int, order_id int, product_id int, quantity int)
""".strip()

SYSTEM_INSTRUCTION = f"""
You repair broken SQL queries.

You are given a query that does not work, and a description of what it was
supposed to do. You are NOT told what the error is. Find out by running it.

The database schema is:

{SCHEMA}

How to work:
- Run the broken query first to see how it fails.
- Investigate with additional queries if you need to understand the data.
- Run your corrected query ONCE to confirm it works.
- Then stop calling tools and return your final answer.
- Do not re-run a query you have already confirmed.

Rules:
- Every table lives in the sandbox schema. Always qualify names.
- SELECT only. Anything else will be refused.
""".strip()


def build_user_message(intent: str, broken_query: str) -> str:
    return f"""
What the query was supposed to do:
{intent}

The broken query:
```sql
{broken_query}
""".strip()