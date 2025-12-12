# geo-base MCP Server

MCP (Model Context Protocol) Server for geo-base tile server. This enables Claude Desktop to access geographic data from the geo-base tile server.

## Features

### Tileset Tools
- **list_tilesets**: List all available tilesets (vector, raster, PMTiles)
- **get_tileset**: Get detailed information about a specific tileset
- **get_tileset_tilejson**: Get TileJSON metadata for map client integration

### Feature Tools
- **search_features**: Search geographic features with bbox, layer, and filter criteria
- **get_feature**: Get detailed information about a specific feature

### Utility Tools
- **get_tile_url**: Generate URLs for specific map tiles
- **health_check**: Check the health status of the tile server
- **get_server_info**: Get MCP server configuration information

## Installation

### Prerequisites
- Python 3.11+
- uv (Python package manager)
- Claude Desktop (for using the MCP server)

### Setup

```fish
# Navigate to the mcp directory
cd mcp

# Create environment file
cp .env.example .env

# Edit .env to set TILE_SERVER_URL
# For local development: http://localhost:3000
# For production: https://geo-base-puce.vercel.app

# Install dependencies
uv sync

# Run the server (for testing)
uv run python server.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TILE_SERVER_URL` | `http://localhost:3000` | Base URL of the geo-base tile server |
| `API_TOKEN` | (none) | JWT token for authenticated requests |
| `SERVER_NAME` | `geo-base` | MCP server name |
| `SERVER_VERSION` | `0.1.0` | MCP server version |
| `ENVIRONMENT` | `development` | Environment (development/production) |
| `HTTP_TIMEOUT` | `30.0` | HTTP request timeout in seconds |
| `DEBUG` | `false` | Enable debug mode |

### Claude Desktop Configuration

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "geo-base": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/geo-base/mcp",
        "run",
        "python",
        "server.py"
      ],
      "env": {
        "TILE_SERVER_URL": "https://geo-base-puce.vercel.app"
      }
    }
  }
}
```

## Usage Examples

Once configured in Claude Desktop, you can use natural language to interact with the geo-base tile server:

### List Tilesets
```
Show me all available tilesets
```

### Search Features
```
Find all features in Tokyo area (bbox: 139.5,35.5,140.0,36.0)
```

### Get Tileset Information
```
Get details about tileset {tileset_id}
```

### Health Check
```
Check if the tile server is healthy
```

## Deployment (Fly.io)

For remote deployment using Fly.io:

### Prerequisites

1. [Fly.io account](https://fly.io/signup)
2. [Fly CLI](https://fly.io/docs/flyctl/install/) installed

### First-time Setup

```fish
# Install Fly CLI (if not installed)
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
fly auth login

# Navigate to mcp directory
cd mcp

# Launch the app (first time only)
fly launch --no-deploy

# Set secrets (optional, for authenticated API access)
fly secrets set API_TOKEN=your-jwt-token

# Deploy
fly deploy
```

### Updating Deployment

```fish
cd mcp
fly deploy
```

### Connecting Claude Desktop to Remote MCP Server

After deploying to Fly.io, update your Claude Desktop configuration to use the remote server:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "geo-base-remote": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "https://geo-base-mcp.fly.dev/sse",
        "--transport=sse"
      ]
    }
  }
}
```

> **Note**: You need `mcp-proxy` to connect to remote SSE endpoints. Install it with:
> ```fish
> uv tool install mcp-proxy
> ```

### Transport Modes

The MCP server supports multiple transport modes:

| Mode | Environment Variable | Use Case |
|------|---------------------|----------|
| `stdio` | `MCP_TRANSPORT=stdio` | Local Claude Desktop (default) |
| `sse` | `MCP_TRANSPORT=sse` | Remote connections via Fly.io |
| `streamable-http` | `MCP_TRANSPORT=streamable-http` | Alternative HTTP transport |

### Monitoring

```fish
# View logs
fly logs

# Check app status
fly status

# Open dashboard
fly dashboard
```

## Development

### Running Tests

```fish
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest
```

### Code Formatting

```fish
# Format code
uv run black .

# Lint code
uv run ruff check .
```

## API Reference

### Tileset Tools

#### `list_tilesets(type?, is_public?)`
Lists available tilesets from the tile server.

**Parameters:**
- `type` (optional): Filter by type ('vector', 'raster', 'pmtiles')
- `is_public` (optional): Filter by public/private status

**Returns:** List of tilesets with id, name, description, type, format, and zoom range.

#### `get_tileset(tileset_id)`
Gets detailed information about a specific tileset.

**Parameters:**
- `tileset_id`: UUID of the tileset

**Returns:** Tileset details including bounds, center, metadata.

#### `get_tileset_tilejson(tileset_id)`
Gets TileJSON metadata for a tileset.

**Parameters:**
- `tileset_id`: UUID of the tileset

**Returns:** TileJSON object with tiles URL, bounds, zoom range, vector_layers.

### Feature Tools

#### `search_features(bbox?, layer?, filter?, limit?, tileset_id?)`
Searches for geographic features.

**Parameters:**
- `bbox` (optional): Bounding box "minx,miny,maxx,maxy" (WGS84)
- `layer` (optional): Layer name filter
- `filter` (optional): Property filter "key=value"
- `limit` (optional): Max features to return (default: 100)
- `tileset_id` (optional): Limit to specific tileset

**Returns:** List of GeoJSON features with geometry and properties.

#### `get_feature(feature_id)`
Gets detailed information about a specific feature.

**Parameters:**
- `feature_id`: UUID of the feature

**Returns:** GeoJSON feature with full geometry and properties.

## License

MIT License - see LICENSE file for details.
