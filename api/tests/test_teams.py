"""Tests for Team models and functionality."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from lib.models.team import (
    TeamRole, InvitationStatus, PermissionLevel,
    TeamCreate, TeamUpdate, TeamResponse,
    TeamMemberAdd, TeamMemberUpdate, TeamMemberResponse,
    TeamInvitationCreate, TeamInvitationAccept,
    TeamTilesetAdd, TeamTilesetUpdate,
    PermissionCheckRequest, TeamOwnershipTransfer,
    UserTeamResponse,
    generate_invitation_token, generate_slug, validate_slug,
)


class TestTeamRole:
    def test_role_values(self):
        assert TeamRole.OWNER.value == "owner"
        assert TeamRole.ADMINISTRATOR.value == "administrator"
        assert TeamRole.MEMBER.value == "member"
        assert TeamRole.GUEST.value == "guest"
    
    def test_can_delete_property(self):
        assert TeamRole.OWNER.can_delete is True
        assert TeamRole.ADMINISTRATOR.can_delete is True
        assert TeamRole.MEMBER.can_delete is False
        assert TeamRole.GUEST.can_delete is False
    
    def test_can_write_property(self):
        assert TeamRole.OWNER.can_write is True
        assert TeamRole.ADMINISTRATOR.can_write is True
        assert TeamRole.MEMBER.can_write is True
        assert TeamRole.GUEST.can_write is False
    
    def test_can_manage_team_property(self):
        assert TeamRole.OWNER.can_manage_team is True
        assert TeamRole.ADMINISTRATOR.can_manage_team is True
        assert TeamRole.MEMBER.can_manage_team is False
        assert TeamRole.GUEST.can_manage_team is False
    
    def test_can_delete_team_property(self):
        assert TeamRole.OWNER.can_delete_team is True
        assert TeamRole.ADMINISTRATOR.can_delete_team is False
        assert TeamRole.MEMBER.can_delete_team is False
        assert TeamRole.GUEST.can_delete_team is False
    
    def test_from_string(self):
        assert TeamRole.from_string("owner") == TeamRole.OWNER
        assert TeamRole.from_string("ADMINISTRATOR") == TeamRole.ADMINISTRATOR
        assert TeamRole.from_string("Member") == TeamRole.MEMBER
    
    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid role"):
            TeamRole.from_string("invalid")


class TestPermissionLevel:
    def test_from_role(self):
        assert PermissionLevel.from_role(TeamRole.OWNER) == PermissionLevel.ADMIN
        assert PermissionLevel.from_role(TeamRole.ADMINISTRATOR) == PermissionLevel.ADMIN
        assert PermissionLevel.from_role(TeamRole.MEMBER) == PermissionLevel.WRITE
        assert PermissionLevel.from_role(TeamRole.GUEST) == PermissionLevel.READ


class TestHelperFunctions:
    def test_generate_invitation_token(self):
        token1 = generate_invitation_token()
        token2 = generate_invitation_token()
        assert token1 != token2
        assert len(token1) > 20
    
    def test_generate_slug(self):
        assert generate_slug("My Team") == "my-team"
        assert generate_slug("Test Project 123") == "test-project-123"
        assert generate_slug("Hello_World") == "hello-world"
    
    def test_validate_slug_valid(self):
        assert validate_slug("my-team") is True
        assert validate_slug("team123") is True
        assert validate_slug("a1") is True
    
    def test_validate_slug_invalid(self):
        assert validate_slug("") is False
        assert validate_slug("a") is False
        assert validate_slug("-invalid") is False
        assert validate_slug("UPPERCASE") is False


class TestTeamCreate:
    def test_valid_create_minimal(self):
        team = TeamCreate(name="Test Team")
        assert team.name == "Test Team"
        assert team.slug == "test-team"
    
    def test_auto_generate_slug(self):
        team = TeamCreate(name="My Awesome Team")
        assert team.slug == "my-awesome-team"
    
    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            TeamCreate(name="")
    
    def test_invalid_slug_format(self):
        with pytest.raises(ValidationError, match="Invalid slug format"):
            TeamCreate(name="Test", slug="Invalid Slug")


class TestTeamUpdate:
    def test_valid_update_name(self):
        update = TeamUpdate(name="New Name")
        assert update.name == "New Name"
    
    def test_update_no_fields(self):
        with pytest.raises(ValidationError, match="At least one field"):
            TeamUpdate()


class TestTeamMemberAdd:
    def test_valid_add_default_role(self):
        member = TeamMemberAdd(user_id="user-123")
        assert member.role == TeamRole.MEMBER
    
    def test_cannot_assign_owner_role(self):
        with pytest.raises(ValidationError, match="Cannot assign 'owner' role"):
            TeamMemberAdd(user_id="user-123", role=TeamRole.OWNER)


class TestTeamMemberUpdate:
    def test_valid_update_role(self):
        update = TeamMemberUpdate(role=TeamRole.ADMINISTRATOR)
        assert update.role == TeamRole.ADMINISTRATOR
    
    def test_cannot_change_to_owner(self):
        with pytest.raises(ValidationError, match="Cannot change role to 'owner'"):
            TeamMemberUpdate(role=TeamRole.OWNER)


class TestTeamInvitationCreate:
    def test_valid_invitation(self):
        invitation = TeamInvitationCreate(email="test@example.com")
        assert invitation.email == "test@example.com"
        assert invitation.role == TeamRole.MEMBER
        assert invitation.expires_in_days == 7
    
    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            TeamInvitationCreate(email="not-an-email")
    
    def test_cannot_invite_as_owner(self):
        with pytest.raises(ValidationError, match="Cannot invite someone as 'owner'"):
            TeamInvitationCreate(email="test@example.com", role=TeamRole.OWNER)


class TestPermissionCheckRequest:
    def test_valid_request(self):
        request = PermissionCheckRequest(user_id="user-123", tileset_id="tileset-456", action="read")
        assert request.action == "read"
    
    def test_invalid_action(self):
        with pytest.raises(ValidationError, match="Invalid action"):
            PermissionCheckRequest(user_id="user", tileset_id="tileset", action="invalid")


class TestTeamOwnershipTransfer:
    def test_valid_transfer(self):
        transfer = TeamOwnershipTransfer(new_owner_id="user-123456789")
        assert transfer.new_owner_id == "user-123456789"
    
    def test_invalid_user_id(self):
        with pytest.raises(ValidationError, match="Invalid user ID"):
            TeamOwnershipTransfer(new_owner_id="short")


class TestPermissionMatrix:
    def test_owner_permissions(self):
        role = TeamRole.OWNER
        assert role.can_write is True
        assert role.can_delete is True
        assert role.can_manage_team is True
        assert role.can_delete_team is True
    
    def test_guest_permissions(self):
        role = TeamRole.GUEST
        assert role.can_write is False
        assert role.can_delete is False
        assert role.can_manage_team is False
        assert role.can_delete_team is False
