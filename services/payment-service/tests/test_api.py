import uuid
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest
from httpx import ASGITransport, AsyncClient

from src.core.constants import PaymentStatus
from src.dependencies import get_payment_service
from src.gateways.dto import GatewayPaymentUrlResult
from src.main import app
from src.models.payment import Payment
from src.services.payment_service import PaymentService


@pytest.fixture
def mock_payment_service():
    service = AsyncMock(spec=PaymentService)
    return service


@pytest.mark.asyncio
async def test_health_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "service": "payment-service"}


@pytest.mark.asyncio
async def test_create_payment_intent_api(mock_payment_service):
    booking_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_payment = Payment(
        id=uuid.uuid4(),
        booking_id=booking_id,
        user_id=user_id,
        amount=Decimal("150000.00"),
        currency="VND",
        status=PaymentStatus.PENDING,
    )
    mock_payment_service.create_or_get_intent.return_value = mock_payment

    app.dependency_overrides[get_payment_service] = lambda: mock_payment_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "booking_id": str(booking_id),
            "user_id": str(user_id),
            "amount": "150000.00",
            "currency": "VND",
        }
        resp = await client.post("/api/v1/payments/intent", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["booking_id"] == str(booking_id)
        assert data["data"]["status"] == "PENDING"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_checkout_api(mock_payment_service):
    booking_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_payment_service.checkout.return_value = GatewayPaymentUrlResult(
        payment_url="http://gateway.test/checkout/123",
        qr_code_url="http://gateway.test/qr/123.png",
        gateway_reference="MOCK-REF-123",
    )

    app.dependency_overrides[get_payment_service] = lambda: mock_payment_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "booking_id": str(booking_id),
            "user_id": str(user_id),
            "amount": "200000.00",
        }
        resp = await client.post("/api/v1/payments/checkout", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["payment_url"] == "http://gateway.test/checkout/123"
        assert data["data"]["gateway_reference"] == "MOCK-REF-123"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_payment_status_api(mock_payment_service):
    booking_id = uuid.uuid4()

    mock_payment = Payment(
        id=uuid.uuid4(),
        booking_id=booking_id,
        user_id=uuid.uuid4(),
        amount=Decimal("150000.00"),
        currency="VND",
        status=PaymentStatus.SUCCESS,
    )
    mock_payment_service.get_payment_status.return_value = mock_payment

    app.dependency_overrides[get_payment_service] = lambda: mock_payment_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/payments/{booking_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "SUCCESS"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_webhook_api(mock_payment_service):
    mock_payment_service.process_verified_webhook.return_value = {
        "status": "ok",
        "message": "Webhook processed successfully",
    }
    app.dependency_overrides[get_payment_service] = lambda: mock_payment_service

    from src.gateways.mock.provider import MockGatewayProvider
    provider = MockGatewayProvider()

    payload = {
        "event": "payment.completed",
        "data": {
            "booking_id": str(uuid.uuid4()),
            "transaction_id": "TX-123",
            "amount": "150000.00",
            "status": "SUCCESS",
        },
    }
    import json
    raw_body = json.dumps(payload).encode("utf-8")
    sig = provider.sign_payload(raw_body)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/payments/webhook",
            content=raw_body,
            headers={"X-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Webhook processed successfully"}

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_mock_gateway_ui():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/mock-gateway/checkout",
            params={
                "booking_id": str(uuid.uuid4()),
                "amount": "150000",
                "ref": "TX-TEST-001",
            },
        )
        assert resp.status_code == 200
        assert "Cổng Thanh Toán Giả Lập" in resp.text
        assert "SANDBOX ENVIRONMENT" in resp.text
