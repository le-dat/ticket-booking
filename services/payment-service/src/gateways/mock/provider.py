import hashlib
import hmac
import uuid
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from src.core.config import settings
from src.core.constants import PaymentStatus
from src.gateways.base import BasePaymentGateway
from src.gateways.dto import (
    GatewayPaymentUrlResult,
    GatewayQueryResult,
    GatewayWebhookResult,
)


class MockGatewayProvider(BasePaymentGateway):
    """Sandbox / Mock Payment Gateway Provider for local testing and CI/CD."""

    def __init__(self, secret: str | None = None):
        self.secret = (secret or settings.WEBHOOK_SECRET).encode("utf-8")

    def sign_payload(self, body_bytes: bytes) -> str:
        """Helper to generate HMAC-SHA512 signature for webhook simulation."""
        digest = hmac.new(self.secret, body_bytes, hashlib.sha512).hexdigest()
        return f"sha512={digest}"

    async def create_payment_url(
        self,
        booking_id: uuid.UUID,
        amount: Decimal,
        order_info: str,
        return_url: str,
    ) -> GatewayPaymentUrlResult:
        gateway_reference = f"MOCK-TX-{uuid.uuid4().hex[:12].upper()}"
        params = {
            "booking_id": str(booking_id),
            "amount": str(amount),
            "order_info": order_info,
            "return_url": return_url,
            "ref": gateway_reference,
        }
        mock_ui_url = f"http://localhost:{settings.PORT}/api/v1/mock-gateway/checkout?{urlencode(params)}"

        return GatewayPaymentUrlResult(
            payment_url=mock_ui_url,
            qr_code_url=f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={mock_ui_url}",
            gateway_reference=gateway_reference,
        )

    async def verify_webhook(
        self,
        raw_body: bytes,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> GatewayWebhookResult:
        signature_header = (
            headers.get("x-signature")
            or headers.get("X-Signature")
            or headers.get("x-signature-sha512")
            or ""
        )

        expected_signature = self.sign_payload(raw_body)
        is_valid = hmac.compare_digest(expected_signature, signature_header)

        data = payload.get("data", payload)
        booking_id_raw = data.get("booking_id")
        try:
            booking_id = uuid.UUID(str(booking_id_raw)) if booking_id_raw else uuid.uuid4()
        except ValueError:
            booking_id = uuid.uuid4()

        raw_status = str(data.get("status", "FAILED")).upper()
        status = PaymentStatus.SUCCESS if raw_status in ("SUCCESS", "PAID", "00") else PaymentStatus.FAILED

        amount_raw = data.get("amount", "0")
        try:
            amount = Decimal(str(amount_raw))
        except Exception:
            amount = Decimal("0")

        gateway_tx_id = str(data.get("transaction_id") or data.get("ref") or f"MOCK-{uuid.uuid4().hex[:8]}")

        return GatewayWebhookResult(
            is_valid=is_valid,
            booking_id=booking_id,
            gateway_transaction_id=gateway_tx_id,
            amount=amount,
            status=status,
            raw_data=payload,
        )

    async def query_transaction(
        self,
        booking_id: uuid.UUID,
        gateway_transaction_id: str | None = None,
    ) -> GatewayQueryResult:
        # Mock active query response
        return GatewayQueryResult(
            is_found=True,
            status=PaymentStatus.SUCCESS if gateway_transaction_id else PaymentStatus.PENDING,
            gateway_transaction_id=gateway_transaction_id or f"MOCK-INQ-{booking_id}",
            amount=None,
            raw_data={"queried_booking_id": str(booking_id), "source": "mock_query"},
        )
