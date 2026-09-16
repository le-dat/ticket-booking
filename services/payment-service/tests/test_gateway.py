import json
import uuid
from decimal import Decimal
import pytest

from src.core.constants import PaymentStatus
from src.gateways.factory import PaymentGatewayFactory
from src.gateways.mock.provider import MockGatewayProvider


@pytest.mark.asyncio
async def test_mock_gateway_create_url():
    provider = MockGatewayProvider(secret="test_secret_123")
    booking_id = uuid.uuid4()
    amount = Decimal("250000.00")

    result = await provider.create_payment_url(
        booking_id=booking_id,
        amount=amount,
        order_info="Test movie booking",
        return_url="http://localhost:3000/done",
    )

    assert result.payment_url.startswith("http://localhost:")
    assert str(booking_id) in result.payment_url
    assert "250000" in result.payment_url
    assert result.gateway_reference.startswith("MOCK-TX-")
    assert result.qr_code_url is not None


@pytest.mark.asyncio
async def test_mock_gateway_verify_valid_signature():
    secret = "my_super_secret"
    provider = MockGatewayProvider(secret=secret)
    booking_id = uuid.uuid4()

    payload = {
        "event": "payment.completed",
        "data": {
            "booking_id": str(booking_id),
            "transaction_id": "TX-998877",
            "amount": "150000.00",
            "status": "SUCCESS",
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    valid_signature = provider.sign_payload(raw_body)

    result = await provider.verify_webhook(
        raw_body=raw_body,
        headers={"x-signature": valid_signature},
        payload=payload,
    )

    assert result.is_valid is True
    assert result.booking_id == booking_id
    assert result.gateway_transaction_id == "TX-998877"
    assert result.amount == Decimal("150000.00")
    assert result.status == PaymentStatus.SUCCESS


@pytest.mark.asyncio
async def test_mock_gateway_verify_invalid_signature():
    provider = MockGatewayProvider(secret="correct_secret")
    payload = {"data": {"booking_id": str(uuid.uuid4()), "status": "SUCCESS"}}
    raw_body = json.dumps(payload).encode("utf-8")

    result = await provider.verify_webhook(
        raw_body=raw_body,
        headers={"x-signature": "sha512=invalid_signature_hash"},
        payload=payload,
    )

    assert result.is_valid is False


def test_gateway_factory_resolver():
    gateway = PaymentGatewayFactory.get_gateway("mock")
    assert isinstance(gateway, MockGatewayProvider)

    with pytest.raises(ValueError, match="Unsupported payment gateway"):
        PaymentGatewayFactory.get_gateway("non_existent_gateway")
