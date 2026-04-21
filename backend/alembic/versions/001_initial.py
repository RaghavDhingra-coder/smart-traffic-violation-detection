# TODO for initial-migration: evolve the schema as business rules stabilize and new entities are introduced.
"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-04-21 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate", sa.String(length=32), nullable=False),
        sa.Column("owner_name", sa.String(length=128), nullable=False),
        sa.Column("owner_contact", sa.String(length=64), nullable=True),
        sa.Column("vehicle_type", sa.String(length=64), nullable=False),
        sa.Column("registration_state", sa.String(length=16), nullable=True),
    )
    op.create_index("ix_vehicles_id", "vehicles", ["id"], unique=False)
    op.create_index("ix_vehicles_plate", "vehicles", ["plate"], unique=True)

    op.create_table(
        "challans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate", sa.String(length=32), nullable=False),
        sa.Column("violation_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("image_path", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_challans_id", "challans", ["id"], unique=False)
    op.create_index("ix_challans_plate", "challans", ["plate"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("challan_id", sa.Integer(), sa.ForeignKey("challans.id"), nullable=False),
        sa.Column("razorpay_order_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_payments_id", "payments", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_challans_plate", table_name="challans")
    op.drop_index("ix_challans_id", table_name="challans")
    op.drop_table("challans")
    op.drop_index("ix_vehicles_plate", table_name="vehicles")
    op.drop_index("ix_vehicles_id", table_name="vehicles")
    op.drop_table("vehicles")
