# Airtable Plugin for Claude Code

A Claude Code plugin that gives your agent full access to the Airtable API through Python CLI scripts. Connection testing, record CRUD, batch operations, schema management, and webhooks.

## Why This Exists

I needed to migrate hundreds of property compliance records between Airtable bases: inspections, certifications, linked properties, PDF attachments and doing it manually wasn't an option. So I built this plugin, pointed Claude at the source base, and let it handle the migration autonomously: creating tables, mapping fields, batch-transferring records (including attachments via URL), and verifying counts. The only gap was formula fields, which Airtable's API doesn't support creating programmatically, those had to be added manually after the migration.

## What's Included

| Script | Purpose |
|--------|---------|
| `connection.py` | Test API connection, list accessible bases |
| `records.py` | Create, read, update, delete, query records; manage comments |
| `batch.py` | Bulk create, update, upsert, delete (handles Airtable's 10-record batch limit) |
| `schema.py` | List tables, describe fields, create tables and fields |
| `webhooks.py` | Create, list, inspect, and delete webhooks |

All scripts support `--json` for machine-readable output and follow PII-safe practices (no token leaks, confirmation before writes, minimal data fetching).

## Installation

### Claude Code

From inside Claude Code (interactive mode):

```bash
/plugin marketplace add https://github.com/garyj/airtable-skill
/plugin install airtable
```

Or from your terminal (CLI):

```bash
claude plugin marketplace add garyj/airtable-skill
claude plugin install airtable
```

### Updating

```bash
/plugin update airtable@airtable-marketplace
```

Or from terminal:

```bash
claude plugin update airtable@airtable-marketplace
```

### Local Development

Clone the repo and validate the plugin structure:

```bash
git clone https://github.com/garyj/airtable-skill.git
claude plugin validate /path/to/airtable-skill
```

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- An [Airtable API token](https://airtable.com/create/tokens) with appropriate scopes

### Set Up Your Token

Create a personal access token at <https://airtable.com/create/tokens> with these scopes:

- `data.records:read`, read records
- `data.records:write`, create, update, delete records
- `schema.bases:read`, view base structure
- `schema.bases:write`, create tables and fields
- `webhook:manage`, webhook operations

Then set the environment variable:

```bash
export AIRTABLE_API_TOKEN="patXXXXXXXX.XXXXXXX"
```

## Verify Installation

After installing, test the connection:

```
Test my Airtable connection
```

Claude will run `connection.py test` and confirm whether your token is valid and which bases are accessible.

## Usage

The plugin activates automatically when you mention Airtable, bases, tables, records, or structured data.

**Explore a base:**
> List the tables in my Airtable base appXXXXX

**Query records:**
> Find all contacts in the Contacts table where Status is Active

**Bulk operations:**
> Create 50 records in the Tasks table from this CSV data...

**Schema management:**
> Create a new table called Invoices with fields for amount, date, and status

See `skills/airtable/SKILL.md` for the full script reference, formula examples, and workflow guides.

## Known Limitations

- **Formula fields cannot be created via the API.** After migrations or table creation, formula fields must be added manually in the Airtable UI.
- **Airtable rate limits apply.** The batch script handles the 10-record-per-request limit automatically, but high-volume operations may hit the 5 requests/second rate limit.
- **Attachments are URL-based only.** Attachments can be added by providing URLs (Airtable downloads them), but direct file uploads from disk are not supported.

## Running Tests

```bash
# All tests (unit tests run without a token)
uv run pytest

# Unit tests only (no Airtable access needed)
uv run pytest -m "not integration"

# Integration tests (requires AIRTABLE_API_TOKEN and AIRTABLE_TEST_BASE_ID)
uv run pytest -m integration
```

## License

MIT License, see LICENSE file for details.

## Support

- **Issues**: <https://github.com/garyj/airtable-skill/issues>
