import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from src.gateways.dto import (
    GatewayPaymentUrlResult,
    GatewayQueryResult,
    GatewayWebhookResult,
)


class BasePaymentGateway(ABC):
    """Abstract Base Class (Port) that all payment gateway providers must implement."""

    @abstractmethod
    async def create_payment_url(
        self,
        booking_id: uuid.UUID,
        amount: Decimal,
        order_info: str,
        return_url: str,
    ) -> GatewayPaymentUrlResult:
        """Generate checkout redirect URL or QR code for customer."""
        pass

    @abstractmethod
    async def verify_webhook(
        self,
        raw_body: bytes,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> GatewayWebhookResult:
        """Verify gateway digital signature and normalize incoming webhook payload."""
        pass

    @abstractmethod
    async def query_transaction(
        self,
        booking_id: uuid.UUID,
        gateway_transaction_id: str | None = None,
    ) -> GatewayQueryResult:
        """Actively query gateway for transaction status (reconciliation)."""
        pass
