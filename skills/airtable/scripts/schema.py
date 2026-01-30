#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyairtable>=3.3.0",
# ]
# ///
"""
Airtable schema management script.

List tables in a base, view detailed field information, create new tables, delete tables, add fields, and update fields.

Usage:
    uv run schema.py tables list --base-id <id>
    uv run schema.py tables list --base-id <id> --json
    uv run schema.py tables describe --base-id <id> --table <name>
    uv run schema.py tables describe --base-id <id> --table <name> --json
    uv run schema.py tables create --base-id <id> --name <name> --fields <json>
    uv run schema.py tables create --base-id <id> --name <name> --fields <json> --json
    uv run schema.py tables delete --base-id <id> --table <name>
    uv run schema.py fields create --base-id <id> --table <name> --field <json>
    uv run schema.py fields create --base-id <id> --table <name> --field <json> --json
    uv run schema.py fields update --base-id <id> --table <name> --field-id <id> --name <new-name>
    uv run schema.py fields update --base-id <id> --table <name> --field-id <id> --description <desc>
"""

import argparse
import json
import os
import sys

from pyairtable import Api


def get_api_token() -> str | None:
    """Get the Airtable API token from environment."""
    return os.environ.get("AIRTABLE_API_TOKEN")


def list_tables(api: Api, base_id: str) -> list[dict]:
    """List all tables in a base with field counts."""
    base = api.base(base_id)
    schema = base.schema()

    tables = []
    for table_schema in schema.tables:
        tables.append({
            "id": table_schema.id,
            "name": table_schema.name,
            "field_count": len(table_schema.fields),
        })

    return tables


def describe_table(api: Api, base_id: str, table_name: str) -> dict:
    """Get detailed information about a table including fields."""
    base = api.base(base_id)
    table = base.table(table_name)
    table_schema = table.schema()

    fields = []
    for field in table_schema.fields:
        fields.append({
            "id": field.id,
            "name": field.name,
            "type": field.type,
        })

    return {
        "id": table_schema.id,
        "name": table_schema.name,
        "fields": fields,
    }


# Table creation supports fewer types because the Airtable API only allows
# simple field types when creating a brand-new table.
TABLE_CREATION_FIELD_TYPES = {
    "singleLineText",
    "number",
    "singleSelect",
    "checkbox",
    "date",
    "dateTime",
    "email",
    "url",
}

# Adding a field to an existing table is more permissive — relational,
# computed, and rich-content types are all available.
FIELD_CREATION_FIELD_TYPES = {
    "singleLineText",
    "multilineText",
    "number",
    "singleSelect",
    "multipleSelects",
    "checkbox",
    "date",
    "dateTime",
    "email",
    "url",
    "phoneNumber",
    "currency",
    "percent",
    "duration",
    "rating",
    "richText",
    "multipleRecordLinks",
    "multipleAttachments",
    "multipleLookupValues",
    "rollup",
}

# Supported rollup aggregation functions
SUPPORTED_ROLLUP_FUNCTIONS = {
    "SUM",
    "COUNT",
    "AVERAGE",
    "MAX",
    "MIN",
    "COUNTA",
    "COUNTALL",
    "CONCATENATE",
    "ARRAYJOIN",
    "ARRAYUNIQUE",
    "ARRAYCOMPACT",
}


def validate_field_definition(field: dict, allowed_types: set[str] | None = None) -> str | None:
    """Validate a field definition. Returns error message or None if valid.

    Args:
        field: Dictionary with at least 'name' and 'type' keys.
        allowed_types: Set of accepted type strings.
            Defaults to TABLE_CREATION_FIELD_TYPES when None.
    """
    if allowed_types is None:
        allowed_types = TABLE_CREATION_FIELD_TYPES

    if "name" not in field:
        return "Field must have a 'name' property"
    if "type" not in field:
        return f"Field '{field.get('name', 'unknown')}' must have a 'type' property"
    if field["type"] not in allowed_types:
        return (
            f"Field '{field['name']}' has unsupported type '{field['type']}'. "
            f"Supported types: {', '.join(sorted(allowed_types))}"
        )
    # Validate multipleRecordLinks requires linkedTableId or linkedTableName in options
    if field["type"] == "multipleRecordLinks":
        options = field.get("options", {})
        if not options.get("linkedTableId") and not options.get("linkedTableName"):
            return (
                f"Field '{field['name']}' of type 'multipleRecordLinks' requires "
                "'options.linkedTableId' or 'options.linkedTableName' to specify the linked table"
            )
    # Validate multipleLookupValues requires recordLinkFieldId and fieldIdInLinkedTable in options
    if field["type"] == "multipleLookupValues":
        options = field.get("options", {})
        if not options.get("recordLinkFieldId") and not options.get("recordLinkFieldName"):
            return (
                f"Field '{field['name']}' of type 'multipleLookupValues' requires "
                "'options.recordLinkFieldId' or 'options.recordLinkFieldName' to specify the link field"
            )
        if not options.get("fieldIdInLinkedTable") and not options.get("fieldNameInLinkedTable"):
            return (
                f"Field '{field['name']}' of type 'multipleLookupValues' requires "
                "'options.fieldIdInLinkedTable' or 'options.fieldNameInLinkedTable' to specify the field to look up"
            )
    # Validate rollup requires recordLinkFieldId, fieldIdInLinkedTable, and aggregation function in options
    if field["type"] == "rollup":
        options = field.get("options", {})
        if not options.get("recordLinkFieldId") and not options.get("recordLinkFieldName"):
            return (
                f"Field '{field['name']}' of type 'rollup' requires "
                "'options.recordLinkFieldId' or 'options.recordLinkFieldName' to specify the link field"
            )
        if not options.get("fieldIdInLinkedTable") and not options.get("fieldNameInLinkedTable"):
            return (
                f"Field '{field['name']}' of type 'rollup' requires "
                "'options.fieldIdInLinkedTable' or 'options.fieldNameInLinkedTable' to specify the field to aggregate"
            )
        # Validate aggregation function - Airtable uses a formula string that contains the function
        # Accept either 'formula' (raw Airtable format) or 'aggregationFunction' (simplified format)
        if not options.get("formula") and not options.get("aggregationFunction"):
            return (
                f"Field '{field['name']}' of type 'rollup' requires "
                "'options.formula' or 'options.aggregationFunction' to specify the aggregation (e.g., SUM, COUNT, AVERAGE)"
            )
        # Validate the aggregation function if provided
        if options.get("aggregationFunction"):
            func = options["aggregationFunction"].upper()
            if func not in SUPPORTED_ROLLUP_FUNCTIONS:
                return (
                    f"Field '{field['name']}' has unsupported aggregation function '{options['aggregationFunction']}'. "
                    f"Supported functions: {', '.join(sorted(SUPPORTED_ROLLUP_FUNCTIONS))}"
                )
    return None


def create_table(api: Api, base_id: str, name: str, fields_json: str) -> dict:
    """Create a new table with the specified fields.

    Args:
        api: The Airtable API instance.
        base_id: The base ID to create the table in.
        name: The name of the new table.
        fields_json: JSON string defining the fields.

    Returns:
        Dictionary with created table ID and field information.

    Raises:
        ValueError: If fields_json is invalid or contains unsupported field types.
    """
    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for fields: {e}") from e

    if not isinstance(fields, list):
        raise ValueError("Fields must be a JSON array")

    if not fields:
        raise ValueError("At least one field is required")

    # Validate all fields
    for field in fields:
        error = validate_field_definition(field)
        if error:
            raise ValueError(error)

    # Create the table
    base = api.base(base_id)
    new_table = base.create_table(name=name, fields=fields)

    # Get the created table schema to return field IDs
    table = base.table(new_table.id)
    table_schema = table.schema()

    created_fields = []
    for field in table_schema.fields:
        created_fields.append({
            "id": field.id,
            "name": field.name,
            "type": field.type,
        })

    return {
        "id": new_table.id,
        "name": new_table.name,
        "fields": created_fields,
    }


def delete_table(api: Api, base_id: str, table_name: str) -> dict:
    """Delete a table from the base.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table to delete.

    Returns:
        Dictionary with deleted table name confirmation.
    """
    base = api.base(base_id)
    table = base.table(table_name)
    table_schema = table.schema()

    # Store the name before deletion
    deleted_name = table_schema.name
    table_id = table_schema.id

    # Delete using the Airtable API
    api.request(
        method="DELETE",
        url=f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}",
    )

    return {
        "deleted": True,
        "name": deleted_name,
    }


def resolve_linked_table_name(api: Api, base_id: str, table_name: str) -> str:
    """Resolve a table name to its ID.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name of the table to resolve.

    Returns:
        The table ID.

    Raises:
        ValueError: If the table is not found.
    """
    base = api.base(base_id)
    schema = base.schema()

    for table_schema in schema.tables:
        if table_schema.name == table_name:
            return table_schema.id

    raise ValueError(f"Table '{table_name}' not found in base '{base_id}'")


def resolve_field_name(api: Api, base_id: str, table_name: str, field_name: str) -> str:
    """Resolve a field name to its ID.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table containing the field.
        field_name: The name of the field to resolve.

    Returns:
        The field ID.

    Raises:
        ValueError: If the field is not found.
    """
    base = api.base(base_id)
    table = base.table(table_name)
    table_schema = table.schema()

    for field in table_schema.fields:
        if field.name == field_name:
            return field.id

    raise ValueError(f"Field '{field_name}' not found in table '{table_name}'")


def _resolve_linked_field(api: Api, base_id: str, table_name: str, record_link_field_id: str, field_name: str) -> str:
    """Resolve a field name in a linked table to its field ID.

    Finds the linked table by inspecting the record link field's options,
    then resolves the field name within that linked table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table containing the record link field.
        record_link_field_id: The ID of the record link field.
        field_name: The name of the field in the linked table to resolve.

    Returns:
        The field ID in the linked table.

    Raises:
        ValueError: If the linked table or field cannot be determined.
    """
    base = api.base(base_id)
    table_for_schema = base.table(table_name)
    table_schema = table_for_schema.schema()
    linked_table_id = None
    for fld in table_schema.fields:
        if fld.id == record_link_field_id:
            if hasattr(fld, "options") and fld.options:
                linked_table_id = getattr(fld.options, "linked_table_id", None)
            break
    if not linked_table_id:
        raise ValueError(
            f"Could not determine linked table for record link field '{record_link_field_id}'"
        )
    return resolve_field_name(api, base_id, linked_table_id, field_name)


def create_field(api: Api, base_id: str, table_name: str, field_json: str) -> dict:
    """Create a new field on an existing table.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table to add the field to.
        field_json: JSON string defining the field.

    Returns:
        Dictionary with created field ID, name, type, and options for link fields.

    Raises:
        ValueError: If field_json is invalid or contains unsupported field types.
    """
    try:
        field = json.loads(field_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for field: {e}") from e

    if not isinstance(field, dict):
        raise ValueError("Field must be a JSON object")

    # Validate the field definition
    error = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
    if error:
        raise ValueError(error)

    # Extract field properties
    name = field["name"]
    field_type = field["type"]
    description = field.get("description")
    options = field.get("options")

    # For multipleRecordLinks, resolve linkedTableName to linkedTableId if needed
    if field_type == "multipleRecordLinks" and options:
        if options.get("linkedTableName") and not options.get("linkedTableId"):
            linked_table_name = options.pop("linkedTableName")
            options["linkedTableId"] = resolve_linked_table_name(api, base_id, linked_table_name)

    # For multipleLookupValues, resolve field names to field IDs if needed
    if field_type == "multipleLookupValues" and options:
        # Resolve recordLinkFieldName to recordLinkFieldId
        if options.get("recordLinkFieldName") and not options.get("recordLinkFieldId"):
            record_link_field_name = options.pop("recordLinkFieldName")
            options["recordLinkFieldId"] = resolve_field_name(api, base_id, table_name, record_link_field_name)

        # To resolve fieldNameInLinkedTable, we need to find the linked table first
        if options.get("fieldNameInLinkedTable") and not options.get("fieldIdInLinkedTable"):
            field_name_in_linked_table = options.pop("fieldNameInLinkedTable")
            options["fieldIdInLinkedTable"] = _resolve_linked_field(
                api, base_id, table_name, options["recordLinkFieldId"], field_name_in_linked_table
            )

    # For rollup, resolve field names to field IDs and convert aggregationFunction to formula if needed
    if field_type == "rollup" and options:
        # Resolve recordLinkFieldName to recordLinkFieldId
        if options.get("recordLinkFieldName") and not options.get("recordLinkFieldId"):
            record_link_field_name = options.pop("recordLinkFieldName")
            options["recordLinkFieldId"] = resolve_field_name(api, base_id, table_name, record_link_field_name)

        # To resolve fieldNameInLinkedTable, we need to find the linked table first
        if options.get("fieldNameInLinkedTable") and not options.get("fieldIdInLinkedTable"):
            field_name_in_linked_table = options.pop("fieldNameInLinkedTable")
            options["fieldIdInLinkedTable"] = _resolve_linked_field(
                api, base_id, table_name, options["recordLinkFieldId"], field_name_in_linked_table
            )

        # Convert aggregationFunction to formula format expected by Airtable API
        if options.get("aggregationFunction") and not options.get("formula"):
            func = options.pop("aggregationFunction").upper()
            # Airtable expects the formula in the format: FUNCTION(values)
            options["formula"] = f"{func}(values)"

    # Create the field (validate=True resolves table name to ID for meta API)
    base = api.base(base_id)
    table = base.table(table_name, validate=True)
    created_field = table.create_field(
        name=name,
        field_type=field_type,
        description=description,
        options=options,
    )

    result = {
        "id": created_field.id,
        "name": created_field.name,
        "type": created_field.type,
    }

    # Include link configuration for multipleRecordLinks fields
    if field_type == "multipleRecordLinks" and options:
        result["options"] = {}
        if options.get("linkedTableId"):
            result["options"]["linkedTableId"] = options["linkedTableId"]
        if options.get("prefersSingleRecordLink"):
            result["options"]["prefersSingleRecordLink"] = options["prefersSingleRecordLink"]

    # Include lookup configuration for multipleLookupValues fields
    if field_type == "multipleLookupValues" and options:
        result["options"] = {}
        if options.get("recordLinkFieldId"):
            result["options"]["recordLinkFieldId"] = options["recordLinkFieldId"]
        if options.get("fieldIdInLinkedTable"):
            result["options"]["fieldIdInLinkedTable"] = options["fieldIdInLinkedTable"]

    # Include rollup configuration for rollup fields
    if field_type == "rollup" and options:
        result["options"] = {}
        if options.get("recordLinkFieldId"):
            result["options"]["recordLinkFieldId"] = options["recordLinkFieldId"]
        if options.get("fieldIdInLinkedTable"):
            result["options"]["fieldIdInLinkedTable"] = options["fieldIdInLinkedTable"]
        if options.get("formula"):
            result["options"]["formula"] = options["formula"]

    return result


def update_field(
    api: Api, base_id: str, table_name: str, field_id: str, name: str | None = None, description: str | None = None
) -> dict:
    """Update an existing field's name or description.

    Args:
        api: The Airtable API instance.
        base_id: The base ID containing the table.
        table_name: The name or ID of the table containing the field.
        field_id: The ID of the field to update.
        name: New name for the field (optional).
        description: New description for the field (optional).

    Returns:
        Dictionary with updated field ID, name, type, and description.

    Raises:
        ValueError: If neither name nor description is provided.
    """
    if name is None and description is None:
        raise ValueError("At least one of --name or --description must be provided")

    base = api.base(base_id)
    table = base.table(table_name)
    table_schema = table.schema()

    # Find the field in the schema
    field = None
    for f in table_schema.fields:
        if f.id == field_id:
            field = f
            break

    if field is None:
        raise ValueError(f"Field with ID '{field_id}' not found in table '{table_name}'")

    # Update field properties
    if name is not None:
        field.name = name
    if description is not None:
        field.description = description

    # Save the changes
    field.save()

    result = {
        "id": field.id,
        "name": field.name,
        "type": field.type,
    }
    if field.description:
        result["description"] = field.description

    return result


def format_tables_table(tables: list[dict]) -> str:
    """Format tables list as a table with columns: Table ID, Table Name, Field Count."""
    if not tables:
        return "No tables found."

    # Calculate column widths
    id_width = max(len("Table ID"), max(len(t["id"]) for t in tables))
    name_width = max(len("Table Name"), max(len(t["name"]) for t in tables))
    count_width = max(len("Field Count"), max(len(str(t["field_count"])) for t in tables))

    # Build table
    lines = []
    header = f"{'Table ID':<{id_width}}  {'Table Name':<{name_width}}  {'Field Count':>{count_width}}"
    separator = f"{'-' * id_width}  {'-' * name_width}  {'-' * count_width}"
    lines.append(header)
    lines.append(separator)

    for table in tables:
        lines.append(
            f"{table['id']:<{id_width}}  {table['name']:<{name_width}}  {table['field_count']:>{count_width}}"
        )

    return "\n".join(lines)


def format_fields_table(table_info: dict) -> str:
    """Format table description with field details."""
    lines = []
    lines.append(f"Table: {table_info['name']} ({table_info['id']})")
    lines.append("")

    fields = table_info["fields"]
    if not fields:
        lines.append("No fields found.")
        return "\n".join(lines)

    # Calculate column widths
    name_width = max(len("Field Name"), max(len(f["name"]) for f in fields))
    type_width = max(len("Field Type"), max(len(f["type"]) for f in fields))
    id_width = max(len("Field ID"), max(len(f["id"]) for f in fields))

    # Build fields table
    header = f"{'Field Name':<{name_width}}  {'Field Type':<{type_width}}  {'Field ID':<{id_width}}"
    separator = f"{'-' * name_width}  {'-' * type_width}  {'-' * id_width}"
    lines.append(header)
    lines.append(separator)

    for field in fields:
        lines.append(
            f"{field['name']:<{name_width}}  {field['type']:<{type_width}}  {field['id']:<{id_width}}"
        )

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Airtable schema management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # tables subcommand group
    tables_parser = subparsers.add_parser("tables", help="Table operations")
    tables_subparsers = tables_parser.add_subparsers(dest="tables_command", required=True)

    # tables list subcommand
    tables_list_parser = tables_subparsers.add_parser("list", help="List all tables in a base")
    tables_list_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    tables_list_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # tables describe subcommand
    tables_describe_parser = tables_subparsers.add_parser(
        "describe", help="Show detailed field info for a table"
    )
    tables_describe_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    tables_describe_parser.add_argument(
        "--table", required=True, help="The table name or ID"
    )
    tables_describe_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # tables create subcommand
    tables_create_parser = tables_subparsers.add_parser(
        "create", help="Create a new table with specified fields"
    )
    tables_create_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    tables_create_parser.add_argument(
        "--name", required=True, help="The name for the new table"
    )
    tables_create_parser.add_argument(
        "--fields",
        required=True,
        help=(
            "JSON array of field definitions. "
            "Supported types: singleLineText, number, singleSelect, checkbox, date, dateTime, email, url"
        ),
    )
    tables_create_parser.add_argument(
        "--json", action="store_true", help="Output as JSON with table ID and field IDs"
    )

    # tables delete subcommand
    tables_delete_parser = tables_subparsers.add_parser(
        "delete", help="Delete a table from the base"
    )
    tables_delete_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    tables_delete_parser.add_argument(
        "--table", required=True, help="The table name or ID to delete"
    )
    tables_delete_parser.add_argument(
        "--json", action="store_true", help="Output as JSON with deleted table name"
    )

    # fields subcommand group
    fields_parser = subparsers.add_parser("fields", help="Field operations")
    fields_subparsers = fields_parser.add_subparsers(dest="fields_command", required=True)

    # fields create subcommand
    fields_create_parser = fields_subparsers.add_parser(
        "create", help="Create a new field on an existing table"
    )
    fields_create_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    fields_create_parser.add_argument(
        "--table", required=True, help="The table name or ID"
    )
    fields_create_parser.add_argument(
        "--field",
        required=True,
        help=(
            "JSON object defining the field. Must include 'name' and 'type'. "
            "For multipleRecordLinks, include 'options.linkedTableId' or 'options.linkedTableName'. "
            "Optional: 'options.prefersSingleRecordLink' (true/false) for single-link behavior. "
            "For multipleLookupValues, include 'options.recordLinkFieldId' or 'options.recordLinkFieldName' "
            "and 'options.fieldIdInLinkedTable' or 'options.fieldNameInLinkedTable'. "
            "For rollup, include 'options.recordLinkFieldId' or 'options.recordLinkFieldName', "
            "'options.fieldIdInLinkedTable' or 'options.fieldNameInLinkedTable', "
            "and 'options.aggregationFunction' (SUM, COUNT, AVERAGE, MAX, MIN, COUNTA, etc.) or 'options.formula'. "
            "Supported types: singleLineText, multilineText, number, singleSelect, "
            "multipleSelects, checkbox, date, dateTime, email, url, phoneNumber, "
            "currency, percent, duration, rating, richText, multipleRecordLinks, multipleAttachments, "
            "multipleLookupValues, rollup"
        ),
    )
    fields_create_parser.add_argument(
        "--json", action="store_true", help="Output as JSON with field ID"
    )

    # fields update subcommand
    fields_update_parser = fields_subparsers.add_parser(
        "update", help="Update a field's name or description"
    )
    fields_update_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    fields_update_parser.add_argument(
        "--table", required=True, help="The table name or ID"
    )
    fields_update_parser.add_argument(
        "--field-id", required=True, help="The field ID to update"
    )
    fields_update_parser.add_argument(
        "--name", help="New name for the field"
    )
    fields_update_parser.add_argument(
        "--description", help="New description for the field"
    )
    fields_update_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    args = parser.parse_args()

    # Check for API token
    token = get_api_token()
    if not token:
        print("Error: AIRTABLE_API_TOKEN environment variable is not set.", file=sys.stderr)
        print("Set it with: export AIRTABLE_API_TOKEN=your_token", file=sys.stderr)
        return 1

    api = Api(token)

    if args.command == "tables":
        if args.tables_command == "list":
            try:
                tables = list_tables(api, args.base_id)
                if args.json:
                    print(json.dumps(tables, indent=2))
                else:
                    print(format_tables_table(tables))
                return 0
            except Exception as e:
                print(f"Error listing tables: {e}", file=sys.stderr)
                return 1

        elif args.tables_command == "describe":
            try:
                table_info = describe_table(api, args.base_id, args.table)
                if args.json:
                    print(json.dumps(table_info, indent=2))
                else:
                    print(format_fields_table(table_info))
                return 0
            except Exception as e:
                print(f"Error describing table: {e}", file=sys.stderr)
                return 1

        elif args.tables_command == "create":
            try:
                result = create_table(api, args.base_id, args.name, args.fields)
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Created table '{result['name']}' with ID: {result['id']}")
                    print(f"Fields created: {len(result['fields'])}")
                return 0
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"Error creating table: {e}", file=sys.stderr)
                return 1

        elif args.tables_command == "delete":
            try:
                result = delete_table(api, args.base_id, args.table)
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Deleted table '{result['name']}'")
                return 0
            except Exception as e:
                print(f"Error deleting table: {e}", file=sys.stderr)
                return 1

    elif args.command == "fields":
        if args.fields_command == "create":
            try:
                result = create_field(api, args.base_id, args.table, args.field)
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Created field '{result['name']}' with ID: {result['id']}")
                    print(f"Type: {result['type']}")
                return 0
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"Error creating field: {e}", file=sys.stderr)
                return 1

        elif args.fields_command == "update":
            try:
                result = update_field(
                    api, args.base_id, args.table, args.field_id, args.name, args.description
                )
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Updated field '{result['name']}' (ID: {result['id']})")
                    print(f"Type: {result['type']}")
                    if result.get("description"):
                        print(f"Description: {result['description']}")
                return 0
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"Error updating field: {e}", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
