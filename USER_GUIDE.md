# Celonis MCP Client User Guide

## Overview

The Celonis MCP (Model Context Protocol) Client allows you to interact with Celonis MCP servers to execute tools and retrieve data from your Celonis environment. This client supports OAuth2 authentication and communicates via Server-Sent Events (SSE) and JSON-RPC 2.0.

## Prerequisites

- Python 3.7 or higher
- Access to a Celonis training or production environment
- OAuth2 credentials (Client ID and Client Secret) with the `mcp-asset.tools:execute` scope

## Installation

1. **Create a virtual environment** (recommended):
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. **Install required dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with your Celonis credentials:

```env
# OAuth2 Credentials (Recommended)
CELONIS_CLIENT_ID=your-client-id-here
CELONIS_CLIENT_SECRET=your-client-secret-here

# MCP Server Endpoint URL
CELONIS_ENDPOINT_URL=https://your-team.celonis.cloud/studio-copilot/api/v1/mcp-servers/mcp/your-asset-id

# Alternative: Separate Team URL and Server ID
# CELONIS_TEAM_URL=https://your-team.celonis.cloud
# CELONIS_SERVER_ID=your-asset-id
```

### Command-Line Arguments (Optional)

You can override environment variables using command-line arguments:

```powershell
# Using OAuth2
python celonis_mcp.py --oauth CLIENT_ID CLIENT_SECRET --endpoint-url "https://..."

# Using Team URL and Server ID
python celonis_mcp.py --oauth CLIENT_ID CLIENT_SECRET --team-info "https://your-team.celonis.cloud" "server-id"
```

## Usage

### 1. List Available Tools

Retrieve all tools available in your MCP server:

```powershell
python celonis_mcp.py --action list
```

**Output:**
```json
{
  "tools": [
    {
      "name": "get_insights",
      "description": "Finds recommended insights and improvement potentials...",
      "inputSchema": { ... }
    },
    {
      "name": "search_data",
      "description": "Searches for relevant columns or instances...",
      "inputSchema": { ... }
    },
    {
      "name": "load_data",
      "description": "Retrieves data based on IDs from the database...",
      "inputSchema": { ... }
    }
  ]
}
```

### 2. Call a Tool

Execute a specific tool with arguments:

```powershell
python celonis_mcp.py --action call --tool-name "TOOL_NAME" --tool-args '{"arg1": "value1", "arg2": "value2"}'
```

**Important:** Tool arguments must be valid JSON.

## Available Tools

### What you send vs. what you get (MCP)
- You provide: OAuth2 credentials (Client ID/Secret), the MCP endpoint URL (with `?draft=false`), an action (`list` or `call`), and when calling tools, a JSON object matching each tool's input schema.
- You receive: A JSON-RPC response containing either `result` (with tool output) or `error` (code/message). For `tools/list`, you get tool metadata and input/output schemas. For tool calls, you get the tool-specific result payload (e.g., insights, search results, or paginated data).

### Tool 1: `search_data`

**Description:** Searches for relevant columns or instances from the knowledge model.

**Input Schema:**
- `search_terms` (array of strings): Terms to search for in KPIs and attributes
- `user_query` (string): The original user message

**Example:**
```powershell
python celonis_mcp.py --action call --tool-name "search_data" --tool-args '{
  "search_terms": ["vendor", "payment", "invoice"],
  "user_query": "Show me vendor payment and invoice data"
}'
```

### Tool 2: `get_insights`

**Description:** Finds recommended insights and improvement potentials in your data given a KPI and record attributes.

**Input Schema:**
- `kpi` (string): KPI ID to find insights for
- `field_ids` (array of strings): List of record attribute IDs (format: XXX.YYY)
- `string_filters` (optional): Filter by string values
- `null_filters` (optional): Filter by null values
- `date_filters` (optional): Filter by date ranges
- `numeric_filters` (optional): Filter by numeric comparisons

**Example:**
```powershell
python celonis_mcp.py --action call --tool-name "get_insights" --tool-args '{
  "kpi": "KPI.PAYMENT_RATE",
  "field_ids": ["VENDOR.NAME", "VENDOR.REGION"],
  "string_filters": [
    {
      "column_id": "VENDOR.REGION",
      "values": ["EMEA"],
      "add_wildcard_before": true,
      "add_wildcard_after": true,
      "case_sensitive": false
    }
  ]
}'
```

### Tool 3: `load_data`

**Description:** Retrieves data from the Celonis platform and returns paginated results.

**Input Schema:**
- `columns` (array of strings): List of KPI and Record Attribute IDs to retrieve
- `page` (integer, default: 0): Page number
- `page_size` (integer, default: 50): Number of records per page
- `order_by` (string, optional): Column to sort by
- `ascending` (boolean, optional): Sort direction
- `limit` (integer, optional): Maximum number of rows
- `applied_filters` (object, optional): Filter criteria

**Example:**
```powershell
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["VENDOR.NAME", "INVOICE.AMOUNT", "PAYMENT.DATE"],
  "page": 0,
  "page_size": 100,
  "order_by": "INVOICE.AMOUNT",
  "ascending": false,
  "limit": 500
}'
```

**Example with Filters:**
```powershell
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["VENDOR.NAME", "INVOICE.AMOUNT"],
  "applied_filters": {
    "string_filters": [
      {
        "column_id": "VENDOR.NAME",
        "values": ["Acme Corp"],
        "add_wildcard_before": false,
        "add_wildcard_after": true,
        "case_sensitive": false
      }
    ],
    "numeric_filters": [
      {
        "column_id": "INVOICE.AMOUNT",
        "value": 1000,
        "comparator": ">"
      }
    ]
  }
}'
```

## Filter Types

### String Filters
Filter by text values with wildcard support:
```json
{
  "column_id": "TABLE.COLUMN",
  "values": ["search_value"],
  "add_wildcard_before": true,
  "add_wildcard_after": true,
  "case_sensitive": false,
  "negation": false
}
```

### Numeric Filters
Filter by numeric comparisons:
```json
{
  "column_id": "TABLE.COLUMN",
  "value": 100,
  "comparator": ">"
}
```
**Comparators:** `=`, `!=`, `>`, `>=`, `<`, `<=`

### Date Filters
Filter by date ranges:
```json
{
  "column_id": "TABLE.DATE_COLUMN",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "negation": false
}
```

### Null Filters
Filter by null or non-null values:
```json
{
  "column_id": "TABLE.COLUMN",
  "is_null": true
}
```

## Troubleshooting

### Authentication Errors

**Error:** `OAuth Authentication Failed`

**Solutions:**
1. Verify your Client ID and Client Secret are correct
2. Ensure your OAuth credentials have the `mcp-asset.tools:execute` scope
3. Check that your credentials haven't expired
4. Verify the team URL is correct

### Connection Errors

**Error:** `SSE Connection Error`

**Solutions:**
1. Verify the MCP endpoint URL is correct
2. Check that `?draft=false` is included in the URL
3. Ensure your network allows connections to the Celonis server
4. Verify the asset ID exists and is accessible

### Tool Execution Errors

**Error:** `Timeout waiting for RPC response`

**Solutions:**
1. Check that the tool name is spelled correctly
2. Verify all required arguments are provided
3. Ensure argument values match the expected schema
4. Check network connectivity

**Error:** `Invalid JSON args`

**Solutions:**
1. Ensure tool arguments are properly formatted JSON
2. Use double quotes for strings in JSON
3. Escape special characters properly
4. Validate JSON syntax using a JSON validator

### Common Issues

**Issue:** Column IDs not found

**Solution:** Use the `search_data` tool first to discover available column IDs in your knowledge model.

**Issue:** Empty results

**Solution:** Verify your filters are not too restrictive. Start with broader filters and narrow down.

## Best Practices

1. **Discovery First:** Always use `search_data` to explore available KPIs and attributes before querying data

2. **Pagination:** For large datasets, use pagination with reasonable page sizes (50-100 records)

3. **Filtering:** Apply filters to reduce data volume and improve performance

4. **Error Handling:** Check response objects for error fields before processing results

5. **Credentials Security:** Never commit the `.env` file to version control. Add it to `.gitignore`

## API Reference

### Authentication Flow

1. Client sends OAuth2 token request with client credentials
2. Server responds with access token
3. Client includes token in Authorization header for all requests
4. Tokens are valid for the duration of the session

### JSON-RPC 2.0 Protocol

All tool calls use JSON-RPC 2.0 format:

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": "unique-request-id",
  "params": {
    "name": "tool_name",
    "arguments": { ... }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": { ... }
}
```

**Error Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Error description"
  }
}
```

## Examples

### Example 1: Search and Load Workflow

```powershell
# Step 1: Search for available fields
python celonis_mcp.py --action call --tool-name "search_data" --tool-args '{
  "search_terms": ["invoice", "vendor"],
  "user_query": "Find invoice and vendor fields"
}'

# Step 2: Load data using discovered field IDs
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["INVOICE.ID", "VENDOR.NAME", "INVOICE.AMOUNT"],
  "page_size": 50
}'
```

### Example 2: Filtered Insights

```powershell
python celonis_mcp.py --action call --tool-name "get_insights" --tool-args '{
  "kpi": "KPI.ON_TIME_DELIVERY",
  "field_ids": ["ORDER.REGION", "VENDOR.TYPE"],
  "date_filters": [
    {
      "column_id": "ORDER.DATE",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  ]
}'
```

## Support

For issues or questions:
- Check the Celonis documentation
- Review error messages in the console output
- Verify your configuration in the `.env` file
- Contact your Celonis administrator for credential issues

## Version History

- **v1.0** - Initial release with OAuth2 authentication and SSE support
- Supports Celonis Studio Copilot MCP servers
- Compatible with JSON-RPC 2.0 protocol
