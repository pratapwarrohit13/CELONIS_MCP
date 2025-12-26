# Celonis MCP Client

This script (`celonis_mcp.py`) is a Python client for connecting to a Celonis Model Context Protocol (MCP) server. It supports OAuth2 authentication and Server-Sent Events (SSE) for protocol communication.

## Prerequisites

- Python 3.x
- `requests` library

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the same directory with your credentials:

```env
CELONIS_ENDPOINT_URL=https://[TEAM].celonis.cloud/studio-copilot/api/v1/mcp-servers/mcp/[SERVER_ID]
CELONIS_API_KEY=[YOUR_API_KEY]
# OR for OAuth2:
# CELONIS_CLIENT_ID=[CLIENT_ID]
# CELONIS_CLIENT_SECRET=[CLIENT_SECRET]
```

## Usage

### 1. Connection Verification (List Tools)
Run the script without arguments to use the configuration from `.env`:

```bash
python celonis_mcp.py --action list
```

### 2. Call a Tool
To execute a specific tool:

```bash
python celonis_mcp.py \
  --action call \
  --tool-name "tool_name" \
  --tool-args '{"arg1": "value"}'
```

You can still override settings via CLI arguments if needed:

## Current Status & Known Issues

### ✅ Authentication
- **Status**: Working.
- **Details**: Uses OAuth2 Client Credentials flow with scope `mcp-asset.tools:execute`.

### ⚠️ Connection Handshake
- **Status**: Partially Working / Blocked.
- **Details**: The client successfully connects to the SSE stream and receives heartbeat pings.
- **Blocker**: The server **does not send the `endpoint` event** required by the MCP protocol to tell the client where to send POST requests.
- **Result**: The script will connect, log `Connecting to SSE...`, and then time out with `Timeout waiting for endpoint from SSE.`

### Troubleshooting
- **Timeout**: If you see a timeout, it means the server is reachable but not sending the required initialization event.
- **401 Unauthorized**: Check your Client ID and Secret.
- **403 Forbidden**: Ensure your ID has the correct permissions/scopes.
