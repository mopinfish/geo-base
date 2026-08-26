# Deployment guide

geo-base consists of independently deployable API, MCP, admin UI, PostgreSQL/PostGIS, object storage, and Redis components. Start from the local Docker environment, then supply equivalent managed or self-hosted services in your target environment.

Keep credentials outside Git, use the `.env.example` files as variable inventories, terminate TLS at the public boundary, restrict database/object-storage access, and rotate authentication secrets before production use. Run the checks in [TESTING.md](./TESTING.md) against a dedicated test database before release.

Deployment-provider configuration is intentionally not prescribed here. Review capacity, backups, monitoring, data residency, access control, and recovery requirements for your organization.
