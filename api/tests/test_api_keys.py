"""
Tests for API Key models and functionality.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from lib.models.api_key import (
    # Enums
    ApiKeyScope,
    ApiKeyEnvironment,
    # Models
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyRevoke,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    ApiKeyUsageStats,
    RateLimitStatus,
    # Helpers
    generate_api_key,
    hash_api_key,
    validate_api_key_format,
    mask_api_key,
)


# =============================================================================
# ApiKeyScope Tests
# =============================================================================

class TestApiKeyScope:
    """Tests for ApiKeyScope enum."""
    
    def test_scope_values(self):
        """Test scope enum values."""
        assert ApiKeyScope.READ.value == "read"
        assert ApiKeyScope.WRITE.value == "write"
        assert ApiKeyScope.DELETE.value == "delete"
        assert ApiKeyScope.ADMIN.value == "admin"
    
    def test_from_string(self):
        """Test creating scope from string."""
        assert ApiKeyScope.from_string("read") == ApiKeyScope.READ
        assert ApiKeyScope.from_string("WRITE") == ApiKeyScope.WRITE
        assert ApiKeyScope.from_string("Delete") == ApiKeyScope.DELETE
    
    def test_from_string_invalid(self):
        """Test invalid scope string raises error."""
        with pytest.raises(ValueError, match="Invalid scope"):
            ApiKeyScope.from_string("invalid")
    
    def test_includes_hierarchy(self):
        """Test scope inclusion hierarchy."""
        # Admin includes all
        assert ApiKeyScope.ADMIN.includes(ApiKeyScope.READ) is True
        assert ApiKeyScope.ADMIN.includes(ApiKeyScope.WRITE) is True
        assert ApiKeyScope.ADMIN.includes(ApiKeyScope.DELETE) is True
        assert ApiKeyScope.ADMIN.includes(ApiKeyScope.ADMIN) is True
        
        # Delete includes write and read
        assert ApiKeyScope.DELETE.includes(ApiKeyScope.READ) is True
        assert ApiKeyScope.DELETE.includes(ApiKeyScope.WRITE) is True
        assert ApiKeyScope.DELETE.includes(ApiKeyScope.DELETE) is True
        assert ApiKeyScope.DELETE.includes(ApiKeyScope.ADMIN) is False
        
        # Write includes read
        assert ApiKeyScope.WRITE.includes(ApiKeyScope.READ) is True
        assert ApiKeyScope.WRITE.includes(ApiKeyScope.WRITE) is True
        assert ApiKeyScope.WRITE.includes(ApiKeyScope.DELETE) is False
        
        # Read only includes itself
        assert ApiKeyScope.READ.includes(ApiKeyScope.READ) is True
        assert ApiKeyScope.READ.includes(ApiKeyScope.WRITE) is False


class TestApiKeyEnvironment:
    """Tests for ApiKeyEnvironment enum."""
    
    def test_environment_values(self):
        """Test environment enum values."""
        assert ApiKeyEnvironment.LIVE.value == "live"
        assert ApiKeyEnvironment.TEST.value == "test"


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_generate_api_key_live(self):
        """Test generating a live API key."""
        full_key, prefix, key_hash = generate_api_key(ApiKeyEnvironment.LIVE)
        
        assert full_key.startswith("gb_live_")
        assert prefix.startswith("gb_live_")
        assert len(prefix) == 16  # gb_live_ (8) + 8 random chars
        assert len(key_hash) == 64  # SHA-256 hex
        assert key_hash == hash_api_key(full_key)
    
    def test_generate_api_key_test(self):
        """Test generating a test API key."""
        full_key, prefix, key_hash = generate_api_key(ApiKeyEnvironment.TEST)
        
        assert full_key.startswith("gb_test_")
        assert prefix.startswith("gb_test_")
    
    def test_generate_api_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = [generate_api_key()[0] for _ in range(10)]
        assert len(set(keys)) == 10
    
    def test_hash_api_key(self):
        """Test API key hashing."""
        key = "gb_live_test1234567890abcdef"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 64  # SHA-256
        assert hash_api_key("different_key") != hash1
    
    def test_validate_api_key_format_valid(self):
        """Test valid API key formats."""
        assert validate_api_key_format("gb_live_abcdefghijklmnopqrstuvwxyz123456") is True
        assert validate_api_key_format("gb_test_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456") is True
        assert validate_api_key_format("gb_live_abcdef123456789012345678901234567") is True
    
    def test_validate_api_key_format_invalid(self):
        """Test invalid API key formats."""
        assert validate_api_key_format("invalid") is False
        assert validate_api_key_format("gb_invalid_abc") is False
        assert validate_api_key_format("xx_live_abcdef") is False
        assert validate_api_key_format("") is False
    
    def test_mask_api_key(self):
        """Test API key masking."""
        masked = mask_api_key("gb_live_abc12345")
        assert masked == "gb_live_abc12345" + "*" * 20
        assert "abc12345" in masked


# =============================================================================
# ApiKeyCreate Tests
# =============================================================================

class TestApiKeyCreate:
    """Tests for ApiKeyCreate model."""
    
    def test_valid_create_minimal(self):
        """Test valid key creation with minimal fields."""
        key = ApiKeyCreate(name="Test Key")
        
        assert key.name == "Test Key"
        assert key.description is None
        assert key.team_id is None
        assert key.scopes == [ApiKeyScope.READ]
        assert key.rate_limit_per_minute == 60
        assert key.rate_limit_per_day == 10000
        assert key.expires_in_days is None
        assert key.environment == ApiKeyEnvironment.LIVE
    
    def test_valid_create_full(self):
        """Test valid key creation with all fields."""
        key = ApiKeyCreate(
            name="Production API Key",
            description="For production use",
            team_id="team-123",
            scopes=[ApiKeyScope.READ, ApiKeyScope.WRITE],
            rate_limit_per_minute=100,
            rate_limit_per_day=50000,
            expires_in_days=90,
            environment=ApiKeyEnvironment.LIVE,
            metadata={"purpose": "integration"}
        )
        
        assert key.name == "Production API Key"
        assert key.description == "For production use"
        assert key.team_id == "team-123"
        assert ApiKeyScope.READ in key.scopes
        assert ApiKeyScope.WRITE in key.scopes
        assert key.rate_limit_per_minute == 100
        assert key.rate_limit_per_day == 50000
        assert key.expires_in_days == 90
        assert key.metadata == {"purpose": "integration"}
    
    def test_name_too_short(self):
        """Test name validation - too short."""
        with pytest.raises(ValidationError):
            ApiKeyCreate(name="")
    
    def test_name_too_long(self):
        """Test name validation - too long."""
        with pytest.raises(ValidationError):
            ApiKeyCreate(name="x" * 256)
    
    def test_empty_scopes_defaults_to_read(self):
        """Test that empty scopes defaults to read."""
        key = ApiKeyCreate(name="Test", scopes=[])
        assert key.scopes == [ApiKeyScope.READ]
    
    def test_duplicate_scopes_removed(self):
        """Test that duplicate scopes are removed."""
        key = ApiKeyCreate(
            name="Test",
            scopes=[ApiKeyScope.READ, ApiKeyScope.READ, ApiKeyScope.WRITE]
        )
        assert len(key.scopes) == 2
    
    def test_rate_limit_bounds(self):
        """Test rate limit bounds."""
        # Valid bounds
        ApiKeyCreate(name="Test", rate_limit_per_minute=1)
        ApiKeyCreate(name="Test", rate_limit_per_minute=10000)
        ApiKeyCreate(name="Test", rate_limit_per_day=1)
        ApiKeyCreate(name="Test", rate_limit_per_day=1000000)
        
        # Invalid bounds
        with pytest.raises(ValidationError):
            ApiKeyCreate(name="Test", rate_limit_per_minute=0)
        with pytest.raises(ValidationError):
            ApiKeyCreate(name="Test", rate_limit_per_minute=10001)
        with pytest.raises(ValidationError):
            ApiKeyCreate(name="Test", rate_limit_per_day=0)
    
    def test_expires_in_days_bounds(self):
        """Test expires_in_days bounds."""
        # Valid
        ApiKeyCreate(name="Test", expires_in_days=1)
        ApiKeyCreate(name="Test", expires_in_days=365)
        
        # Invalid
        with pytest.raises(ValidationError):
            ApiKeyCreate(name="Test", expires_in_days=0)
        with pytest.raises(ValidationError):
            ApiKeyCreate(name="Test", expires_in_days=366)


# =============================================================================
# ApiKeyUpdate Tests
# =============================================================================

class TestApiKeyUpdate:
    """Tests for ApiKeyUpdate model."""
    
    def test_valid_update_name(self):
        """Test valid name update."""
        update = ApiKeyUpdate(name="New Name")
        assert update.name == "New Name"
    
    def test_valid_update_scopes(self):
        """Test valid scopes update."""
        update = ApiKeyUpdate(scopes=[ApiKeyScope.ADMIN])
        assert update.scopes == [ApiKeyScope.ADMIN]
    
    def test_valid_update_rate_limits(self):
        """Test valid rate limit update."""
        update = ApiKeyUpdate(
            rate_limit_per_minute=120,
            rate_limit_per_day=20000
        )
        assert update.rate_limit_per_minute == 120
        assert update.rate_limit_per_day == 20000
    
    def test_valid_update_is_active(self):
        """Test valid is_active update."""
        update = ApiKeyUpdate(is_active=False)
        assert update.is_active is False
    
    def test_update_no_fields(self):
        """Test update with no fields raises error."""
        with pytest.raises(ValidationError, match="At least one field"):
            ApiKeyUpdate()


# =============================================================================
# ApiKeyRevoke Tests
# =============================================================================

class TestApiKeyRevoke:
    """Tests for ApiKeyRevoke model."""
    
    def test_valid_revoke_no_reason(self):
        """Test valid revoke without reason."""
        revoke = ApiKeyRevoke()
        assert revoke.reason is None
    
    def test_valid_revoke_with_reason(self):
        """Test valid revoke with reason."""
        revoke = ApiKeyRevoke(reason="Security concern")
        assert revoke.reason == "Security concern"
    
    def test_reason_too_long(self):
        """Test reason too long raises error."""
        with pytest.raises(ValidationError):
            ApiKeyRevoke(reason="x" * 501)


# =============================================================================
# Response Model Tests
# =============================================================================

class TestApiKeyResponse:
    """Tests for ApiKeyResponse model."""
    
    def test_valid_response(self):
        """Test valid response creation."""
        now = datetime.utcnow()
        response = ApiKeyResponse(
            id="key-123",
            name="Test Key",
            prefix="gb_live_abc12345",
            user_id="user-456",
            scopes=["read", "write"],
            rate_limit_per_minute=60,
            rate_limit_per_day=10000,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        assert response.id == "key-123"
        assert response.name == "Test Key"
        assert response.is_expired is False
        assert response.is_revoked is False
        assert "gb_live_abc12345" in response.masked_key
    
    def test_expired_key(self):
        """Test expired key detection."""
        past = datetime.utcnow() - timedelta(days=1)
        response = ApiKeyResponse(
            id="key-123",
            name="Test Key",
            prefix="gb_live_abc12345",
            user_id="user-456",
            scopes=["read"],
            rate_limit_per_minute=60,
            rate_limit_per_day=10000,
            is_active=True,
            expires_at=past,
            created_at=past,
            updated_at=past
        )
        
        assert response.is_expired is True
    
    def test_revoked_key(self):
        """Test revoked key detection."""
        now = datetime.utcnow()
        response = ApiKeyResponse(
            id="key-123",
            name="Test Key",
            prefix="gb_live_abc12345",
            user_id="user-456",
            scopes=["read"],
            rate_limit_per_minute=60,
            rate_limit_per_day=10000,
            is_active=False,
            revoked_at=now,
            created_at=now,
            updated_at=now
        )
        
        assert response.is_revoked is True


class TestApiKeyCreatedResponse:
    """Tests for ApiKeyCreatedResponse model."""
    
    def test_includes_key(self):
        """Test that created response includes the actual key."""
        now = datetime.utcnow()
        response = ApiKeyCreatedResponse(
            id="key-123",
            name="Test Key",
            prefix="gb_live_abc12345",
            user_id="user-456",
            scopes=["read"],
            rate_limit_per_minute=60,
            rate_limit_per_day=10000,
            is_active=True,
            created_at=now,
            updated_at=now,
            key="gb_live_fullkeyvalue1234567890"
        )
        
        assert response.key == "gb_live_fullkeyvalue1234567890"


# =============================================================================
# RateLimitStatus Tests
# =============================================================================

class TestRateLimitStatus:
    """Tests for RateLimitStatus model."""
    
    def test_not_limited(self):
        """Test not rate limited status."""
        status = RateLimitStatus(
            key_id="key-123",
            minute_limit=60,
            minute_used=30,
            minute_remaining=30,
            day_limit=10000,
            day_used=5000,
            day_remaining=5000
        )
        
        assert status.is_limited is False
    
    def test_minute_limited(self):
        """Test minute rate limited status."""
        status = RateLimitStatus(
            key_id="key-123",
            minute_limit=60,
            minute_used=60,
            minute_remaining=0,
            day_limit=10000,
            day_used=100,
            day_remaining=9900
        )
        
        assert status.is_limited is True
    
    def test_day_limited(self):
        """Test day rate limited status."""
        status = RateLimitStatus(
            key_id="key-123",
            minute_limit=60,
            minute_used=10,
            minute_remaining=50,
            day_limit=10000,
            day_used=10000,
            day_remaining=0
        )
        
        assert status.is_limited is True


# =============================================================================
# ApiKeyUsageStats Tests
# =============================================================================

class TestApiKeyUsageStats:
    """Tests for ApiKeyUsageStats model."""
    
    def test_valid_stats(self):
        """Test valid usage stats."""
        stats = ApiKeyUsageStats(
            key_id="key-123",
            total_requests=1000,
            avg_response_time_ms=45.5,
            error_count=10,
            success_rate=99.0,
            requests_by_day=[]
        )
        
        assert stats.total_requests == 1000
        assert stats.avg_response_time_ms == 45.5
        assert stats.error_count == 10
        assert stats.success_rate == 99.0


# =============================================================================
# Permission Matrix Tests
# =============================================================================

class TestPermissionMatrix:
    """Tests for permission hierarchy."""
    
    def test_read_permissions(self):
        """Test read scope permissions."""
        read = ApiKeyScope.READ
        assert read.includes(ApiKeyScope.READ) is True
        assert read.includes(ApiKeyScope.WRITE) is False
        assert read.includes(ApiKeyScope.DELETE) is False
        assert read.includes(ApiKeyScope.ADMIN) is False
    
    def test_write_permissions(self):
        """Test write scope permissions."""
        write = ApiKeyScope.WRITE
        assert write.includes(ApiKeyScope.READ) is True
        assert write.includes(ApiKeyScope.WRITE) is True
        assert write.includes(ApiKeyScope.DELETE) is False
        assert write.includes(ApiKeyScope.ADMIN) is False
    
    def test_delete_permissions(self):
        """Test delete scope permissions."""
        delete = ApiKeyScope.DELETE
        assert delete.includes(ApiKeyScope.READ) is True
        assert delete.includes(ApiKeyScope.WRITE) is True
        assert delete.includes(ApiKeyScope.DELETE) is True
        assert delete.includes(ApiKeyScope.ADMIN) is False
    
    def test_admin_permissions(self):
        """Test admin scope has all permissions."""
        admin = ApiKeyScope.ADMIN
        assert admin.includes(ApiKeyScope.READ) is True
        assert admin.includes(ApiKeyScope.WRITE) is True
        assert admin.includes(ApiKeyScope.DELETE) is True
        assert admin.includes(ApiKeyScope.ADMIN) is True
