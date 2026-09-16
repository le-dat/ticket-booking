"""init payments and transactions tables

Revision ID: 001_init_payments_and_transactions
Revises:
Create Date: 2026-09-16 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_init_payments_and_transactions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    payment_status_enum = postgresql.ENUM(
        "PENDING",
        "SUCCESS",
        "FAILED",
        "CANCELLED",
        "REFUNDED",
        "PAYMENT_EXPIRED_REFUND_PENDING",
        name="payment_status",
        create_type=False,
    )
    transaction_status_enum = postgresql.ENUM(
        "INITIATED",
        "SUCCESS",
        "FAILED",
        name="transaction_status",
        create_type=False,
    )

    sa.Enum(
        "PENDING",
        "SUCCESS",
        "FAILED",
        "CANCELLED",
        "REFUNDED",
        "PAYMENT_EXPIRED_REFUND_PENDING",
        name="payment_status",
    ).create(op.get_bind(), checkfirst=True)

    sa.Enum(
        "INITIATED",
        "SUCCESS",
        "FAILED",
        name="transaction_status",
    ).create(op.get_bind(), checkfirst=True)

    # 1. Create payments table
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="VND"),
        sa.Column("status", payment_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_payments_booking_id", "payments", ["booking_id"])
    op.create_index("idx_payments_user_id", "payments", ["user_id"])
    op.create_index("idx_payments_status", "payments", ["status"])

    # 2. Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gateway", sa.String(length=50), nullable=False, server_default="mock"),
        sa.Column("gateway_transaction_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True, unique=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", transaction_status_enum, nullable=False, server_default="INITIATED"),
        sa.Column("gateway_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_transactions_payment_id", "transactions", ["payment_id"])
    op.create_index("idx_transactions_gateway_tx_id", "transactions", ["gateway_transaction_id"])
    op.create_index("idx_transactions_idempotency_key", "transactions", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("payments")
    sa.Enum(name="transaction_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_status").drop(op.get_bind(), checkfirst=True)
