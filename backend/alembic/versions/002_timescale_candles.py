"""TimescaleDB candles hypertable for OHLCV storage.

Revision ID: 002
Revises: 001
Create Date: 2025-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
    )
    op.create_index("ix_candles_symbol_timeframe_ts", "candles", ["symbol", "timeframe", "ts"], unique=False)
    # For TimescaleDB: run manually after migration: SELECT create_hypertable('candles', 'ts', if_not_exists => TRUE);


def downgrade() -> None:
    op.drop_index("ix_candles_symbol_timeframe_ts", table_name="candles")
    op.drop_table("candles")
