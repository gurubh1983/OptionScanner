"""Template marketplace: price, purchases, ratings.

Revision ID: 003
Revises: 002
Create Date: 2025-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scan_rules", sa.Column("price_inr", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scan_rules", sa.Column("price_usd", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scan_rules", sa.Column("premium_only", sa.Boolean(), nullable=False, server_default="false"))

    op.create_table(
        "template_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_inr", sa.Integer(), nullable=False),
        sa.Column("amount_usd", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["scan_rules.id"]),
    )
    op.create_index(op.f("ix_template_purchases_buyer_id"), "template_purchases", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_template_purchases_rule_id"), "template_purchases", ["rule_id"], unique=False)

    op.create_table(
        "template_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["scan_rules.id"]),
        sa.UniqueConstraint("user_id", "rule_id", name="uq_template_rating_user_rule"),
    )
    op.create_index(op.f("ix_template_ratings_rule_id"), "template_ratings", ["rule_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_template_ratings_rule_id"), table_name="template_ratings")
    op.drop_table("template_ratings")
    op.drop_index(op.f("ix_template_purchases_rule_id"), table_name="template_purchases")
    op.drop_index(op.f("ix_template_purchases_buyer_id"), table_name="template_purchases")
    op.drop_table("template_purchases")
    op.drop_column("scan_rules", "premium_only")
    op.drop_column("scan_rules", "price_usd")
    op.drop_column("scan_rules", "price_inr")
