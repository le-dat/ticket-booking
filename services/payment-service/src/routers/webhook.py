import json
import logging
from typing import Any
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from src.dependencies import get_payment_service
from src.gateways.factory import PaymentGatewayFactory
from src.services.payment_service import PaymentService

logger = logging.getLogger("payment-service.webhook")
router = APIRouter(prefix="/api/v1/payments", tags=["webhook"])


@router.post(
    "/webhook",
    summary="Gateway webhook callback endpoint",
    response_description="Payment Gateway compatible confirmation JSON",
)
async def payment_webhook(
    request: Request,
    gateway: str | None = Query(default=None, description="Payment gateway identifier (mock, vnpay, momo)"),
    service: PaymentService = Depends(get_payment_service),
) -> JSONResponse:
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as exc:
        logger.error("Malformed JSON in webhook request: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": "Invalid JSON body"},
        )

    # 1. Resolve targeted Gateway Plugin
    gateway_name = gateway or request.headers.get("x-gateway") or "mock"
    try:
        gateway_provider = PaymentGatewayFactory.get_gateway(gateway_name)
    except ValueError as val_err:
        logger.warning("Unsupported gateway requested: %s", val_err)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": str(val_err)},
        )

    # 2. Verify signature & normalize payload
    verify_result = await gateway_provider.verify_webhook(
        raw_body=raw_body,
        headers=headers,
        payload=payload,
    )

    if not verify_result.is_valid:
        logger.warning("❌ Signature verification failed for gateway '%s'", gateway_name)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"status": "error", "message": "Invalid webhook digital signature"},
        )

    # 3. Process normalized data in Core Service
    result = await service.process_verified_webhook(
        result=verify_result,
        gateway_name=gateway_name,
    )

    # 4. Return Gateway-compatible success envelope
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result,
    )
