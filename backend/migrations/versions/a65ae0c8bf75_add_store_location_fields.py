"""add store location fields

Revision ID: a65ae0c8bf75
Revises: d2c3f4e5a6b7
Create Date: 2026-09-28 15:47:40.939502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a65ae0c8bf75"
down_revision: Union[str, None] = "d2c3f4e5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("pincode", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("latitude", sa.Float(), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("longitude", sa.Float(), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("landmark", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("address_details", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "address_details")
    op.drop_column("stores", "landmark")
    op.drop_column("stores", "longitude")
    op.drop_column("stores", "latitude")
    op.drop_column("stores", "pincode")