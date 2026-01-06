# Celonis MCP Client

A Python client for interacting with Celonis Model Context Protocol (MCP) servers. Execute tools to search data, get insights, and load data from your Celonis environment via JSON-RPC 2.0 protocol with OAuth2 authentication and Server-Sent Events (SSE).

## Features

- ✅ **OAuth2 Authentication** - Client Credentials flow with `mcp-asset.tools:execute` scope
- ✅ **JSON-RPC 2.0** - Standard protocol for tool invocation
- ✅ **Server-Sent Events** - Real-time communication with Celonis servers
- ✅ **Multiple Tools** - Access to `search_data`, `get_insights`, and `load_data` tools
- ✅ **Flexible Filtering** - String, numeric, date, and null filters for data queries
- ✅ **Pagination Support** - Handle large datasets with page-based retrieval

## Prerequisites

- **Python 3.7+**
- **Celonis Account** with MCP server access
- **OAuth2 Credentials** (Client ID and Client Secret)
- **MCP Server Endpoint URL** (from your Celonis team)

## Quick Start

### 1. Installation

Clone or download the repository:
```powershell
cd C:\path\to\CELONIS_MCP
```

Create and activate a virtual environment:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:
```powershell
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
# OAuth2 Credentials (required)
CELONIS_CLIENT_ID=your-client-id
CELONIS_CLIENT_SECRET=your-client-secret

# MCP Server Endpoint (required)
CELONIS_ENDPOINT_URL=https://your-team.celonis.cloud/studio-copilot/api/v1/mcp-servers/mcp/your-asset-id
```

### 3. List Available Tools

```powershell
python celonis_mcp.py --action list
```

### 4. Call a Tool

**Search for data:**
```powershell
python celonis_mcp.py --action call --tool-name "search_data" --tool-args '{
  "search_terms": ["vendor", "payment"],
  "user_query": "Find vendor and payment data"
}'
```

**Load data:**
```powershell
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["VENDOR.NAME", "INVOICE.AMOUNT"],
  "page_size": 50
}'
```

**Get insights:**
```powershell
python celonis_mcp.py --action call --tool-name "get_insights" --tool-args '{
  "kpi": "VENDOR.PAYMENT_RATE",
  "field_ids": ["VENDOR.REGION"]
}'
```

## Documentation

Refer to the detailed guides in this repository:

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete usage guide with examples and troubleshooting
- **[MCP_INPUT_OUTPUT.md](MCP_INPUT_OUTPUT.md)** - Input/output specifications for each tool

## Available Tools

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `search_data` | Discover KPIs and record attributes | `search_terms`, `user_query` | `search_result` (string) |
| `get_insights` | Get business insights on KPIs | `kpi`, `field_ids`, optional filters | `insights` (string) |
| `load_data` | Retrieve paginated data | `columns`, optional pagination/filters | `data_frame_content` (table) |

## Usage Examples

### Example 1: Search and Load Workflow

```powershell
# Step 1: Discover available fields
python celonis_mcp.py --action call --tool-name "search_data" --tool-args '{
  "search_terms": ["invoice", "vendor"],
  "user_query": "Find invoice and vendor fields"
}'

# Step 2: Load data using discovered field IDs
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["INVOICE.ID", "VENDOR.NAME", "INVOICE.AMOUNT"],
  "page_size": 100
}'
```

### Example 2: Filtered Data Query

```powershell
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["VENDOR.NAME", "INVOICE.AMOUNT", "PAYMENT.DATE"],
  "applied_filters": {
    "numeric_filters": [
      {
        "column_id": "INVOICE.AMOUNT",
        "value": 1000,
        "comparator": ">"
      }
    ]
  },
  "order_by": "INVOICE.AMOUNT",
  "ascending": false,
  "page_size": 50
}'
```

## Command-Line Arguments

```
--action {list,call}           Action to perform (default: list)
--tool-name TOOL_NAME          Name of tool to call (required for --action call)
--tool-args JSON_STRING        JSON arguments for tool (required for --action call)
--oauth ID SECRET              Override OAuth credentials via CLI
--endpoint-url URL             Override endpoint URL via CLI
--team-info TEAM_URL SERVER_ID Override team URL and server ID via CLI
--api-key KEY                  Use legacy API key instead of OAuth2
```

## Authentication

The client uses **OAuth2 Client Credentials flow**:

1. Client sends credentials to `https://your-team.celonis.cloud/oauth2/token`
2. Server returns `access_token` with scope `mcp-asset.tools:execute`
3. Client includes token in `Authorization: Bearer <token>` header for all requests
4. Token is valid for the duration of the session

## Response Format

All responses follow **JSON-RPC 2.0** standard:

**Success:**
```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "result": { "tool_output": "..." }
}
```

**Error:**
```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32600,
    "message": "Error description"
  }
}
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `OAuth Authentication Failed` | Invalid credentials | Verify Client ID and Secret in `.env` |
| `SSE Connection Error` | Network or endpoint issue | Check endpoint URL and network connectivity |
| `Timeout waiting for RPC response` | Tool execution timeout | Verify tool name and arguments; check network |
| `Invalid JSON args` | Malformed JSON | Use double quotes in JSON; validate syntax |
| `Column IDs not found` | Wrong ID format | Use `search_data` first to discover IDs |

For detailed troubleshooting, see [USER_GUIDE.md - Troubleshooting](USER_GUIDE.md#troubleshooting).

## Project Structure

```
CELONIS_MCP/
├── celonis_mcp.py              # Main client script
├── requirements.txt             # Python dependencies
├── .env                         # Configuration file (not in git)
├── .gitignore                   # Git ignore rules
├── README.md                    # This file
├── USER_GUIDE.md                # Comprehensive user guide
└── MCP_INPUT_OUTPUT.md          # Input/output reference
```

## Status

✅ **Fully Functional**

- ✅ Authentication: Working
- ✅ Connection: Working
- ✅ Tool Execution: Working
- ✅ Response Parsing: Working
- ✅ Error Handling: Implemented

## Support

- Check [USER_GUIDE.md](USER_GUIDE.md) for detailed documentation
- Review [MCP_INPUT_OUTPUT.md](MCP_INPUT_OUTPUT.md) for API specifications
- Check error messages and stack traces for debugging
- Verify `.env` configuration and endpoint availability
