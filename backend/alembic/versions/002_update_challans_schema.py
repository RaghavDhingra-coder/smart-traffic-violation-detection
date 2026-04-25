"""Update challans schema for AI integration

Revision ID: 002_update_challans_schema
Revises: 001_initial
Create Date: 2026-04-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "002_update_challans_schema"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("challans", sa.Column("image_url", sa.String(length=255), nullable=True))
    op.execute("UPDATE challans SET status = 'UNPAID' WHERE status IS NULL OR status = 'pending'")
    op.alter_column(
        "challans",
        "status",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default="UNPAID",
    )
    op.drop_column("challans", "amount")
    op.drop_column("challans", "image_path")


def downgrade() -> None:
    op.add_column("challans", sa.Column("image_path", sa.String(length=255), nullable=True))
    op.add_column("challans", sa.Column("amount", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE challans SET status = 'pending' WHERE status = 'UNPAID'")
    op.alter_column(
        "challans",
        "status",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default="pending",
    )
    op.drop_column("challans", "image_url")
