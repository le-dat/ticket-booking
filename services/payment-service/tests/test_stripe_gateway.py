import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from src.core.constants import PaymentStatus
from src.gateways.factory import PaymentGatewayFactory
from src.gateways.stripe.provider import StripeGatewayProvider


def test_stripe_factory_resolution():
    gateway = PaymentGatewayFactory.get_gateway("stripe")
    assert isinstance(gateway, StripeGatewayProvider)


@pytest.mark.asyncio
async def test_stripe_create_payment_url():
    provider = StripeGatewayProvider(api_key="sk_test_123", webhook_secret="whsec_123")
    booking_id = uuid.uuid4()
    amount = Decimal("150000.00")

    mock_session = MagicMock()
    mock_session.id = "cs_test_session_12345"
    mock_session.url = "https://checkout.stripe.com/c/pay/cs_test_session_12345"

    with patch("stripe.checkout.Session.create", return_value=mock_session) as mock_create:
        result = await provider.create_payment_url(
            booking_id=booking_id,
            amount=amount,
            order_info="Booking payment",
            return_url="http://localhost:3000/done",
        )

        mock_create.assert_called_once()
        assert result.payment_url == "https://checkout.stripe.com/c/pay/cs_test_session_12345"
        assert result.gateway_reference == "cs_test_session_12345"


@pytest.mark.asyncio
async def test_stripe_verify_webhook_success():
    provider = StripeGatewayProvider(api_key="sk_test_123", webhook_secret="whsec_123")
    booking_id = uuid.uuid4()

    mock_event = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_9988",
                "payment_intent": "pi_test_1122",
                "amount_total": 150000,
                "currency": "vnd",
                "metadata": {
                    "booking_id": str(booking_id),
                },
            }
        },
    }

    with patch("stripe.Webhook.construct_event", return_value=mock_event):
        result = await provider.verify_webhook(
            raw_body=b'{"test": "data"}',
            headers={"stripe-signature": "t=123,v1=valid_sig"},
            payload={"test": "data"},
        )

        assert result.is_valid is True
        assert result.booking_id == booking_id
        assert result.gateway_transaction_id == "cs_test_9988"
        assert result.amount == Decimal("150000")
        assert result.status == PaymentStatus.SUCCESS


@pytest.mark.asyncio
async def test_stripe_verify_webhook_invalid_signature():
    provider = StripeGatewayProvider(api_key="sk_test_123", webhook_secret="whsec_123")

    with patch("stripe.Webhook.construct_event", side_effect=Exception("Invalid signature")):
        result = await provider.verify_webhook(
            raw_body=b'{"test": "bad"}',
            headers={"stripe-signature": "bad_sig"},
            payload={"test": "bad"},
        )

        assert result.is_valid is False
        assert result.status == PaymentStatus.FAILED


@pytest.mark.asyncio
async def test_stripe_query_transaction():
    provider = StripeGatewayProvider(api_key="sk_test_123", webhook_secret="whsec_123")
    booking_id = uuid.uuid4()
    cs_id = "cs_test_reconcile_123"

    mock_session = {
        "id": cs_id,
        "payment_status": "paid",
        "amount_total": 200000,
        "currency": "vnd",
    }

    with patch("stripe.checkout.Session.retrieve", return_value=mock_session):
        res = await provider.query_transaction(booking_id=booking_id, gateway_transaction_id=cs_id)
        assert res.is_found is True
        assert res.status == PaymentStatus.SUCCESS
        assert res.amount == Decimal("200000")
