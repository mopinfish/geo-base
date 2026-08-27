# Demo reproduction

The demo uses `hinanbasho-naka-ku.geojson`, a FeatureCollection containing 87 point features.

1. Start PostGIS/Redis, API, MCP, and the admin UI using the root README.
2. Sign in to the admin UI and import `hinanbasho-naka-ku.geojson` as a GeoJSON tileset.
3. Confirm that the imported dataset reports 87 features.
4. Open its map preview and confirm the points appear within Hiroshima City's Naka-ku extent.
5. Connect a compatible MCP client and call the available tileset/feature tools against the imported dataset.

Exact tool availability depends on the checked-out version and configured authentication. Do not use the demo as a performance or production-readiness benchmark.

Data provenance and license details are in [dataset.md](./dataset.md).

The demo dataset contains 87 point features.
