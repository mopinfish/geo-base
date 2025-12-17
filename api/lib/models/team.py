"""
Pydantic models for Team operations.
"""

import re
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr


SLUG_PATTERN = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')
DEFAULT_INVITATION_EXPIRY_DAYS = 7
INVITATION_TOKEN_LENGTH = 64


class TeamRole(str, Enum):
    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    MEMBER = "member"
    GUEST = "guest"
    
    @property
    def can_delete(self) -> bool:
        return self in (TeamRole.OWNER, TeamRole.ADMINISTRATOR)
    
    @property
    def can_write(self) -> bool:
        return self in (TeamRole.OWNER, TeamRole.ADMINISTRATOR, TeamRole.MEMBER)
    
    @property
    def can_manage_team(self) -> bool:
        return self in (TeamRole.OWNER, TeamRole.ADMINISTRATOR)
    
    @property
    def can_delete_team(self) -> bool:
        return self == TeamRole.OWNER
    
    @classmethod
    def from_string(cls, value: str) -> "TeamRole":
        try:
            return cls(value.lower())
        except ValueError:
            valid_roles = [r.value for r in cls]
            raise ValueError(f"Invalid role '{value}'. Must be one of: {', '.join(valid_roles)}")


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    
    @classmethod
    def from_role(cls, role: TeamRole) -> "PermissionLevel":
        if role in (TeamRole.OWNER, TeamRole.ADMINISTRATOR):
            return cls.ADMIN
        elif role == TeamRole.MEMBER:
            return cls.WRITE
        else:
            return cls.READ


def generate_invitation_token() -> str:
    return secrets.token_urlsafe(INVITATION_TOKEN_LENGTH)


def generate_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def validate_slug(slug: str) -> bool:
    if not slug or len(slug) < 2 or len(slug) > 100:
        return False
    return SLUG_PATTERN.match(slug) is not None


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    settings: Optional[Dict[str, Any]] = None
    
    @field_validator('slug')
    @classmethod
    def validate_slug_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_lower = v.lower()
        if not validate_slug(v_lower):
            raise ValueError("Invalid slug format")
        return v_lower
    
    @model_validator(mode='after')
    def generate_slug_if_not_provided(self) -> 'TeamCreate':
        if self.slug is None:
            self.slug = generate_slug(self.name)
            if not validate_slug(self.slug):
                self.slug = re.sub(r'[^a-z0-9]', '', self.name.lower())[:50]
        return self


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    settings: Optional[Dict[str, Any]] = None
    
    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'TeamUpdate':
        if self.name is None and self.description is None and self.settings is None:
            raise ValueError("At least one field must be provided for update")
        return self


class TeamResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    owner_id: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    member_count: Optional[int] = None
    tileset_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    teams: List[TeamResponse]
    total: int
    page: int = 1
    page_size: int = 20


class TeamMemberAdd(BaseModel):
    user_id: str
    role: TeamRole = TeamRole.MEMBER
    notification_enabled: bool = True
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: TeamRole) -> TeamRole:
        if v == TeamRole.OWNER:
            raise ValueError("Cannot assign 'owner' role directly")
        return v


class TeamMemberUpdate(BaseModel):
    role: Optional[TeamRole] = None
    notification_enabled: Optional[bool] = None
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[TeamRole]) -> Optional[TeamRole]:
        if v == TeamRole.OWNER:
            raise ValueError("Cannot change role to 'owner'")
        return v
    
    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'TeamMemberUpdate':
        if self.role is None and self.notification_enabled is None:
            raise ValueError("At least one field must be provided for update")
        return self


class TeamMemberResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: TeamRole
    notification_enabled: bool = True
    joined_at: datetime
    updated_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class TeamMemberListResponse(BaseModel):
    members: List[TeamMemberResponse]
    total: int
    team_id: str


class TeamInvitationCreate(BaseModel):
    email: EmailStr
    role: TeamRole = TeamRole.MEMBER
    message: Optional[str] = Field(None, max_length=500)
    expires_in_days: int = Field(DEFAULT_INVITATION_EXPIRY_DAYS, ge=1, le=30)
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: TeamRole) -> TeamRole:
        if v == TeamRole.OWNER:
            raise ValueError("Cannot invite someone as 'owner'")
        return v


class TeamInvitationResponse(BaseModel):
    id: str
    team_id: str
    email: str
    role: TeamRole
    invited_by: str
    message: Optional[str] = None
    token: str
    status: InvitationStatus
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime
    team_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class TeamInvitationAccept(BaseModel):
    token: str = Field(..., min_length=10)


class TeamInvitationListResponse(BaseModel):
    invitations: List[TeamInvitationResponse]
    total: int
    team_id: str


class TeamTilesetAdd(BaseModel):
    tileset_id: str
    permission_level: Optional[PermissionLevel] = None


class TeamTilesetUpdate(BaseModel):
    permission_level: Optional[PermissionLevel] = None


class TeamTilesetResponse(BaseModel):
    id: str
    team_id: str
    tileset_id: str
    added_by: str
    permission_level: Optional[PermissionLevel] = None
    created_at: datetime
    tileset_name: Optional[str] = None
    tileset_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class TeamTilesetListResponse(BaseModel):
    tilesets: List[TeamTilesetResponse]
    total: int
    team_id: str


class PermissionCheckRequest(BaseModel):
    user_id: str
    tileset_id: str
    action: str
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid_actions = {"read", "create", "update", "delete"}
        v_lower = v.lower()
        if v_lower not in valid_actions:
            raise ValueError(f"Invalid action '{v}'. Must be one of: {', '.join(sorted(valid_actions))}")
        return v_lower


class PermissionCheckResponse(BaseModel):
    allowed: bool
    user_id: str
    tileset_id: str
    action: str
    permission_level: Optional[PermissionLevel] = None
    reason: Optional[str] = None


class UserTeamResponse(BaseModel):
    team_id: str
    team_name: str
    team_slug: str
    team_description: Optional[str] = None
    owner_id: str
    role: TeamRole
    joined_at: datetime
    member_count: int = 0
    
    class Config:
        from_attributes = True


class UserTeamsListResponse(BaseModel):
    teams: List[UserTeamResponse]
    total: int
    user_id: str


class TeamOwnershipTransfer(BaseModel):
    new_owner_id: str
    
    @field_validator('new_owner_id')
    @classmethod
    def validate_new_owner(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("Invalid user ID format")
        return v
