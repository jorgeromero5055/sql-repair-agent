"""The ground truth for the eval.

Twenty correct queries against the sandbox, each with a plain description of what it does.
Deliverable 2 breaks these on purpose; deliverable 4 compares the agent's answer back against them.

The intent is what the agent is shown. It never names a column or a table — that would be the
answer written in English.
"""

CASES = [
    {
        "id": "all_customers",
        "intent": "List every customer, alphabetically by name.",
        "sql": "SELECT name, city FROM sandbox.customers ORDER BY name",
    },
    {
        "id": "customers_in_austin",
        "intent": "Which customers are based in Austin?",
        "sql": "SELECT name FROM sandbox.customers WHERE city = 'Austin' ORDER BY name",
    },
    {
        "id": "customers_per_city",
        "intent": "How many customers are in each city?",
        "sql": """
            SELECT city, COUNT(*) AS customers
            FROM sandbox.customers
            GROUP BY city
            ORDER BY city
        """,
    },
    {
        "id": "newest_customers",
        "intent": "Who are the three most recently signed-up customers?",
        "sql": """
            SELECT name, signed_up
            FROM sandbox.customers
            ORDER BY signed_up DESC
            LIMIT 3
        """,
    },
    {
        "id": "products_by_price",
        "intent": "List the products from most to least expensive.",
        "sql": "SELECT name, price FROM sandbox.products ORDER BY price DESC",
    },
    {
        "id": "cheap_products",
        "intent": "Which products cost less than forty dollars?",
        "sql": """
            SELECT name, price
            FROM sandbox.products
            WHERE price < 40
            ORDER BY price
        """,
    },
    {
        "id": "average_price",
        "intent": "What is the average price of a product?",
        "sql": "SELECT AVG(price) AS average_price FROM sandbox.products",
    },
    {
        "id": "order_count",
        "intent": "How many orders are there in total?",
        "sql": "SELECT COUNT(*) AS orders FROM sandbox.orders",
    },
    {
        "id": "orders_per_status",
        "intent": "How many orders are in each state?",
        "sql": """
            SELECT status, COUNT(*) AS orders
            FROM sandbox.orders
            GROUP BY status
            ORDER BY status
        """,
    },
    {
        "id": "completed_orders",
        "intent": "Show the orders that went through, oldest first.",
        "sql": """
            SELECT id, placed_at
            FROM sandbox.orders
            WHERE status = 'completed'
            ORDER BY placed_at
        """,
    },
    {
        "id": "orders_in_july",
        "intent": "Which orders were placed in July 2024?",
        "sql": """
            SELECT id, placed_at, status
            FROM sandbox.orders
            WHERE placed_at >= DATE '2024-07-01' AND placed_at < DATE '2024-08-01'
            ORDER BY placed_at
        """,
    },
    {
        "id": "orders_with_customer",
        "intent": "Show every order together with the name of who placed it.",
        "sql": """
            SELECT o.id, c.name, o.placed_at
            FROM sandbox.orders o
            JOIN sandbox.customers c ON c.id = o.customer_id
            ORDER BY o.id
        """,
    },
    {
        "id": "orders_per_customer",
        "intent": "How many orders has each customer placed? Include customers who have placed none.",
        "sql": """
            SELECT c.name, COUNT(o.id) AS orders
            FROM sandbox.customers c
            LEFT JOIN sandbox.orders o ON o.customer_id = c.id
            GROUP BY c.name
            ORDER BY c.name
        """,
    },
    {
        "id": "customers_who_ordered",
        "intent": "Which customers have placed at least one order?",
        "sql": """
            SELECT DISTINCT c.name
            FROM sandbox.customers c
            JOIN sandbox.orders o ON o.customer_id = c.id
            ORDER BY c.name
        """,
    },
    {
        "id": "items_per_order",
        "intent": "How many individual items are in each order?",
        "sql": """
            SELECT o.id, SUM(i.quantity) AS items
            FROM sandbox.orders o
            JOIN sandbox.order_items i ON i.order_id = o.id
            GROUP BY o.id
            ORDER BY o.id
        """,
    },
    {
        "id": "order_totals",
        "intent": "What is each order worth?",
        "sql": """
            SELECT o.id, SUM(i.quantity * p.price) AS total
            FROM sandbox.orders o
            JOIN sandbox.order_items i ON i.order_id = o.id
            JOIN sandbox.products p ON p.id = i.product_id
            GROUP BY o.id
            ORDER BY o.id
        """,
    },
    {
        "id": "completed_revenue",
        "intent": "How much money did we actually take, counting only orders that went through?",
        "sql": """
            SELECT SUM(i.quantity * p.price) AS revenue
            FROM sandbox.orders o
            JOIN sandbox.order_items i ON i.order_id = o.id
            JOIN sandbox.products p ON p.id = i.product_id
            WHERE o.status = 'completed'
        """,
    },
    {
        "id": "revenue_per_product",
        "intent": "How much has each product brought in?",
        "sql": """
            SELECT p.name, SUM(i.quantity * p.price) AS revenue
            FROM sandbox.products p
            JOIN sandbox.order_items i ON i.product_id = p.id
            GROUP BY p.name
            ORDER BY revenue DESC
        """,
    },
    {
        "id": "best_selling_product",
        "intent": "Which single product has sold the most units?",
        "sql": """
            SELECT p.name, SUM(i.quantity) AS units
            FROM sandbox.products p
            JOIN sandbox.order_items i ON i.product_id = p.id
            GROUP BY p.name
            ORDER BY units DESC
            LIMIT 1
        """,
    },
    {
        "id": "big_spenders",
        "intent": "Which customers have spent more than fifty dollars on orders that went through?",
        "sql": """
            SELECT c.name, SUM(i.quantity * p.price) AS spent
            FROM sandbox.customers c
            JOIN sandbox.orders o ON o.customer_id = c.id
            JOIN sandbox.order_items i ON i.order_id = o.id
            JOIN sandbox.products p ON p.id = i.product_id
            WHERE o.status = 'completed'
            GROUP BY c.name
            HAVING SUM(i.quantity * p.price) > 50
            ORDER BY spent DESC
        """,
    },
]
