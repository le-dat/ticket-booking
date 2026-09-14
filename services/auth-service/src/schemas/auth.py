# REASON: Defines DTOs for request/response with Pydantic v2 for automatic input validation
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.core.constants import TOKEN_TYPE_BEARER
from src.models.user import Role


# REASON: Validates request payload when a client calls the user registration endpoint
class RegisterRequest(BaseModel):
    # REASON: Automatically validates RFC-compliant email formats
    email: EmailStr = Field(..., description="User registration email address", examples=["customer@ticket.vn"])
    
    # REASON: Enforces password length between 6 and 72 characters (Bcrypt safe boundary)
    password: str = Field(..., min_length=6, max_length=72, description="Password between 6 and 72 characters", examples=["password123"])
    
    # REASON: User full name is required for electronic ticket issuance
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the user", examples=["John Doe"])


# REASON: Validates request payload when a client calls the user login endpoint
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered user email", examples=["customer@ticket.vn"])
    password: str = Field(..., max_length=72, description="User password", examples=["password123"])


# REASON: Returns public user profile data, strictly excluding password_hash
class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    created_at: datetime

    # REASON: from_attributes=True enables Pydantic to read attributes directly from SQLAlchemy model instances
    model_config = ConfigDict(from_attributes=True)


# REASON: Payload returned upon successful login or token refresh, containing both tokens
class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token for Bearer authentication (15 minutes)")
    refresh_token: str = Field(..., description="Random Refresh Token used to obtain a new Access Token (7 days)")
    token_type: str = Field(default=TOKEN_TYPE_BEARER, description="Token type (always bearer)")
    expires_in: int = Field(default=900, description="Access Token lifetime in seconds (900s = 15 minutes)")
    user: UserResponse = Field(..., description="Summary of the authenticated user")


# REASON: Payload required to obtain a new token pair when the access token expires
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid Refresh Token issued by server upon login")


# REASON: Payload required to log out and revoke a refresh token
class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, description="Optional Refresh Token to revoke upon logout")
