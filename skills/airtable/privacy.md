# Privacy Guidelines

## Core Principles

### 1. Never Expose API Tokens

- NEVER display, echo, or log `AIRTABLE_API_TOKEN`
- NEVER include tokens in error messages or debug output
- When referencing authentication, say "using configured credentials"
- If a command fails, do NOT show the full curl command or URL with token

**Example Error Handling:**
```
# Bad
Error: Request failed: GET https://api.airtable.com/v0/appXXX?token=pat123...

# Good
Error: Could not access the base. Verify your token has the required permissions.
```

### 2. Confirm Before Write Operations

- NEVER execute create, update, or delete operations without explicit user permission
- Write operations (create, update, delete, batch operations) require explicit consent
- Always confirm what will be changed before proceeding

**Example Confirmation:**
```
This will delete record rec123 from the Tenants table. Proceed? (y/n)
This will update 5 records in Properties. The following fields will change:
  - Status: "Pending" → "Active"
Proceed? (y/n)
```

### 3. Minimal Data Fetching

- Only request fields needed for the current task
- Use `--fields` parameter to limit returned data
- Don't fetch "everything just in case"
- Set reasonable `--max-records` limits instead of fetching all records

**Example:**
```bash
# Bad: Fetching everything
uv run scripts/records.py list --base-id appXXX --table Tenants

# Good: Fetching only what's needed
uv run scripts/records.py list --base-id appXXX --table Tenants \
    --fields "Name,Unit Number" --max-records 10
```

## Handling PII in Airtable Records

Airtable bases often contain Personally Identifiable Information (PII). Common examples include:

| Data Type | Examples | Handling |
|-----------|----------|----------|
| **Names** | Tenant names, owner names, contact names | Display only when necessary for the task |
| **Addresses** | Property addresses, mailing addresses | Avoid displaying full addresses when partial suffices |
| **Contact Info** | Phone numbers, email addresses | Mask or omit unless explicitly needed |
| **Financial** | Rent amounts, payment history, bank info | Never display without explicit request |
| **IDs** | SSN, driver's license, passport numbers | NEVER display, even if present in records |
| **Dates** | Birthdays, lease dates | Display lease dates; avoid personal dates |

### Best Practices for PII

1. **Summarize Rather Than Dump**
   - Instead of showing all 50 tenant records, summarize: "Found 50 tenants across 3 properties"
   - Offer to show details on specific records rather than bulk data

2. **Mask Sensitive Fields**
   - Phone: `(555) ***-**34`
   - Email: `j***@example.com`
   - Address: `*** Main St, Unit 5`

3. **Ask Before Displaying**
   - "This record contains contact information. Would you like to see it?"
   - "Found 10 records with financial data. Show summary or full details?"

4. **Field Selection**
   - When listing records, select only non-sensitive fields by default
   - Require explicit request to include PII fields

## Error Handling Without Exposing Tokens

### Safe Error Messages

When API calls fail, provide helpful errors without exposing sensitive data:

| Scenario | Bad Message | Good Message |
|----------|-------------|--------------|
| Auth failure | `401: Invalid token pat123...` | `Authentication failed. Verify your AIRTABLE_API_TOKEN is valid.` |
| Not found | `404: Base appXXX not found at https://api...` | `Base not found. Check the base ID and your token's permissions.` |
| Rate limit | `429: Too many requests to api.airtable.com/v0/...` | `Rate limited. Wait a moment before retrying.` |
| Permission | `403: Token lacks write access to appXXX` | `Permission denied. Your token may not have write access to this base.` |

### Error Response Format

```
Error: [Brief description]
Suggestion: [How to fix it]

# Never include:
# - Full URLs with tokens
# - Raw API error responses
# - Token values, even partial
```

## Data Retention

- Do NOT store Airtable data between sessions
- Do NOT cache record information locally
- Each request should fetch fresh data from the API
- Webhook payloads should be processed and not persisted

## Response Formatting Guidelines

### Displaying Records

- Format records as clean tables, not raw JSON
- Truncate long field values with `[...more]` indicator
- Show record counts and offer pagination
- Default to showing 10-20 records maximum

### Large Datasets

```
Found 150 records in Properties table.

Showing first 10:
ID           Property Name    Status
-----------  ---------------  --------
rec123       Oak Street       Active
rec456       Pine Avenue      Pending
...

Use --max-records or --formula to refine results.
```

## Webhook Security

- Webhook notification URLs should not be logged or displayed
- Webhook payloads may contain record data with PII
- Process webhook data in memory without persistent storage
- Validate webhook sources when possible

## What NOT To Do

| Don't | Instead |
|-------|---------|
| Show raw API responses | Format as clean tables/lists |
| Display the API token | Say "using configured credentials" |
| Fetch all records without asking | Ask how many/which records needed |
| Modify without confirmation | Always confirm writes |
| Show full record dumps | Summarize key fields |
| Log sensitive field values | Log record IDs only |
| Display error URLs with tokens | Summarize the error type |
| Store data between sessions | Fetch fresh data each time |
