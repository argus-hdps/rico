"""Create dev database flag table

Revision ID: 8d8176be0c8e
Revises:
Create Date: 2024-03-13 17:40:07.175400+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d8176be0c8e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dev_gonogo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("is_devel", sa.Boolean, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("dev_gonogo")
