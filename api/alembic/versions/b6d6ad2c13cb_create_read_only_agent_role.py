"""create read only agent role

Revision ID: b6d6ad2c13cb
Revises: fb18cfd04ab0
Create Date: 2026-08-23 14:49:37.146099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6d6ad2c13cb'
down_revision: Union[str, Sequence[str], None] = 'fb18cfd04ab0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

import os

def upgrade() -> None:
    password = os.environ["AGENT_DB_PASSWORD"]
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agent_ro') THEN
                CREATE ROLE agent_ro LOGIN NOINHERIT PASSWORD '{password}';
            END IF;
        END
        $$
    """)
    
    op.execute("GRANT USAGE ON SCHEMA sandbox TO agent_ro")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA sandbox TO agent_ro")
    op.execute("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA sandbox
        GRANT SELECT ON TABLES TO agent_ro
    """)

    op.execute("REVOKE ALL ON SCHEMA public FROM agent_ro")


def downgrade() -> None:
    op.execute("REVOKE ALL ON SCHEMA sandbox FROM agent_ro")
    op.execute("DROP ROLE IF EXISTS agent_ro")