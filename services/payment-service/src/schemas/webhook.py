import uuid
from decimal import Decimal
from pydantic import BaseModel, Field


class WebhookDataPayload(BaseModel):
    booking_id: uuid.UUID = Field(..., description="Booking ID")
    transaction_id: str = Field(..., description="Gateway transaction reference")
    amount: Decimal = Field(..., description="Transaction amount")
    status: str = Field(default="SUCCESS", description="Transaction status (SUCCESS / FAILED)")


class WebhookPayload(BaseModel):
    event: str = Field(default="payment.completed", description="Gateway event name")
    data: WebhookDataPayload = Field(..., description="Event payload object")


class MockWebhookSimulateRequest(BaseModel):
    booking_id: uuid.UUID = Field(..., description="Booking ID to simulate webhook for")
    transaction_id: str | None = Field(default=None, description="Optional custom transaction ID")
    amount: Decimal = Field(..., gt=0, description="Amount paid")
    status: str = Field(default="SUCCESS", description="Status to simulate: SUCCESS or FAILED")
