import logging
import uuid
from decimal import Decimal
from typing import Any
import stripe

from src.core.config import settings
from src.core.constants import PaymentStatus
from src.gateways.base import BasePaymentGateway
from src.gateways.dto import (
    GatewayPaymentUrlResult,
    GatewayQueryResult,
    GatewayWebhookResult,
)

logger = logging.getLogger("payment-service.gateways.stripe")


class StripeGatewayProvider(BasePaymentGateway):
    """Stripe Payment Gateway Provider implementing BasePaymentGateway interface."""

    def __init__(
        self,
        api_key: str | None = None,
        webhook_secret: str | None = None,
    ):
        self.api_key = api_key or settings.STRIPE_SECRET_KEY
        self.webhook_secret = webhook_secret or settings.STRIPE_WEBHOOK_SECRET

    def _convert_amount_to_stripe(self, amount: Decimal, currency: str) -> int:
        """Stripe uses cents for USD/EUR, but zero-decimal integer for VND/JPY."""
        currency_lower = currency.lower()
        if currency_lower in ("vnd", "jpy", "krw"):
            return int(amount)
        return int(amount * 100)

    def _convert_amount_from_stripe(self, amount_stripe: int, currency: str) -> Decimal:
        """Convert Stripe smallest units back to standard Decimal amount."""
        currency_lower = currency.lower()
        if currency_lower in ("vnd", "jpy", "krw"):
            return Decimal(amount_stripe)
        return Decimal(amount_stripe) / Decimal(100)

    async def create_payment_url(
        self,
        booking_id: uuid.UUID,
        amount: Decimal,
        order_info: str,
        return_url: str,
    ) -> GatewayPaymentUrlResult:
        currency = settings.STRIPE_CURRENCY.lower()
        stripe_unit_amount = self._convert_amount_to_stripe(amount, currency)

        session = stripe.checkout.Session.create(
            api_key=self.api_key,
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "unit_amount": stripe_unit_amount,
                        "product_data": {
                            "name": order_info,
                            "description": f"Booking ID: {booking_id}",
                        },
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "booking_id": str(booking_id),
            },
            success_url=f"{return_url}?booking_id={booking_id}&session_id={{CHECKOUT_SESSION_ID}}&status=SUCCESS",
            cancel_url=f"{return_url}?booking_id={booking_id}&status=CANCELLED",
        )

        return GatewayPaymentUrlResult(
            payment_url=session.url or "",
            qr_code_url=None,
            gateway_reference=session.id,
        )

    async def verify_webhook(
        self,
        raw_body: bytes,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> GatewayWebhookResult:
        sig_header = headers.get("stripe-signature") or headers.get("Stripe-Signature", "")

        try:
            event = stripe.Webhook.construct_event(
                payload=raw_body,
                sig_header=sig_header,
                secret=self.webhook_secret,
            )
        except Exception as exc:
            logger.warning("❌ Stripe webhook signature verification failed: %s", exc)
            return GatewayWebhookResult(
                is_valid=False,
                booking_id=uuid.uuid4(),
                gateway_transaction_id="",
                amount=Decimal("0"),
                status=PaymentStatus.FAILED,
                raw_data=payload,
            )

        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        booking_id_str = data_object.get("metadata", {}).get("booking_id")
        try:
            booking_id = uuid.UUID(booking_id_str) if booking_id_str else uuid.uuid4()
        except ValueError:
            booking_id = uuid.uuid4()

        gateway_tx_id = data_object.get("id") or data_object.get("payment_intent") or "UNKNOWN_TX"
        currency = data_object.get("currency", "vnd")
        amount_total = data_object.get("amount_total", 0)
        amount = self._convert_amount_from_stripe(amount_total, currency)

        status = (
            PaymentStatus.SUCCESS
            if event_type in ("checkout.session.completed", "payment_intent.succeeded")
            else PaymentStatus.FAILED
        )

        return GatewayWebhookResult(
            is_valid=True,
            booking_id=booking_id,
            gateway_transaction_id=gateway_tx_id,
            amount=amount,
            status=status,
            raw_data=event,
        )

    async def query_transaction(
        self,
        booking_id: uuid.UUID,
        gateway_transaction_id: str | None = None,
    ) -> GatewayQueryResult:
        if not gateway_transaction_id:
            return GatewayQueryResult(
                is_found=False,
                status=PaymentStatus.PENDING,
            )

        try:
            if gateway_transaction_id.startswith("cs_"):
                session = stripe.checkout.Session.retrieve(
                    gateway_transaction_id,
                    api_key=self.api_key,
                )
                is_paid = session.get("payment_status") == "paid"
                status = PaymentStatus.SUCCESS if is_paid else PaymentStatus.PENDING
                amount = self._convert_amount_from_stripe(
                    session.get("amount_total", 0),
                    session.get("currency", "vnd"),
                )
                return GatewayQueryResult(
                    is_found=True,
                    status=status,
                    gateway_transaction_id=gateway_transaction_id,
                    amount=amount,
                    raw_data=dict(session),
                )
        except Exception as exc:
            logger.error("Error querying Stripe session %s: %s", gateway_transaction_id, exc)

        return GatewayQueryResult(is_found=False, status=PaymentStatus.PENDING)
