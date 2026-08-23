"""create sandbox schema and seed data

Revision ID: fb18cfd04ab0
Revises: abb6e68480ea
Create Date: 2026-08-23 14:35:43.948157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb18cfd04ab0'
down_revision: Union[str, Sequence[str], None] = 'abb6e68480ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS sandbox")

    op.execute("""
        CREATE TABLE sandbox.customers (
            id          integer PRIMARY KEY,
            name        text NOT NULL,
            city        text NOT NULL,
            signed_up   date NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE sandbox.products (
            id     integer PRIMARY KEY,
            name   text NOT NULL,
            price  numeric(10,2) NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE sandbox.orders (
            id           integer PRIMARY KEY,
            customer_id  integer NOT NULL REFERENCES sandbox.customers(id),
            placed_at    date NOT NULL,
            status       text NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE sandbox.order_items (
            id          integer PRIMARY KEY,
            order_id    integer NOT NULL REFERENCES sandbox.orders(id),
            product_id  integer NOT NULL REFERENCES sandbox.products(id),
            quantity    integer NOT NULL
        )
    """)

    op.execute("""
        INSERT INTO sandbox.customers (id, name, city, signed_up) VALUES
        (1, 'Ana Reyes',      'Austin',  '2024-01-15'),
        (2, 'Ben Okafor',     'Denver',  '2024-02-03'),
        (3, 'Chen Wei',       'Austin',  '2024-03-22'),
        (4, 'Dana Kowalski',  'Miami',   '2024-05-10'),
        (5, 'Eli Fontaine',   'Denver',  '2024-07-01')
    """)

    op.execute("""
        INSERT INTO sandbox.products (id, name, price) VALUES
        (1, 'Desk lamp',     34.00),
        (2, 'Notebook',       6.50),
        (3, 'Mechanical kb', 89.99),
        (4, 'Monitor stand', 45.00),
        (5, 'Cable pack',    12.25)
    """)

    op.execute("""
        INSERT INTO sandbox.orders (id, customer_id, placed_at, status) VALUES
        (1, 1, '2024-06-01', 'completed'),
        (2, 1, '2024-06-15', 'completed'),
        (3, 2, '2024-06-20', 'cancelled'),
        (4, 3, '2024-07-02', 'completed'),
        (5, 3, '2024-07-19', 'pending'),
        (6, 4, '2024-08-05', 'completed'),
        (7, 5, '2024-08-11', 'completed')
    """)

    op.execute("""
        INSERT INTO sandbox.order_items (id, order_id, product_id, quantity) VALUES
        (1, 1, 1, 2), (2, 1, 2, 5),
        (3, 2, 3, 1),
        (4, 3, 5, 3),
        (5, 4, 1, 1), (6, 4, 4, 2),
        (7, 5, 2, 10),
        (8, 6, 3, 1), (9, 6, 5, 2),
        (10, 7, 4, 1)
    """)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS sandbox CASCADE")
