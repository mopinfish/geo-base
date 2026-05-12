"""
Pydantic models for API Key operations.
"""

import hashlib
import re
import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# =============================================================================
# Constants
# =============================================================================

API_KEY_PREFIX = "gb"
API_KEY_LENGTH = 32  # Random part length
VALID_SCOPES = {"read", "write", "delete", "admin"}


# =============================================================================
# Enums
# =============================================================================


class ApiKeyScope(str, Enum):
    """API key permission scopes."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

    @classmethod
    def from_string(cls, value: str) -> "ApiKeyScope":
        """Create scope from string."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"Invalid scope '{value}'. Must be one of: {', '.join(s.value for s in cls)}"
            )

    def includes(self, other: "ApiKeyScope") -> bool:
        """Check if this scope includes another scope."""
        hierarchy = {
            ApiKeyScope.READ: 1,
            ApiKeyScope.WRITE: 2,
            ApiKeyScope.DELETE: 3,
            ApiKeyScope.ADMIN: 4,
        }
        return hierarchy.get(self, 0) >= hierarchy.get(other, 0)


class ApiKeyEnvironment(str, Enum):
    """API key environment types."""

    LIVE = "live"
    TEST = "test"


# =============================================================================
# Helper Functions
# =============================================================================


def generate_api_key(
    environment: ApiKeyEnvironment = ApiKeyEnvironment.LIVE,
) -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, prefix, key_hash)
    """
    random_part = secrets.token_urlsafe(API_KEY_LENGTH)
    # prefix は DB 側 VARCHAR(12) 制約に合わせて 12 文字以内（"gb_live_xxxx" / "gb_test_xxxx"）。
    # スキーマコメント "gb_live_abc1" の意図に揃える。以前は [:8] だったため
    # 16 文字の prefix が生成され "value too long for type character varying(12)" で
    # POST /api/api-keys が 500 になっていた（issue #79）。
    prefix = f"{API_KEY_PREFIX}_{environment.value}_{random_part[:4]}"
    full_key = f"{API_KEY_PREFIX}_{environment.value}_{random_part}"
    key_hash = hash_api_key(full_key)
    return full_key, prefix, key_hash


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


def validate_api_key_format(key: str) -> bool:
    """Validate API key format."""
    pattern = rf"^{API_KEY_PREFIX}_(live|test)_[A-Za-z0-9_-]{{32,}}$"
    return bool(re.match(pattern, key))


def mask_api_key(prefix: str) -> str:
    """Create a masked display version of an API key."""
    return f"{prefix}{'*' * 20}"


# =============================================================================
# Request Models
# =============================================================================


class ApiKeyCreate(BaseModel):
    """Model for creating a new API key."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Human-readable name for the key"
    )
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    team_id: Optional[str] = Field(None, description="Optional team to associate the key with")
    scopes: List[ApiKeyScope] = Field(
        default=[ApiKeyScope.READ], description="Permission scopes for this key"
    )
    rate_limit_per_minute: int = Field(
        default=60, ge=1, le=10000, description="Requests per minute limit"
    )
    rate_limit_per_day: int = Field(
        default=10000, ge=1, le=1000000, description="Requests per day limit"
    )
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Days until expiration (optional)"
    )
    environment: ApiKeyEnvironment = Field(
        default=ApiKeyEnvironment.LIVE, description="Key environment"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: List[ApiKeyScope]) -> List[ApiKeyScope]:
        """Ensure at least one scope is provided."""
        if not v:
            return [ApiKeyScope.READ]
        return list(set(v))  # Remove duplicates

    @model_validator(mode="after")
    def validate_rate_limits(self) -> "ApiKeyCreate":
        """Ensure rate limits are sensible."""
        if self.rate_limit_per_minute * 60 * 24 < self.rate_limit_per_day:
            # This is fine - daily limit is less restrictive
            pass
        return self


class ApiKeyUpdate(BaseModel):
    """Model for updating an API key."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    scopes: Optional[List[ApiKeyScope]] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_per_day: Optional[int] = Field(None, ge=1, le=1000000)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "ApiKeyUpdate":
        """Ensure at least one field is provided for update."""
        if all(
            getattr(self, field) is None
            for field in [
                "name",
                "description",
                "scopes",
                "rate_limit_per_minute",
                "rate_limit_per_day",
                "is_active",
                "metadata",
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        return self


class ApiKeyRevoke(BaseModel):
    """Model for revoking an API key."""

    reason: Optional[str] = Field(None, max_length=500, description="Reason for revocation")


# =============================================================================
# Response Models
# =============================================================================


class ApiKeyResponse(BaseModel):
    """Response model for API key (without the actual key)."""

    id: str
    name: str
    description: Optional[str] = None
    prefix: str
    user_id: str
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    scopes: List[str]
    rate_limit_per_minute: int
    rate_limit_per_day: int
    is_active: bool
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    is_expired: bool = False
    is_revoked: bool = False
    masked_key: str = ""

    @model_validator(mode="after")
    def compute_fields(self) -> "ApiKeyResponse":
        """Compute derived fields.

        `expires_at` は DB の TIMESTAMPTZ から tz-aware datetime として復元される
        ケースと、create 経路で `datetime.utcnow()` (naive) として作られるケースが
        混在するので、比較前にどちらか一方に揃える。`datetime.now(timezone.utc)` を
        基準にし、naive 側は UTC として interpret する。
        """
        if self.expires_at is not None:
            exp = self.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            self.is_expired = exp < datetime.now(timezone.utc)
        else:
            self.is_expired = False
        self.is_revoked = self.revoked_at is not None
        self.masked_key = mask_api_key(self.prefix)
        return self

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Response model when creating a new API key (includes the actual key)."""

    key: str = Field(..., description="The full API key - only shown once!")

    model_config = {"from_attributes": True}


class ApiKeyListResponse(BaseModel):
    """Response model for listing API keys."""

    keys: List[ApiKeyResponse]
    total: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# Usage Statistics Models
# =============================================================================


class ApiKeyUsageDay(BaseModel):
    """Usage statistics for a single day."""

    date: str
    requests: int
    errors: int
    avg_response_time: float


class ApiKeyUsageStats(BaseModel):
    """Usage statistics for an API key."""

    key_id: str
    total_requests: int
    avg_response_time_ms: float
    error_count: int
    success_rate: float
    requests_by_day: List[ApiKeyUsageDay]


class ApiKeyUsageLogEntry(BaseModel):
    """Single usage log entry."""

    id: str
    endpoint: str
    method: str
    status_code: Optional[int]
    response_time_ms: Optional[int]
    ip_address: Optional[str]
    created_at: datetime


class ApiKeyUsageLogResponse(BaseModel):
    """Response model for usage logs."""

    logs: List[ApiKeyUsageLogEntry]
    total: int
    key_id: str


# =============================================================================
# Rate Limit Models
# =============================================================================


class RateLimitStatus(BaseModel):
    """Current rate limit status for an API key."""

    key_id: str
    minute_limit: int
    minute_used: int
    minute_remaining: int
    day_limit: int
    day_used: int
    day_remaining: int
    is_limited: bool = False

    @model_validator(mode="after")
    def compute_is_limited(self) -> "RateLimitStatus":
        """Check if rate limited."""
        self.is_limited = self.minute_remaining <= 0 or self.day_remaining <= 0
        return self


# =============================================================================
# Validation Models
# =============================================================================


class ApiKeyValidationRequest(BaseModel):
    """Request to validate an API key."""

    key: str = Field(..., min_length=20, description="The API key to validate")
    required_scope: Optional[ApiKeyScope] = Field(
        None, description="Required scope for the operation"
    )


class ApiKeyValidationResponse(BaseModel):
    """Response from API key validation."""

    valid: bool
    key_id: Optional[str] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    scopes: List[str] = []
    has_required_scope: bool = True
    rate_limit_status: Optional[RateLimitStatus] = None
    error: Optional[str] = None
