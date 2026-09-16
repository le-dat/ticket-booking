from src.core.config import settings
from src.gateways.base import BasePaymentGateway
from src.gateways.mock.provider import MockGatewayProvider
from src.gateways.stripe.provider import StripeGatewayProvider


class PaymentGatewayFactory:
    """Registry and resolver factory for payment gateway plugins."""

    _providers: dict[str, type[BasePaymentGateway]] = {
        "mock": MockGatewayProvider,
        "stripe": StripeGatewayProvider,
    }

    @classmethod
    def register_gateway(cls, name: str, provider_cls: type[BasePaymentGateway]) -> None:
        """Register or override a gateway provider plugin."""
        cls._providers[name.lower()] = provider_cls

    @classmethod
    def get_gateway(cls, gateway_name: str | None = None) -> BasePaymentGateway:
        """Resolve gateway instance by name or fallback to application default setting."""
        selected_name = (gateway_name or settings.DEFAULT_PAYMENT_GATEWAY).lower()
        provider_cls = cls._providers.get(selected_name)
        if not provider_cls:
            raise ValueError(
                f"Unsupported payment gateway: '{selected_name}'. Available gateways: {list(cls._providers.keys())}"
            )
        return provider_cls()
