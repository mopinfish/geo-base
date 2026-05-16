# Access Control Review

> English: this page ・ 日本語: [ACCESS_CONTROL_REVIEW.ja.md](./ACCESS_CONTROL_REVIEW.ja.md)

This document reviews geo-base access control as of 2026-05-09, based on the current implementation
of authentication, team sharing, API keys, and tileset access rules.

## Overview

The access-control model is made up of:

- Authentication (`AUTH_PROVIDER=local`, plus the pluggable auth framework)
- Authorization for teams, API keys, and tileset sharing
- DB schema support for team roles, invitations, API key scopes, and rate limiting

## Main Findings

### Critical

- Team-shared tilesets cannot be edited by non-owners through the current write path
- API keys cannot perform write/delete operations in the current router wiring
- `features` and `datasources` still use the older tileset access check and do not fully handle team sharing

### Important

- The team add/remove permission behavior was asymmetrical before Issue #54; that has since been addressed
- Invitation token persistence should be revisited with cleanup-expired work
- Redis rate limiting support was later added and uses a fail-open policy
- Middleware allow-list and portable RLS remain tracked follow-up items

## Key Recommendation

The highest-priority follow-up is to unify authorization checks around the v2 auth context and to make write
paths consistently honor team membership and API key scopes.

## Reference Files

- `api/lib/auth/__init__.py`
- `api/lib/auth/context.py`
- `api/lib/auth/api_key_auth.py`
- `api/lib/routers/teams.py`
- `api/lib/routers/tilesets.py`
- `api/lib/routers/api_keys.py`
- `docker/postgis-init/05_teams_schema.sql`
- `docker/postgis-init/06_api_keys_schema.sql`

## Revision History

- 2026-05-09: Initial audit based on the Phase 3 / Step 3.3-A implementation
