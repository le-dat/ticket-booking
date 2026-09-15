# REASON: User model definition following SQLAlchemy 2.0 Mapped & Role Enum
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


# REASON: Enum defining 3 user roles in ticket booking system
class Role(str, enum.Enum):
    CUSTOMER = "CUSTOMER"    # REASON: General ticket purchaser
    ORGANIZER = "ORGANIZER"  # REASON: Event organizer / cinema manager
    ADMIN = "ADMIN"          # REASON: System administrator with full permissions


class User(Base):
    # REASON: Database table name is users (plural lowercase)
    __tablename__ = "users"

    # REASON: Primary key UUID v4 prevents ID enumeration and distributes well in microservices
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # REASON: Unique email indexed to optimize lookup performance during Login/Register
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # REASON: Store hashed password with Bcrypt, never plaintext
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # REASON: Display name of the user printed on electronic tickets (E-Ticket)
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # REASON: Role-based authorization defaulting to CUSTOMER
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role_enum"),
        default=Role.CUSTOMER,
        nullable=False,
    )

    # REASON: Record creation timestamp in UTC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # REASON: Record update timestamp automatically updated on change
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship with RefreshTokens owned by this user
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
