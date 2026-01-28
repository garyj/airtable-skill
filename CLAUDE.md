# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code skill for Airtable integration. It provides Python CLI scripts that Claude can use to interact with Airtable bases, tables, and records. The skill is located in `.claude/skills/airtable/`.

## Development Commands

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_connection.py

# Run a single test
uv run pytest tests/test_connection.py::TestConnectionScript::test_missing_token_error

# Run skill scripts (from project root)
uv run .claude/skills/airtable/scripts/connection.py test
uv run .claude/skills/airtable/scripts/records.py list --base-id appXXX --table "TableName"
```

## Architecture

### Skill Structure

```
.claude/skills/airtable/
├── SKILL.md              # Skill definition and usage documentation
├── privacy.md            # PII handling and security guidelines
└── scripts/              # CLI scripts executed via `uv run`
    ├── connection.py     # Test API connection, list bases
    ├── records.py        # CRUD for individual records
    ├── batch.py          # Bulk create/update/upsert/delete
    ├── schema.py         # Table and field management
    └── webhooks.py       # Webhook management
```

### Script Pattern

All scripts use PEP 723 inline metadata for dependencies and follow this pattern:
- Accept `--base-id` and `--table` for targeting
- Support `--json` flag for machine-readable output
- Read `AIRTABLE_API_TOKEN` from environment
- Return exit code 0 on success, 1 on failure

### Tests

Tests in `tests/` are organized by script with integration tests that skip automatically when `AIRTABLE_API_TOKEN` is not set:
- Unit tests mock the pyairtable API
- Integration tests require a valid token and run against real Airtable

### Intentional Cross-Script Duplication

Functions like `get_api_token()`, token-check boilerplate, and error sanitization are intentionally duplicated across scripts. Do not refactor them into a shared module. PEP 723 requires each script to be fully self-contained so that `uv run` can execute it standalone with only inline-declared dependencies. Extracting shared code into a separate module would break this constraint.

## Key Dependencies

- **pyairtable**: Python SDK for the Airtable API
- **uv**: Package manager (scripts use PEP 723 inline dependencies)

## Environment Variables

- `AIRTABLE_API_TOKEN`: Required for all Airtable operations
- `AIRTABLE_TEST_BASE_ID`: Optional, for integration tests
