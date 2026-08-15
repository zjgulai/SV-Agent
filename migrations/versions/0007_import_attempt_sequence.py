"""Give immutable import observations a stable timeline order.

Revision ID: 0007_import_attempt_sequence
Revises: 0006_reliable_execution_ledger
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_import_attempt_sequence"
down_revision: str | None = "0006_reliable_execution_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE import_attempt_sequence")
    op.add_column(
        "import_attempts",
        sa.Column(
            "attempt_sequence",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("nextval('import_attempt_sequence')"),
        ),
    )
    op.drop_index("ix_import_attempts_job", table_name="import_attempts")
    op.create_index(
        "ix_import_attempts_job", "import_attempts", ["job_id", "attempt_sequence"]
    )


def downgrade() -> None:
    op.drop_index("ix_import_attempts_job", table_name="import_attempts")
    op.create_index("ix_import_attempts_job", "import_attempts", ["job_id", "id"])
    op.drop_column("import_attempts", "attempt_sequence")
    op.execute("DROP SEQUENCE import_attempt_sequence")
