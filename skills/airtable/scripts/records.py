#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyairtable>=3.3.0",
# ]
# ///
"""
Airtable record management script.

Create and manage records in tables.

Usage:
    uv run records.py create --base-id <id> --table <name> --fields <json>
    uv run records.py create --base-id <id> --table <name> --fields <json> --json
    uv run records.py get --base-id <id> --table <name> --record-id <id>
    uv run records.py get --base-id <id> --table <name> --record-id <id> --json
    uv run records.py list --base-id <id> --table <name>
    uv run records.py list --base-id <id> --table <name> --max-records <n> --fields <field1,field2> --json
    uv run records.py list --base-id <id> --table <name> --sort <field>
    uv run records.py list --base-id <id> --table <name> --sort <field>:desc
    uv run records.py list --base-id <id> --table <name> --sort <field1>,<field2>:desc
    uv run records.py update --base-id <id> --table <name> --record-id <id> --fields <json>
    uv run records.py update --base-id <id> --table <name> --record-id <id> --fields <json> --json
    uv run records.py delete --base-id <id> --table <name> --record-id <id>
    uv run records.py query --base-id <id> --table <name> --formula <formula>
    uv run records.py query --base-id <id> --table <name> --match <json> --json
    uv run records.py comments --base-id <id> --table <name> --record-id <id>
    uv run records.py comments --base-id <id> --table <name> --record-id <id> --json
    uv run records.py add-comment --base-id <id> --table <name> --record-id <id> --text <text>
    uv run records.py delete-comment --base-id <id> --table <name> --record-id <id> --comment-id <id>

Formula Examples:
    # Basic field comparisons
    --formula "{Status}='Active'"
    --formula "{Score}>20"

    # Lookup field references (from linked tables)
    --formula "{Property Status (from Properties)}='Active'"
    --formula "{Owner Name (from Owner)}='John Smith'"

    # Rollup field references with aggregations
    --formula "{Total Amount}>1000"
    --formula "{Count of Items}>=5"

    # Linked record IDs in formulas
    --formula "FIND('recABC123',ARRAYJOIN({Properties}))"

    # Text matching functions for lookups
    --formula "FIND('Active',{Property Status (from Properties)})"
    --formula "SEARCH('smith',LOWER({Owner Name (from Owner)}))"

    # ARRAYJOIN for multi-value lookups
    --formula "ARRAYJOIN({Property Names (from Properties)},', ')='Building A, Building B'"

    # Combining conditions
    --formula "AND({Status}='Active',{Total Amount}>1000)"
    --formula "OR({Property Status (from Properties)}='Active',{Priority}='High')"
"""

import argparse
import json
import os
import sys

from pyairtable import Api
from pyairtable.formulas import match as formula_match


def get_api_token() -> str | None:
    """Get the Airtable API token from environment."""
    return os.environ.get("AIRTABLE_API_TOKEN")


def create_record(api: Api, base_id: str, table_name: str, fields_json: str) -> dict:
    """Create a single record in a table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        fields_json: JSON string of field values.

    Returns:
        Dictionary with created record ID and field values.

    Raises:
        ValueError: If fields_json is invalid.
    """
    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for fields: {e}") from e

    if not isinstance(fields, dict):
        raise ValueError("Fields must be a JSON object")

    if not fields:
        raise ValueError("At least one field is required")

    # Create the record
    base = api.base(base_id)
    table = base.table(table_name)
    result = table.create(fields)

    return {
        "id": result["id"],
        "fields": result["fields"],
    }


def get_record(api: Api, base_id: str, table_name: str, record_id: str) -> dict:
    """Get a specific record by ID.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        record_id: The ID of the record to retrieve.

    Returns:
        Dictionary with record ID, createdTime, and field values.
    """
    base = api.base(base_id)
    table = base.table(table_name)
    result = table.get(record_id)

    return {
        "id": result["id"],
        "createdTime": result["createdTime"],
        "fields": result["fields"],
    }


def parse_sort_spec(sort_spec: str) -> list[str]:
    """Parse sort specification into pyairtable sort format.

    Args:
        sort_spec: Comma-separated sort fields. Each field can optionally
            have ':desc' suffix for descending order.
            Examples: "Name", "Name:desc", "Name,Age:desc"

    Returns:
        List of sort strings in pyairtable format (prefix with '-' for desc).
    """
    sort_list = []
    for field_spec in sort_spec.split(","):
        field_spec = field_spec.strip()
        if not field_spec:
            continue
        if field_spec.endswith(":desc"):
            # Remove :desc suffix and add - prefix for descending
            field_name = field_spec[:-5]
            sort_list.append(f"-{field_name}")
        else:
            sort_list.append(field_spec)
    return sort_list


def list_records(
    api: Api,
    base_id: str,
    table_name: str,
    max_records: int | None = None,
    fields: list[str] | None = None,
    sort: list[str] | None = None,
) -> list[dict]:
    """List records from a table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        max_records: Maximum number of records to return (optional).
        fields: List of field names to return (optional).
        sort: List of sort fields in pyairtable format (optional).

    Returns:
        List of dictionaries with record ID and field values.
    """
    base = api.base(base_id)
    table = base.table(table_name)

    # Build kwargs for the all() call
    kwargs = {}
    if max_records is not None:
        kwargs["max_records"] = max_records
    if fields is not None:
        kwargs["fields"] = fields
    if sort is not None:
        kwargs["sort"] = sort

    results = table.all(**kwargs)

    return [
        {
            "id": record["id"],
            "fields": record["fields"],
        }
        for record in results
    ]


def update_record(
    api: Api, base_id: str, table_name: str, record_id: str, fields_json: str
) -> dict:
    """Update a record's fields.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        record_id: The ID of the record to update.
        fields_json: JSON string of field values to update.

    Returns:
        Dictionary with updated record ID and field values.

    Raises:
        ValueError: If fields_json is invalid.
    """
    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for fields: {e}") from e

    if not isinstance(fields, dict):
        raise ValueError("Fields must be a JSON object")

    if not fields:
        raise ValueError("At least one field is required")

    # Update the record (partial update - only specified fields are modified)
    base = api.base(base_id)
    table = base.table(table_name)
    result = table.update(record_id, fields)

    return {
        "id": result["id"],
        "fields": result["fields"],
    }


def delete_record(api: Api, base_id: str, table_name: str, record_id: str) -> dict:
    """Delete a record by ID.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        record_id: The ID of the record to delete.

    Returns:
        Dictionary with deleted record ID and deleted flag.
    """
    base = api.base(base_id)
    table = base.table(table_name)
    result = table.delete(record_id)

    return {
        "id": result["id"],
        "deleted": result["deleted"],
    }


def query_records(
    api: Api,
    base_id: str,
    table_name: str,
    formula: str | None = None,
    match_dict: dict | None = None,
) -> list[dict]:
    """Query records using formula or match criteria.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        formula: Airtable formula string (e.g., "{Field}='value'", "{Field}>5").
        match_dict: Dictionary for equality matching (uses pyairtable's match()).

    Returns:
        List of dictionaries with record ID and field values.

    Raises:
        ValueError: If neither formula nor match_dict is provided, or if both are provided.
    """
    if formula is None and match_dict is None:
        raise ValueError("Either --formula or --match must be provided")
    if formula is not None and match_dict is not None:
        raise ValueError("Cannot use both --formula and --match together")

    base = api.base(base_id)
    table = base.table(table_name)

    # Build the formula for the query
    if match_dict is not None:
        query_formula = formula_match(match_dict)
    else:
        query_formula = formula

    results = table.all(formula=query_formula)

    return [
        {
            "id": record["id"],
            "fields": record["fields"],
        }
        for record in results
    ]


def list_comments(
    api: Api, base_id: str, table_name: str, record_id: str
) -> list[dict]:
    """List comments on a record.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        record_id: The ID of the record.

    Returns:
        List of dictionaries with comment ID, author, text, and created time.
    """
    base = api.base(base_id)
    table = base.table(table_name)
    comments = table.comments(record_id)

    return [
        {
            "id": comment.id,
            "author": comment.author.name if comment.author else None,
            "text": comment.text,
            "createdTime": comment.created_time.isoformat(),
        }
        for comment in comments
    ]


def add_comment(
    api: Api, base_id: str, table_name: str, record_id: str, text: str
) -> dict:
    """Add a comment to a record.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        record_id: The ID of the record.
        text: The comment text.

    Returns:
        Dictionary with comment ID and confirmation.
    """
    base = api.base(base_id)
    table = base.table(table_name)
    comment = table.add_comment(record_id, text)

    return {
        "id": comment.id,
        "text": comment.text,
    }


def delete_comment(
    api: Api, base_id: str, table_name: str, record_id: str, comment_id: str
) -> dict:
    """Delete a comment from a record.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table.
        record_id: The ID of the record.
        comment_id: The ID of the comment to delete.

    Returns:
        Dictionary with deleted comment ID and confirmation.

    Raises:
        ValueError: If the comment is not found on the record.
    """
    base = api.base(base_id)
    table = base.table(table_name)
    comments = table.comments(record_id)

    target = None
    for comment in comments:
        if comment.id == comment_id:
            target = comment
            break

    if target is None:
        raise ValueError(
            f"Comment '{comment_id}' not found on record '{record_id}'"
        )

    target.delete()

    return {
        "id": comment_id,
        "deleted": True,
    }


def print_records_table(records: list[dict], empty_message: str) -> bool:
    """Print records in a formatted table.

    Returns True if records were printed, False if empty.
    """
    if not records:
        print(empty_message)
        return False

    # Collect all field names from all records
    all_field_names: set[str] = set()
    for record in records:
        all_field_names.update(record["fields"].keys())
    field_names = sorted(all_field_names)

    # Calculate column widths
    id_header = "ID"
    id_width = max(len(id_header), max(len(r["id"]) for r in records))

    col_widths: dict[str, int] = {}
    for name in field_names:
        max_value_len = 0
        for record in records:
            value = record["fields"].get(name, "")
            value_str = str(value) if value is not None else ""
            max_value_len = max(max_value_len, len(value_str))
        col_widths[name] = max(len(name), max_value_len)

    # Print header
    header_parts = [id_header.ljust(id_width)]
    for name in field_names:
        header_parts.append(name.ljust(col_widths[name]))
    print("  ".join(header_parts))

    # Print separator
    sep_parts = ["-" * id_width]
    for name in field_names:
        sep_parts.append("-" * col_widths[name])
    print("  ".join(sep_parts))

    # Print records
    for record in records:
        row_parts = [record["id"].ljust(id_width)]
        for name in field_names:
            value = record["fields"].get(name, "")
            value_str = str(value) if value is not None else ""
            row_parts.append(value_str.ljust(col_widths[name]))
        print("  ".join(row_parts))

    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Airtable record management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create subcommand
    create_parser = subparsers.add_parser("create", help="Create a single record")
    create_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    create_parser.add_argument("--table", required=True, help="The table name or ID")
    create_parser.add_argument(
        "--fields",
        required=True,
        help='JSON object of field values (e.g., \'{"Name": "John", "Email": "john@example.com"}\')',
    )
    create_parser.add_argument(
        "--json", action="store_true", help="Output as JSON with record ID and fields"
    )

    # get subcommand
    get_parser = subparsers.add_parser("get", help="Get a record by ID")
    get_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    get_parser.add_argument("--table", required=True, help="The table name or ID")
    get_parser.add_argument(
        "--record-id", required=True, help="The record ID to retrieve"
    )
    get_parser.add_argument(
        "--json", action="store_true", help="Output full record as JSON"
    )

    # list subcommand
    list_parser = subparsers.add_parser("list", help="List records from a table")
    list_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    list_parser.add_argument("--table", required=True, help="The table name or ID")
    list_parser.add_argument(
        "--max-records",
        type=int,
        help="Maximum number of records to return",
    )
    list_parser.add_argument(
        "--fields",
        help="Comma-separated list of field names to return (e.g., 'Name,Email')",
    )
    list_parser.add_argument(
        "--sort",
        help="Sort by field(s). Use ':desc' suffix for descending. "
        "Multiple fields: 'Name,Age:desc'",
    )
    list_parser.add_argument(
        "--json", action="store_true", help="Output records as JSON array"
    )

    # update subcommand
    update_parser = subparsers.add_parser("update", help="Update a record by ID")
    update_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    update_parser.add_argument("--table", required=True, help="The table name or ID")
    update_parser.add_argument(
        "--record-id", required=True, help="The record ID to update"
    )
    update_parser.add_argument(
        "--fields",
        required=True,
        help='JSON object of field values to update (e.g., \'{"Name": "New Name"}\')',
    )
    update_parser.add_argument(
        "--json", action="store_true", help="Output updated record as JSON"
    )

    # delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete a record by ID")
    delete_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    delete_parser.add_argument("--table", required=True, help="The table name or ID")
    delete_parser.add_argument(
        "--record-id", required=True, help="The record ID to delete"
    )

    # query subcommand
    query_parser = subparsers.add_parser(
        "query", help="Query records with formula or match criteria"
    )
    query_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    query_parser.add_argument("--table", required=True, help="The table name or ID")
    query_parser.add_argument(
        "--formula",
        help="Airtable formula string. Supports: basic comparisons ({Field}='value'), "
        "lookup fields ({Property Status (from Properties)}='Active'), "
        "rollup fields ({Total Amount}>1000), "
        "text functions (FIND(), SEARCH()), "
        "and ARRAYJOIN() for multi-value fields.",
    )
    query_parser.add_argument(
        "--match",
        help='JSON object for equality matching (e.g., \'{"Name": "John", "Age": 21}\')',
    )
    query_parser.add_argument(
        "--json", action="store_true", help="Output matching records as JSON array"
    )

    # comments subcommand
    comments_parser = subparsers.add_parser(
        "comments", help="List comments on a record"
    )
    comments_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    comments_parser.add_argument("--table", required=True, help="The table name or ID")
    comments_parser.add_argument(
        "--record-id", required=True, help="The record ID to list comments for"
    )
    comments_parser.add_argument(
        "--json", action="store_true", help="Output comments as JSON array"
    )

    # add-comment subcommand
    add_comment_parser = subparsers.add_parser(
        "add-comment", help="Add a comment to a record"
    )
    add_comment_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    add_comment_parser.add_argument(
        "--table", required=True, help="The table name or ID"
    )
    add_comment_parser.add_argument(
        "--record-id", required=True, help="The record ID to add comment to"
    )
    add_comment_parser.add_argument(
        "--text", required=True, help="The comment text"
    )

    # delete-comment subcommand
    delete_comment_parser = subparsers.add_parser(
        "delete-comment", help="Delete a comment from a record"
    )
    delete_comment_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    delete_comment_parser.add_argument(
        "--table", required=True, help="The table name or ID"
    )
    delete_comment_parser.add_argument(
        "--record-id", required=True, help="The record ID containing the comment"
    )
    delete_comment_parser.add_argument(
        "--comment-id", required=True, help="The comment ID to delete"
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
            result = create_record(api, args.base_id, args.table, args.fields)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Created record: {result['id']}")
                print("")
                print("Fields:")
                for name, value in result["fields"].items():
                    print(f"  {name}: {value}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error creating record: {e}", file=sys.stderr)
            return 1

    elif args.command == "get":
        try:
            result = get_record(api, args.base_id, args.table, args.record_id)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Record ID: {result['id']}")
                print(f"Created: {result['createdTime']}")
                print("")
                print("Fields:")
                for name, value in result["fields"].items():
                    print(f"  {name}: {value}")
            return 0
        except Exception as e:
            print(f"Error getting record: {e}", file=sys.stderr)
            return 1

    elif args.command == "list":
        try:
            # Parse fields if provided
            fields_list = None
            if args.fields:
                fields_list = [f.strip() for f in args.fields.split(",")]

            # Parse sort if provided
            sort_list = None
            if args.sort:
                sort_list = parse_sort_spec(args.sort)

            records = list_records(
                api,
                args.base_id,
                args.table,
                max_records=args.max_records,
                fields=fields_list,
                sort=sort_list,
            )

            if args.json:
                print(json.dumps(records, indent=2))
            else:
                print_records_table(records, "No records found.")

            return 0
        except Exception as e:
            print(f"Error listing records: {e}", file=sys.stderr)
            return 1

    elif args.command == "update":
        try:
            result = update_record(
                api, args.base_id, args.table, args.record_id, args.fields
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Updated record: {result['id']}")
                print("")
                print("Fields:")
                for name, value in result["fields"].items():
                    print(f"  {name}: {value}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error updating record: {e}", file=sys.stderr)
            return 1

    elif args.command == "delete":
        try:
            result = delete_record(api, args.base_id, args.table, args.record_id)
            print(f"Deleted record: {result['id']}")
            return 0
        except Exception as e:
            print(f"Error deleting record: {e}", file=sys.stderr)
            return 1

    elif args.command == "query":
        try:
            # Parse match JSON if provided
            match_dict = None
            if args.match:
                try:
                    match_dict = json.loads(args.match)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON for match: {e}") from e

                if not isinstance(match_dict, dict):
                    raise ValueError("Match must be a JSON object")

            records = query_records(
                api,
                args.base_id,
                args.table,
                formula=args.formula,
                match_dict=match_dict,
            )

            if args.json:
                print(json.dumps(records, indent=2))
            else:
                print_records_table(records, "No matching records found.")

            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error querying records: {e}", file=sys.stderr)
            return 1

    elif args.command == "comments":
        try:
            comments = list_comments(api, args.base_id, args.table, args.record_id)

            if args.json:
                print(json.dumps(comments, indent=2))
            else:
                if not comments:
                    print("No comments found.")
                    return 0

                for comment in comments:
                    print(f"Comment ID: {comment['id']}")
                    print(f"Author: {comment['author']}")
                    print(f"Text: {comment['text']}")
                    print(f"Created Time: {comment['createdTime']}")
                    print("")

            return 0
        except Exception as e:
            print(f"Error listing comments: {e}", file=sys.stderr)
            return 1

    elif args.command == "add-comment":
        try:
            result = add_comment(
                api, args.base_id, args.table, args.record_id, args.text
            )
            print(f"Created comment: {result['id']}")
            return 0
        except Exception as e:
            print(f"Error adding comment: {e}", file=sys.stderr)
            return 1

    elif args.command == "delete-comment":
        try:
            result = delete_comment(
                api, args.base_id, args.table, args.record_id, args.comment_id
            )
            print(f"Deleted comment: {result['id']}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error deleting comment: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
