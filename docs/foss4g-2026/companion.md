# Presentation companion

The talk frames geo-base through three user actions:

- **Host:** import and keep a team's spatial data in a self-hosted deployment.
- **See:** view the same data through vector tiles and a MapLibre map.
- **Ask:** expose typed geospatial operations through MCP so a compatible AI client can select them from a natural-language request.

The demo imports 87 point features from a Hiroshima City open dataset, previews those points, and queries the same dataset through MCP. The AI client does not receive unrestricted database access; it calls the operations exposed by the MCP server and API.

This is a focused example. Teams should verify format support, authentication, deployment, backups, question fit, and operational limits with their own data before production use.

See the [demo guide](./demo/README.md) and the main [repository README](../../README.md).
