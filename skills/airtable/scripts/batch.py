#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyairtable>=3.3.0",
# ]
# ///
"""
Airtable batch operations script.

Create, update, upsert, or delete multiple records at once for efficient data management.

Usage:
    uv run batch.py create --base-id <id> --table <name> --records <json-array>
    uv run batch.py create --base-id <id> --table <name> --records <json-array> --json
    uv run batch.py update --base-id <id> --table <name> --records <json-array>
    uv run batch.py update --base-id <id> --table <name> --records <json-array> --json
    uv run batch.py upsert --base-id <id> --table <name> --records <json-array> --key-fields <field1,field2>
    uv run batch.py upsert --base-id <id> --table <name> --records <json-array> --key-fields <field1,field2> --json
    uv run batch.py delete --base-id <id> --table <name> --record-ids <id1,id2,...>
    uv run batch.py delete --base-id <id> --table <name> --record-ids <id1,id2,...> --json

Examples:
    # Create multiple records
    uv run batch.py create --base-id appXXX --table "Contacts" --records '[{"Name": "Alice"}, {"Name": "Bob"}]'

    # Create records with JSON output
    uv run batch.py create --base-id appXXX --table "Contacts" --records '[{"Name": "Alice"}]' --json

    # Update multiple records
    uv run batch.py update --base-id appXXX --table "Contacts" --records '[{"id": "recXXX", "fields": {"Name": "Updated"}}]'

    # Update records with JSON output
    uv run batch.py update --base-id appXXX --table "Contacts" --records '[{"id": "recXXX", "fields": {"Name": "Updated"}}]' --json

    # Upsert records (create or update based on key fields)
    uv run batch.py upsert --base-id appXXX --table "Contacts" --records '[{"Email": "alice@example.com", "Name": "Alice"}]' --key-fields "Email"

    # Upsert with JSON output
    uv run batch.py upsert --base-id appXXX --table "Contacts" --records '[{"Email": "alice@example.com", "Name": "Alice"}]' --key-fields "Email" --json

    # Delete multiple records
    uv run batch.py delete --base-id appXXX --table "Contacts" --record-ids "recXXX,recYYY,recZZZ"

    # Delete records with JSON output
    uv run batch.py delete --base-id appXXX --table "Contacts" --record-ids "recXXX,recYYY" --json
"""

import argparse
import json
import os
import sys

from pyairtable import Api


def get_api_token() -> str | None:
    """Get the Airtable API token from environment."""
    return os.environ.get("AIRTABLE_API_TOKEN")


def batch_create_records(
    api: Api, base_id: str, table_name: str, records_json: str
) -> list[dict]:
    """Create multiple records in a table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        records_json: JSON string of array of field objects.

    Returns:
        List of dictionaries with created record IDs and field values.

    Raises:
        ValueError: If records_json is invalid or contains invalid data.
    """
    try:
        records = json.loads(records_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for records: {e}") from e

    if not isinstance(records, list):
        raise ValueError("Records must be a JSON array")

    if not records:
        raise ValueError("At least one record is required")

    # Validate each record is a dict
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record at index {i} must be an object")
        if not record:
            raise ValueError(f"Record at index {i} must have at least one field")

    # Create the records using pyairtable's batch_create
    # pyairtable handles the 10-record limit internally
    base = api.base(base_id)
    table = base.table(table_name)
    results = table.batch_create(records)

    return [
        {
            "id": result["id"],
            "fields": result["fields"],
        }
        for result in results
    ]


def batch_update_records(
    api: Api, base_id: str, table_name: str, records_json: str
) -> list[dict]:
    """Update multiple records in a table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        records_json: JSON string of array of objects with "id" and "fields".

    Returns:
        List of dictionaries with updated record IDs and field values.

    Raises:
        ValueError: If records_json is invalid or contains invalid data.
    """
    try:
        records = json.loads(records_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for records: {e}") from e

    if not isinstance(records, list):
        raise ValueError("Records must be a JSON array")

    if not records:
        raise ValueError("At least one record is required")

    # Validate each record has "id" and "fields"
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record at index {i} must be an object")
        if "id" not in record:
            raise ValueError(f"Record at index {i} must have an 'id' field")
        if not isinstance(record["id"], str) or not record["id"]:
            raise ValueError(f"Record at index {i} must have a non-empty string 'id'")
        if "fields" not in record:
            raise ValueError(f"Record at index {i} must have a 'fields' object")
        if not isinstance(record["fields"], dict):
            raise ValueError(f"Record at index {i} 'fields' must be an object")
        if not record["fields"]:
            raise ValueError(f"Record at index {i} 'fields' must have at least one field")

    # Update the records using pyairtable's batch_update
    # pyairtable handles the 10-record limit internally
    base = api.base(base_id)
    table = base.table(table_name)
    results = table.batch_update(records)

    return [
        {
            "id": result["id"],
            "fields": result["fields"],
        }
        for result in results
    ]


def batch_upsert_records(
    api: Api, base_id: str, table_name: str, records_json: str, key_fields: str
) -> dict:
    """Upsert (create or update) multiple records in a table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        records_json: JSON string of array of field objects.
        key_fields: Comma-separated string of field names to use for matching.

    Returns:
        Dictionary with 'created', 'updated', and 'records' keys.
        - 'created': List of created record IDs
        - 'updated': List of updated record IDs
        - 'records': List of all upserted records with id and fields

    Raises:
        ValueError: If records_json is invalid or key_fields is empty.
    """
    try:
        records = json.loads(records_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for records: {e}") from e

    if not isinstance(records, list):
        raise ValueError("Records must be a JSON array")

    if not records:
        raise ValueError("At least one record is required")

    # Validate each record is a dict with at least one field
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record at index {i} must be an object")
        if not record:
            raise ValueError(f"Record at index {i} must have at least one field")

    # Parse and validate key fields
    fields = [f.strip() for f in key_fields.split(",") if f.strip()]
    if not fields:
        raise ValueError("At least one key field is required")

    # Validate that each record contains all key fields
    for i, record in enumerate(records):
        for field in fields:
            if field not in record:
                raise ValueError(
                    f"Record at index {i} must contain key field '{field}'"
                )

    # Upsert the records using pyairtable's batch_upsert
    # pyairtable expects records in format [{"fields": {...}}, ...]
    upsert_records = [{"fields": record} for record in records]

    base = api.base(base_id)
    table = base.table(table_name)
    result = table.batch_upsert(upsert_records, key_fields=fields)

    # Extract created and updated record IDs from the result
    created_ids = result.get("createdRecords", [])
    updated_ids = result.get("updatedRecords", [])
    all_records = result.get("records", [])

    return {
        "created": created_ids,
        "updated": updated_ids,
        "records": [
            {
                "id": record["id"],
                "fields": record["fields"],
            }
            for record in all_records
        ],
    }


def batch_delete_records(
    api: Api, base_id: str, table_name: str, record_ids: str
) -> list[str]:
    """Delete multiple records from a table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        record_ids: Comma-separated string of record IDs to delete.

    Returns:
        List of deleted record IDs.

    Raises:
        ValueError: If record_ids is invalid.
    """
    # Parse and validate record IDs
    ids = [rid.strip() for rid in record_ids.split(",") if rid.strip()]

    if not ids:
        raise ValueError("At least one record ID is required")

    # Delete the records using pyairtable's batch_delete
    # pyairtable handles the 10-record limit internally
    base = api.base(base_id)
    table = base.table(table_name)
    results = table.batch_delete(ids)

    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Airtable batch operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create subcommand
    create_parser = subparsers.add_parser("create", help="Create multiple records")
    create_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    create_parser.add_argument("--table", required=True, help="The table name or ID")
    create_parser.add_argument(
        "--records",
        required=True,
        help='JSON array of record objects (e.g., \'[{"Name": "Alice"}, {"Name": "Bob"}]\')',
    )
    create_parser.add_argument(
        "--json", action="store_true", help="Output as JSON array of created records"
    )

    # update subcommand
    update_parser = subparsers.add_parser("update", help="Update multiple records")
    update_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    update_parser.add_argument("--table", required=True, help="The table name or ID")
    update_parser.add_argument(
        "--records",
        required=True,
        help='JSON array of record objects with id and fields (e.g., \'[{"id": "recXXX", "fields": {"Name": "Updated"}}]\')',
    )
    update_parser.add_argument(
        "--json", action="store_true", help="Output as JSON array of updated records"
    )

    # upsert subcommand
    upsert_parser = subparsers.add_parser(
        "upsert", help="Upsert (create or update) multiple records based on key fields"
    )
    upsert_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    upsert_parser.add_argument("--table", required=True, help="The table name or ID")
    upsert_parser.add_argument(
        "--records",
        required=True,
        help='JSON array of record objects (e.g., \'[{"Email": "alice@example.com", "Name": "Alice"}]\')',
    )
    upsert_parser.add_argument(
        "--key-fields",
        required=True,
        help='Comma-separated list of field names to match records (e.g., "Email" or "Email,Name")',
    )
    upsert_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON with created/updated breakdown",
    )

    # delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete multiple records")
    delete_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    delete_parser.add_argument("--table", required=True, help="The table name or ID")
    delete_parser.add_argument(
        "--record-ids",
        required=True,
        help='Comma-separated list of record IDs to delete (e.g., "recXXX,recYYY,recZZZ")',
    )
    delete_parser.add_argument(
        "--json", action="store_true", help="Output as JSON array of deleted record IDs"
    )

    args = parser.parse_args()

    # Check for API token
    token = get_api_token()
    if not token:
        print(
            "Error: AIRTABLE_API_TOKEN environment variable is not set.",
            file=sys.stderr,
        )
        print("Set it with: export AIRTABLE_API_TOKEN=your_token", file=sys.stderr)
        return 1

    api = Api(token)

    if args.command == "create":
        try:
            results = batch_create_records(api, args.base_id, args.table, args.records)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(f"Created {len(results)} record(s):")
                print("")
                for result in results:
                    print(f"  {result['id']}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error creating records: {e}", file=sys.stderr)
            return 1

    elif args.command == "update":
        try:
            results = batch_update_records(api, args.base_id, args.table, args.records)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(f"Updated {len(results)} record(s):")
                print("")
                for result in results:
                    print(f"  {result['id']}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error updating records: {e}", file=sys.stderr)
            return 1

    elif args.command == "upsert":
        try:
            results = batch_upsert_records(
                api, args.base_id, args.table, args.records, args.key_fields
            )
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                created_count = len(results["created"])
                updated_count = len(results["updated"])
                print(f"Upserted {len(results['records'])} record(s):")
                print(f"  Created: {created_count}")
                print(f"  Updated: {updated_count}")
                print("")
                if results["created"]:
                    print("Created record IDs:")
                    for record_id in results["created"]:
                        print(f"  {record_id}")
                if results["updated"]:
                    print("Updated record IDs:")
                    for record_id in results["updated"]:
                        print(f"  {record_id}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error upserting records: {e}", file=sys.stderr)
            return 1

    elif args.command == "delete":
        try:
            results = batch_delete_records(
                api, args.base_id, args.table, args.record_ids
            )
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(f"Deleted {len(results)} record(s):")
                print("")
                for record_id in results:
                    print(f"  {record_id}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error deleting records: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
