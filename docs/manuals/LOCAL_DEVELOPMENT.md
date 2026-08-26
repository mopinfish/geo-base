# Local development

Start PostGIS and Redis with `docker compose -f docker/docker-compose.yml up -d`. Copy each service's `.env.example` to its runtime environment file. Start the API on port 8000, MCP on 8001 when using HTTP transport, and the admin UI on port 3000 using the commands in the root README.

Use only the dedicated `geo_base_test` database for database tests. Local object-storage and authentication values must not be committed.
