# Celonis MCP Client: Input/Output Flow

## How User Input Works

### 1. **Authentication & Configuration (One-time Setup)**

You provide credentials and endpoint info via `.env` file:

```env
CELONIS_CLIENT_ID=your-oauth-client-id
CELONIS_CLIENT_SECRET=your-oauth-client-secret
CELONIS_ENDPOINT_URL=https://your-team.celonis.cloud/studio-copilot/api/v1/mcp-servers/mcp/asset-id
```

**OR** via command-line arguments:
```powershell
python celonis_mcp.py --oauth CLIENT_ID CLIENT_SECRET --endpoint-url "https://..."
```

---

## 2. **Input Methods**

### Method A: List Available Tools
**Input:**
```powershell
python celonis_mcp.py --action list
```

**What you send:**
- Action type: `list`
- No additional parameters

**Output you receive:**
```json
{
  "tools": [
    {
      "name": "get_insights",
      "description": "Finds recommended insights...",
      "inputSchema": { ... },
      "outputSchema": { ... }
    },
    {
      "name": "search_data",
      "description": "Searches for relevant columns...",
      "inputSchema": { ... },
      "outputSchema": { ... }
    },
    {
      "name": "load_data",
      "description": "Retrieves data based on IDs...",
      "inputSchema": { ... },
      "outputSchema": { ... }
    }
  ]
}
```

---

### Method B: Call a Specific Tool

**Input Format:**
```powershell
python celonis_mcp.py --action call --tool-name "TOOL_NAME" --tool-args '{"arg1": "value1", "arg2": "value2"}'
```

---

## 3. **Tool-Specific Input/Output Examples**

### Tool 1: `search_data`

**What you send:**
```powershell
python celonis_mcp.py --action call --tool-name "search_data" --tool-args '{
  "search_terms": ["vendor", "payment", "invoice"],
  "user_query": "Find me vendor payment and invoice data"
}'
```

**What you get in return:**
```json
{
  "search_result": "Found KPIs: [VENDOR.PAYMENT_RATE, VENDOR.ON_TIME_DELIVERY]\nFound Attributes: [VENDOR.NAME, VENDOR.ID, INVOICE.AMOUNT, PAYMENT.DATE]\nInstance Values: [Vendor A, Vendor B, Company XYZ]"
}
```

**Input Requirements:**
- `search_terms` (required): Array of keywords to search for
- `user_query` (required): Original user question/message

---

### Tool 2: `get_insights`

**What you send:**
```powershell
python celonis_mcp.py --action call --tool-name "get_insights" --tool-args '{
  "kpi": "VENDOR.PAYMENT_RATE",
  "field_ids": ["VENDOR.REGION", "VENDOR.TYPE"],
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

**What you get in return:**
```json
{
  "insights": "Top insight: EMEA vendors have 85% payment rate vs 92% global average. Key factors: late invoicing (delay 2.5 days), slow processing (4 days vs 3 day average). Recommendation: Implement automated invoice validation for EMEA vendors."
}
```

**Input Requirements:**
- `kpi` (required): KPI ID (e.g., "VENDOR.PAYMENT_RATE")
- `field_ids` (required): Array of Record Attribute IDs (format: TABLE.COLUMN)
- `string_filters` (optional): Filter by text values
- `numeric_filters` (optional): Filter by numbers (>, <, =, etc.)
- `date_filters` (optional): Filter by date ranges
- `null_filters` (optional): Filter for NULL/non-NULL values

---

### Tool 3: `load_data`

**What you send:**
```powershell
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["VENDOR.NAME", "INVOICE.AMOUNT", "PAYMENT.DATE"],
  "page": 0,
  "page_size": 50,
  "order_by": "INVOICE.AMOUNT",
  "ascending": false,
  "limit": 200,
  "applied_filters": {
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

**What you get in return:**
```json
{
  "page": 0,
  "page_size": 50,
  "total": 547,
  "data_frame_content": {
    "schema": [
      {
        "id": "VENDOR.NAME",
        "type": "string",
        "displayName": "Vendor Name"
      },
      {
        "id": "INVOICE.AMOUNT",
        "type": "decimal",
        "displayName": "Invoice Amount"
      },
      {
        "id": "PAYMENT.DATE",
        "type": "date",
        "displayName": "Payment Date"
      }
    ],
    "data": [
      {
        "VENDOR.NAME": "Acme Corp",
        "INVOICE.AMOUNT": 5000,
        "PAYMENT.DATE": "2024-12-15"
      },
      {
        "VENDOR.NAME": "TechVendor Inc",
        "INVOICE.AMOUNT": 2500,
        "PAYMENT.DATE": "2024-12-14"
      }
      ...50 rows...
    ]
  }
}
```

**Input Requirements:**
- `columns` (required): Array of column IDs to retrieve
- `page` (optional, default: 0): Which page of results (0-indexed)
- `page_size` (optional, default: 50): Rows per page
- `order_by` (optional): Column ID to sort by
- `ascending` (optional, default: true): Sort direction
- `limit` (optional): Maximum total rows to return
- `applied_filters` (optional): String, numeric, date, or null filters

---

## 4. **Complete Workflow Example**

### Step 1: Discover Available Data
```powershell
python celonis_mcp.py --action call --tool-name "search_data" --tool-args '{
  "search_terms": ["vendor", "payment"],
  "user_query": "What vendor and payment data is available?"
}'
```
**Returns:** Available columns, KPIs, and sample values

### Step 2: Get Insights
```powershell
python celonis_mcp.py --action call --tool-name "get_insights" --tool-args '{
  "kpi": "VENDOR.PAYMENT_RATE",
  "field_ids": ["VENDOR.COUNTRY", "VENDOR.SIZE"]
}'
```
**Returns:** Business insights with recommendations

### Step 3: Load Specific Data
```powershell
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["VENDOR.NAME", "VENDOR.COUNTRY", "INVOICE.COUNT"],
  "page_size": 100
}'
```
**Returns:** Paginated data table with all matching records

---

## 5. **Response Structure**

### Success Response
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "actual_tool_output": "..."
  }
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Invalid Request: missing required field 'kpi'"
  }
}
```

---

## 6. **Common Input Patterns**

### Pattern 1: Search First
```powershell
# Step 1: Discover
python celonis_mcp.py --action call --tool-name "search_data" --tool-args '{"search_terms": ["order", "status"], "user_query": "show me order data"}'

# Step 2: Use discovered IDs
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{"columns": ["ORDER.ID", "ORDER.STATUS"]}'
```

### Pattern 2: Filtered Query
```powershell
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{
  "columns": ["INVOICE.ID", "INVOICE.AMOUNT", "VENDOR.NAME"],
  "applied_filters": {
    "string_filters": [{"column_id": "VENDOR.NAME", "values": ["Acme"]}],
    "numeric_filters": [{"column_id": "INVOICE.AMOUNT", "value": 5000, "comparator": ">"}]
  },
  "page_size": 100
}'
```

### Pattern 3: Paginated Large Dataset
```powershell
# Page 1
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{"columns": ["VENDOR.NAME", "INVOICE.AMOUNT"], "page": 0, "page_size": 1000}'

# Page 2
python celonis_mcp.py --action call --tool-name "load_data" --tool-args '{"columns": ["VENDOR.NAME", "INVOICE.AMOUNT"], "page": 1, "page_size": 1000}'
```

---

## 7. **Data Type Reference**

| Type | Example | Filter Type |
|------|---------|------------|
| String | "Vendor A", "Active" | `string_filters` |
| Integer | 100, 5000 | `numeric_filters` |
| Decimal | 1234.56, 99.99 | `numeric_filters` |
| Date | "2024-12-31" | `date_filters` |
| Boolean | true, false | Direct (no filters) |
| Null | NULL | `null_filters` |

---

## 8. **Key Points to Remember**

1. **JSON Format**: All tool arguments must be valid JSON
2. **Column IDs**: Always use format `TABLE.COLUMN` (e.g., `VENDOR.NAME`)
3. **Search First**: Use `search_data` to discover available column IDs
4. **Pagination**: For large datasets, use `page` and `page_size` parameters
5. **Filters**: Multiple filters of the same type go in the same array
6. **Required Fields**: Check tool's `inputSchema` for required vs optional parameters

---

## 9. **Troubleshooting Input Issues**

**Error: "Invalid JSON args"**
- Fix: Ensure quotes are double quotes, not single quotes in JSON values

**Error: "missing required field"**
- Fix: Check tool's inputSchema for required fields (marked with "required")

**Error: "Column not found"**
- Fix: Use `search_data` first to discover correct column IDs

**Empty results**
- Fix: Check if filters are too restrictive; start with no filters, then add them

