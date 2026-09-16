import json
import uuid
from decimal import Decimal
import httpx
from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from src.core.config import settings
from src.gateways.mock.provider import MockGatewayProvider
from src.schemas.response import ApiResponse
from src.schemas.webhook import MockWebhookSimulateRequest

router = APIRouter(prefix="/api/v1/mock-gateway", tags=["mock-gateway"])
mock_provider = MockGatewayProvider()


@router.get("/checkout", response_class=HTMLResponse, summary="Sandbox payment checkout UI for local dev")
async def mock_checkout_page(
    booking_id: uuid.UUID = Query(...),
    amount: Decimal = Query(...),
    ref: str = Query(...),
    order_info: str = Query(default="Vé xem phim / Sự kiện"),
    return_url: str = Query(default=settings.PAYMENT_RETURN_URL),
) -> HTMLResponse:
    """Renders a simple, clean Sandbox checkout page for instant testing."""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mock Payment Gateway Sandbox</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
            .card {{ background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 32px; width: 100%; max-width: 440px; text-align: center; }}
            .badge {{ background: #e0f2fe; color: #0284c7; font-weight: 600; padding: 4px 12px; border-radius: 9999px; font-size: 12px; text-transform: uppercase; display: inline-block; margin-bottom: 12px; }}
            h2 {{ margin: 0 0 8px 0; color: #1e293b; font-size: 20px; }}
            .amount {{ font-size: 32px; font-weight: 700; color: #0f172a; margin: 16px 0; }}
            .info-table {{ width: 100%; margin: 20px 0; border-collapse: collapse; text-align: left; font-size: 14px; }}
            .info-table td {{ padding: 8px 0; border-bottom: 1px solid #f1f5f9; }}
            .info-table td:last-child {{ text-align: right; font-weight: 600; color: #334155; }}
            .btn {{ display: block; width: 100%; padding: 14px; margin-top: 12px; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
            .btn-success {{ background: #10b981; color: white; }}
            .btn-success:hover {{ background: #059669; }}
            .btn-fail {{ background: #f1f5f9; color: #64748b; }}
            .btn-fail:hover {{ background: #e2e8f0; color: #334155; }}
            .qr-box {{ margin: 16px auto; width: 180px; height: 180px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; }}
            .qr-box img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">SANDBOX ENVIRONMENT</span>
            <h2>Cổng Thanh Toán Giả Lập</h2>
            <p style="color: #64748b; font-size: 14px; margin: 0;">Mô phỏng VNPay / MoMo / Stripe</p>
            
            <div class="amount">{amount:,.0f} VND</div>
            
            <div class="qr-box">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=PAYMENT_{booking_id}_{ref}" alt="QR Code" />
            </div>

            <table class="info-table">
                <tr><td style="color:#64748b;">Mã Đơn (Booking ID)</td><td>{str(booking_id)[:8]}...{str(booking_id)[-4:]}</td></tr>
                <tr><td style="color:#64748b;">Mã Giao Dịch Gateway</td><td>{ref}</td></tr>
                <tr><td style="color:#64748b;">Nội dung</td><td>{order_info}</td></tr>
            </table>

            <form method="POST" action="/api/v1/mock-gateway/simulate-webhook">
                <input type="hidden" name="booking_id" value="{booking_id}">
                <input type="hidden" name="transaction_id" value="{ref}">
                <input type="hidden" name="amount" value="{amount}">
                <input type="hidden" name="status" value="SUCCESS">
                <input type="hidden" name="return_url" value="{return_url}">
                <button type="submit" class="btn btn-success">✅ Xác Nhận Thanh Toán Thành Công</button>
            </form>

            <form method="POST" action="/api/v1/mock-gateway/simulate-webhook">
                <input type="hidden" name="booking_id" value="{booking_id}">
                <input type="hidden" name="transaction_id" value="{ref}">
                <input type="hidden" name="amount" value="{amount}">
                <input type="hidden" name="status" value="FAILED">
                <input type="hidden" name="return_url" value="{return_url}">
                <button type="submit" class="btn btn-fail">❌ Hủy / Giả Lập Thất Bại</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/simulate-webhook", summary="Simulate webhook call with HMAC-SHA512 signature")
async def simulate_webhook(request: Request) -> JSONResponse:
    """Constructs a signed payload and POSTs it directly to the webhook handler."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        booking_id = body.get("booking_id")
        transaction_id = body.get("transaction_id") or f"MOCK-SIM-{uuid.uuid4().hex[:8]}"
        amount = body.get("amount", 0)
        status_val = body.get("status", "SUCCESS")
        return_url = body.get("return_url")
    else:
        form = await request.form()
        booking_id = form.get("booking_id")
        transaction_id = form.get("transaction_id") or f"MOCK-SIM-{uuid.uuid4().hex[:8]}"
        amount = form.get("amount", 0)
        status_val = form.get("status", "SUCCESS")
        return_url = form.get("return_url")

    payload = {
        "event": "payment.completed" if status_val == "SUCCESS" else "payment.failed",
        "data": {
            "booking_id": str(booking_id),
            "transaction_id": str(transaction_id),
            "amount": float(amount),
            "status": status_val,
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = mock_provider.sign_payload(body_bytes)

    # Call internal webhook endpoint
    webhook_url = f"http://127.0.0.1:{settings.PORT}/api/v1/payments/webhook"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                webhook_url,
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": signature,
                },
                timeout=5.0,
            )
            webhook_res = resp.json()
        except Exception as exc:
            webhook_res = {"error": f"Failed to call webhook: {str(exc)}"}

    if return_url and "http" in return_url:
        redirect_html = f"""
        <html>
            <head>
                <meta http-equiv="refresh" content="2;url={return_url}?booking_id={booking_id}&status={status_val}">
            </head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h3>Đang hoàn tất thanh toán...</h3>
                <p>Kết quả webhook: {webhook_res.get('status', 'OK')}</p>
                <p>Đang chuyển hướng về ứng dụng trong 2 giây...</p>
                <a href="{return_url}?booking_id={booking_id}&status={status_val}">Bấm vào đây nếu không tự chuyển</a>
            </body>
        </html>
        """
        return HTMLResponse(content=redirect_html)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Webhook simulated successfully",
            "signature": signature,
            "webhook_response": webhook_res,
        },
    )
