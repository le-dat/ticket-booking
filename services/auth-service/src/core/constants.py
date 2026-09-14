# REASON: Centralized management of application constants and machine-readable error codes
import enum


class ErrorCode(str, enum.Enum):
    """Standard machine-readable error codes for Client/Frontend."""
    # Standard HTTP errors
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Business-specific Auth errors
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_REVOKED = "TOKEN_REVOKED"


# REASON: Default access token type according to RFC 6750
TOKEN_TYPE_BEARER = "bearer"

# REASON: Dummy Bcrypt hash (cost=12) to prevent timing attack (User Enumeration) when email does not exist
DUMMY_BCRYPT_HASH = "$2b$12$e88gHzq2sJ7zN3rG/5Ffquz9t6UqvQ4Z4tZ1h6KjJmHqO.Y5wR9j6"
