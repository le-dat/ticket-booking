import uuid
from fastapi import APIRouter, Depends, Query, status

from src.dependencies import get_payment_service
from src.schemas.payment import (
    PaymentCheckoutRequest,
    PaymentCheckoutResponse,
    PaymentCreateIntentRequest,
    PaymentResponseDTO,
)
from src.schemas.response import ApiResponse
from src.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "/intent",
    response_model=ApiResponse[PaymentResponseDTO],
    status_code=status.HTTP_201_CREATED,
    summary="Create or retrieve PENDING payment intent for a booking",
)
async def create_payment_intent(
    req: PaymentCreateIntentRequest,
    service: PaymentService = Depends(get_payment_service),
) -> ApiResponse[PaymentResponseDTO]:
    payment = await service.create_or_get_intent(
        booking_id=req.booking_id,
        user_id=req.user_id,
        amount=req.amount,
        currency=req.currency,
    )
    dto = PaymentResponseDTO.model_validate(payment)
    return ApiResponse(
        data=dto,
        message="Payment intent created successfully",
    )


@router.post(
    "/checkout",
    response_model=ApiResponse[PaymentCheckoutResponse],
    summary="Generate payment checkout session and redirect URL",
)
async def checkout(
    req: PaymentCheckoutRequest,
    service: PaymentService = Depends(get_payment_service),
) -> ApiResponse[PaymentCheckoutResponse]:
    result = await service.checkout(
        booking_id=req.booking_id,
        user_id=req.user_id,
        amount=req.amount,
        gateway_name=req.gateway,
        order_info=req.order_info,
        return_url=req.return_url,
    )
    return ApiResponse(
        data=PaymentCheckoutResponse(
            payment_url=result.payment_url,
            qr_code_url=result.qr_code_url,
            gateway_reference=result.gateway_reference,
        ),
        message="Checkout session initialized successfully",
    )


@router.get(
    "/{booking_id}/status",
    response_model=ApiResponse[PaymentResponseDTO],
    summary="Get payment status with active reconciliation (Edge Case 1)",
)
async def get_payment_status(
    booking_id: uuid.UUID,
    gateway: str | None = Query(default=None, description="Optional specific gateway to query"),
    service: PaymentService = Depends(get_payment_service),
) -> ApiResponse[PaymentResponseDTO]:
    payment = await service.get_payment_status(booking_id=booking_id, gateway_name=gateway)
    dto = PaymentResponseDTO.model_validate(payment)
    return ApiResponse(
        data=dto,
        message=f"Payment status is {dto.status}",
    )


@router.get(
    "/{booking_id}",
    response_model=ApiResponse[PaymentResponseDTO],
    summary="Get payment details by booking ID",
)
async def get_payment_by_booking_id(
    booking_id: uuid.UUID,
    service: PaymentService = Depends(get_payment_service),
) -> ApiResponse[PaymentResponseDTO]:
    payment = await service.get_payment_status(booking_id=booking_id)
    dto = PaymentResponseDTO.model_validate(payment)
    return ApiResponse(
        data=dto,
        message="Payment retrieved successfully",
    )
