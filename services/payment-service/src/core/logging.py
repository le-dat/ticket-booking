import logging
from src.middleware.correlation_id import CorrelationIdLogFilter


def setup_logging() -> None:
    """Configure root logger with standard format containing trace_id."""
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] [trace_id=%(correlation_id)s] %(name)s: %(message)s")
    )
    log_handler.addFilter(CorrelationIdLogFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [log_handler]
