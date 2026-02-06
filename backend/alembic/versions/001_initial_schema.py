"""Initial schema: users, scans, scan_rules, plans, subscriptions.

Revision ID: 001
Revises:
Create Date: 2025-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_superuser", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "plans",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("price_inr", sa.Integer(), default=0),
        sa.Column("price_usd", sa.Integer(), default=0),
        sa.Column("scans_per_day", sa.Integer(), default=5),
        sa.Column("alerts_per_day", sa.Integer(), default=5),
        sa.Column("features", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scan_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_ast", postgresql.JSONB(), nullable=False),
        sa.Column("is_public", sa.Boolean(), default=False),
        sa.Column("use_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_scan_rules_user_id"), "scan_rules", ["user_id"], unique=False)

    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("timeframe", sa.String(20), nullable=False),
        sa.Column("result_count", sa.Integer(), default=0),
        sa.Column("duration_ms", sa.Integer(), default=0),
        sa.Column("result_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["scan_rules.id"]),
    )
    op.create_index(op.f("ix_scans_user_id"), "scans", ["user_id"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False)

    # Seed plans
    op.execute(
        """
        INSERT INTO plans (id, name, price_inr, price_usd, scans_per_day, alerts_per_day, features)
        VALUES
        ('free', 'Free', 0, 0, 5, 5, '["Delayed data","5 scans","5 alerts/day"]'),
        ('pro', 'Pro', 999, 12, -1, -1, '["Unlimited scans","Live data","Backtest","Telegram"]'),
        ('elite', 'Elite', 2499, 30, -1, -1, '["AI signals","API access","Custom indicators","Priority support"]')
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("scans")
    op.drop_table("scan_rules")
    op.drop_table("plans")
    op.drop_table("users")
