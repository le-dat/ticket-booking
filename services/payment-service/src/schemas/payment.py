import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from src.core.constants import PaymentStatus, TransactionStatus


class PaymentCreateIntentRequest(BaseModel):
    booking_id: uuid.UUID = Field(..., description="Unique booking ID from Booking Service")
    user_id: uuid.UUID = Field(..., description="Customer user ID")
    amount: Decimal = Field(..., gt=0, description="Total amount to be paid")
    currency: str = Field(default="VND", description="Payment currency code")


class PaymentCheckoutRequest(BaseModel):
    booking_id: uuid.UUID = Field(..., description="Booking ID to checkout")
    user_id: uuid.UUID = Field(..., description="Customer user ID")
    amount: Decimal = Field(..., gt=0, description="Amount to be charged")
    gateway: str | None = Field(default=None, description="Specific gateway plugin to use (mock, vnpay, momo)")
    order_info: str | None = Field(default=None, description="Description displayed on gateway checkout page")
    return_url: str | None = Field(default=None, description="Frontend URL to redirect customer after payment")


class PaymentCheckoutResponse(BaseModel):
    payment_url: str = Field(..., description="Gateway redirect checkout URL")
    qr_code_url: str | None = Field(default=None, description="QR code link for mobile scan")
    gateway_reference: str = Field(..., description="Gateway transaction reference code")


class TransactionResponseDTO(BaseModel):
    id: uuid.UUID
    gateway: str
    gateway_transaction_id: str | None
    idempotency_key: str | None
    amount: Decimal
    status: TransactionStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentResponseDTO(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
    transactions: list[TransactionResponseDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
