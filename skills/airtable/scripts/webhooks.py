#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyairtable>=3.3.0",
# ]
# ///
"""
Airtable webhook management script.

Create and manage webhooks for receiving notifications of changes.

Usage:
    uv run webhooks.py create --base-id <id> --url <notification-url> --spec <json>
    uv run webhooks.py create --base-id <id> --url <notification-url> --spec <json> --json
    uv run webhooks.py list --base-id <id>
    uv run webhooks.py list --base-id <id> --json
    uv run webhooks.py get --base-id <id> --webhook-id <id>
    uv run webhooks.py get --base-id <id> --webhook-id <id> --json
    uv run webhooks.py delete --base-id <id> --webhook-id <id>
    uv run webhooks.py payloads --base-id <id> --webhook-id <id>
    uv run webhooks.py payloads --base-id <id> --webhook-id <id> --cursor <cursor>
    uv run webhooks.py payloads --base-id <id> --webhook-id <id> --json

Specification Examples:
    # Watch all table data changes
    --spec '{"options": {"filters": {"dataTypes": ["tableData"]}}}'

    # Watch specific table
    --spec '{"options": {"filters": {"dataTypes": ["tableData"], "recordChangeScope": "tblXXXXXXXXXXX"}}}'

    # Watch specific fields
    --spec '{"options": {"filters": {"dataTypes": ["tableData"], "watchDataInFieldIds": ["fldXXXXXXX", "fldYYYYYYY"]}}}'

    # Watch only specific change types
    --spec '{"options": {"filters": {"dataTypes": ["tableData"], "changeTypes": ["add", "update"]}}}'

    # Include cell values in notifications
    --spec '{"options": {"filters": {"dataTypes": ["tableData"]}, "includes": {"includeCellValuesInFieldIds": "all"}}}'
"""

import argparse
import json
import os
import sys

from pyairtable import Api


def get_api_token() -> str | None:
    """Get the Airtable API token from environment."""
    return os.environ.get("AIRTABLE_API_TOKEN")


def list_webhooks(api: Api, base_id: str) -> list[dict]:
    """List all webhooks on a base.

    Args:
        api: The Airtable API instance.
        base_id: The base ID to list webhooks for.

    Returns:
        List of dictionaries with webhook details.
    """
    base = api.base(base_id)
    webhooks = base.webhooks()

    return [
        {
            "id": webhook.id,
            "notification_url": webhook.notification_url,
            "expiration_time": (
                webhook.expiration_time.isoformat() if webhook.expiration_time else None
            ),
            "is_active": webhook.is_hook_enabled,
        }
        for webhook in webhooks
    ]


def get_webhook(api: Api, base_id: str, webhook_id: str) -> dict:
    """Get details of a specific webhook.

    Args:
        api: The Airtable API instance.
        base_id: The base ID the webhook belongs to.
        webhook_id: The webhook ID to retrieve.

    Returns:
        Dictionary with full webhook details including specification,
        cursor position, and expiration time.

    Raises:
        KeyError: If the webhook is not found.
    """
    base = api.base(base_id)
    webhook = base.webhook(webhook_id)

    # Build specification dict from WebhookSpecification model
    spec = webhook.specification
    spec_dict = {
        "options": {
            "filters": {
                "dataTypes": spec.options.filters.data_types,
            }
        }
    }

    # Add optional filter fields if present
    filters = spec.options.filters
    if filters.record_change_scope:
        spec_dict["options"]["filters"]["recordChangeScope"] = (
            filters.record_change_scope
        )
    if filters.change_types:
        spec_dict["options"]["filters"]["changeTypes"] = filters.change_types
    if filters.from_sources:
        spec_dict["options"]["filters"]["fromSources"] = filters.from_sources
    if filters.watch_data_in_field_ids:
        spec_dict["options"]["filters"]["watchDataInFieldIds"] = (
            filters.watch_data_in_field_ids
        )
    if filters.watch_schemas_of_field_ids:
        spec_dict["options"]["filters"]["watchSchemasOfFieldIds"] = (
            filters.watch_schemas_of_field_ids
        )
    if filters.source_options:
        source_opts = {}
        if filters.source_options.form_submission:
            source_opts["formSubmission"] = {
                "viewId": filters.source_options.form_submission.view_id
            }
        if filters.source_options.form_page_submission:
            source_opts["formPageSubmission"] = {
                "pageId": filters.source_options.form_page_submission.page_id
            }
        if source_opts:
            spec_dict["options"]["filters"]["sourceOptions"] = source_opts

    # Add includes if present
    if spec.options.includes:
        includes = spec.options.includes
        includes_dict = {}
        if includes.include_cell_values_in_field_ids is not None:
            includes_dict["includeCellValuesInFieldIds"] = (
                includes.include_cell_values_in_field_ids
            )
        if includes.include_previous_cell_values:
            includes_dict["includePreviousCellValues"] = True
        if includes.include_previous_field_definitions:
            includes_dict["includePreviousFieldDefinitions"] = True
        if includes_dict:
            spec_dict["options"]["includes"] = includes_dict

    return {
        "id": webhook.id,
        "notification_url": webhook.notification_url,
        "is_hook_enabled": webhook.is_hook_enabled,
        "are_notifications_enabled": webhook.are_notifications_enabled,
        "cursor_for_next_payload": webhook.cursor_for_next_payload,
        "expiration_time": (
            webhook.expiration_time.isoformat() if webhook.expiration_time else None
        ),
        "last_successful_notification_time": (
            webhook.last_successful_notification_time.isoformat()
            if webhook.last_successful_notification_time
            else None
        ),
        "specification": spec_dict,
    }


def delete_webhook(api: Api, base_id: str, webhook_id: str) -> None:
    """Delete a webhook from a base.

    Args:
        api: The Airtable API instance.
        base_id: The base ID the webhook belongs to.
        webhook_id: The webhook ID to delete.

    Raises:
        KeyError: If the webhook is not found.
    """
    base = api.base(base_id)
    webhook = base.webhook(webhook_id)
    webhook.delete()


def get_webhook_payloads(
    api: Api, base_id: str, webhook_id: str, cursor: int | None = None
) -> dict:
    """Get payloads for a webhook.

    Args:
        api: The Airtable API instance.
        base_id: The base ID the webhook belongs to.
        webhook_id: The webhook ID to get payloads for.
        cursor: Optional cursor to retrieve payloads after.

    Returns:
        Dictionary with payloads list and cursor information.

    Raises:
        KeyError: If the webhook is not found.
    """
    base = api.base(base_id)
    webhook = base.webhook(webhook_id)

    payloads = []
    last_cursor = cursor
    might_have_more = False

    for payload in webhook.payloads(cursor=cursor or 1):
        payload_dict = {
            "cursor": payload.cursor,
            "timestamp": (
                payload.timestamp.isoformat() if payload.timestamp else None
            ),
        }

        # Add action metadata if present
        if payload.action_metadata:
            payload_dict["action_metadata"] = {
                "source": payload.action_metadata.source,
                "source_metadata": payload.action_metadata.source_metadata,
            }

        # Add payloads (changes)
        if payload.payloads:
            payload_dict["changes"] = payload.payloads

        payloads.append(payload_dict)
        last_cursor = payload.cursor
        might_have_more = payload.might_have_more or False

    return {
        "payloads": payloads,
        "cursor": last_cursor,
        "might_have_more": might_have_more,
    }


def create_webhook(api: Api, base_id: str, notify_url: str, spec_json: str) -> dict:
    """Create a webhook on a base.

    Args:
        api: The Airtable API instance.
        base_id: The base ID to create the webhook on.
        notify_url: The URL to receive notifications.
        spec_json: JSON string of webhook specification.

    Returns:
        Dictionary with webhook ID, MAC secret, and expiration time.

    Raises:
        ValueError: If spec_json is invalid.
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for spec: {e}") from e

    if not isinstance(spec, dict):
        raise ValueError("Spec must be a JSON object")

    if "options" not in spec:
        raise ValueError("Spec must contain 'options' key")

    if "filters" not in spec.get("options", {}):
        raise ValueError("Spec options must contain 'filters' key")

    # Create the webhook
    base = api.base(base_id)
    result = base.add_webhook(notify_url, spec)

    return {
        "id": result.id,
        "mac_secret_base64": result.mac_secret_base64,
        "expiration_time": (
            result.expiration_time.isoformat() if result.expiration_time else None
        ),
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Airtable webhook management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list subcommand
    list_parser = subparsers.add_parser("list", help="List all webhooks on a base")
    list_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON array of webhooks",
    )

    # get subcommand
    get_parser = subparsers.add_parser("get", help="Get details of a specific webhook")
    get_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    get_parser.add_argument("--webhook-id", required=True, help="The webhook ID")
    get_parser.add_argument(
        "--json",
        action="store_true",
        help="Output full webhook as JSON",
    )

    # create subcommand
    create_parser = subparsers.add_parser("create", help="Create a webhook")
    create_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    create_parser.add_argument(
        "--url", required=True, help="The notification URL for the webhook"
    )
    create_parser.add_argument(
        "--spec",
        required=True,
        help='JSON object defining webhook specification (e.g., \'{"options": {"filters": {"dataTypes": ["tableData"]}}}\')',
    )
    create_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON with webhook ID, secret, and expiration",
    )

    # delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete a webhook")
    delete_parser.add_argument("--base-id", required=True, help="The Airtable base ID")
    delete_parser.add_argument("--webhook-id", required=True, help="The webhook ID")
    delete_parser.add_argument(
        "--json", action="store_true", help="Output as JSON with deleted webhook ID"
    )

    # payloads subcommand
    payloads_parser = subparsers.add_parser(
        "payloads", help="Get payloads for a webhook"
    )
    payloads_parser.add_argument(
        "--base-id", required=True, help="The Airtable base ID"
    )
    payloads_parser.add_argument("--webhook-id", required=True, help="The webhook ID")
    payloads_parser.add_argument(
        "--cursor",
        type=int,
        help="Cursor to retrieve payloads after (for pagination)",
    )
    payloads_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON array of payloads",
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

    if args.command == "list":
        try:
            webhooks = list_webhooks(api, args.base_id)
            if args.json:
                print(json.dumps(webhooks, indent=2))
            else:
                if not webhooks:
                    print("No webhooks found.")
                else:
                    for webhook in webhooks:
                        print(f"Webhook ID: {webhook['id']}")
                        print(f"  Notification URL: {webhook['notification_url']}")
                        print(f"  Expiration Time: {webhook['expiration_time']}")
                        print(f"  Is Active: {webhook['is_active']}")
                        print()
            return 0
        except Exception as e:
            print(f"Error listing webhooks: {e}", file=sys.stderr)
            return 1

    elif args.command == "get":
        try:
            webhook = get_webhook(api, args.base_id, args.webhook_id)
            if args.json:
                print(json.dumps(webhook, indent=2))
            else:
                print(f"Webhook ID: {webhook['id']}")
                print(f"Notification URL: {webhook['notification_url']}")
                print(f"Is Hook Enabled: {webhook['is_hook_enabled']}")
                print(
                    f"Are Notifications Enabled: {webhook['are_notifications_enabled']}"
                )
                print()
                print("Cursor & Expiration:")
                print(
                    f"  Cursor for Next Payload: {webhook['cursor_for_next_payload']}"
                )
                print(f"  Expiration Time: {webhook['expiration_time']}")
                if webhook["last_successful_notification_time"]:
                    print(
                        f"  Last Successful Notification: "
                        f"{webhook['last_successful_notification_time']}"
                    )
                print()
                print("Specification:")
                spec = webhook["specification"]
                filters = spec["options"]["filters"]
                print(f"  Data Types: {', '.join(filters['dataTypes'])}")
                if filters.get("recordChangeScope"):
                    print(f"  Record Change Scope: {filters['recordChangeScope']}")
                if filters.get("changeTypes"):
                    print(f"  Change Types: {', '.join(filters['changeTypes'])}")
                if filters.get("fromSources"):
                    print(f"  From Sources: {', '.join(filters['fromSources'])}")
                if filters.get("watchDataInFieldIds"):
                    print(
                        f"  Watch Data In Fields: "
                        f"{', '.join(filters['watchDataInFieldIds'])}"
                    )
                if filters.get("watchSchemasOfFieldIds"):
                    print(
                        f"  Watch Schemas Of Fields: "
                        f"{', '.join(filters['watchSchemasOfFieldIds'])}"
                    )
                if spec["options"].get("includes"):
                    includes = spec["options"]["includes"]
                    print("  Includes:")
                    if includes.get("includeCellValuesInFieldIds"):
                        print(
                            f"    Cell Values In Fields: "
                            f"{includes['includeCellValuesInFieldIds']}"
                        )
                    if includes.get("includePreviousCellValues"):
                        print("    Previous Cell Values: Yes")
                    if includes.get("includePreviousFieldDefinitions"):
                        print("    Previous Field Definitions: Yes")
            return 0
        except KeyError:
            print(f"Error: Webhook '{args.webhook_id}' not found", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error getting webhook: {e}", file=sys.stderr)
            return 1

    elif args.command == "create":
        try:
            result = create_webhook(api, args.base_id, args.url, args.spec)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Created webhook: {result['id']}")
                print(f"Expiration: {result['expiration_time']}")
                print(
                    f"\nSave this secret — it cannot be retrieved again!\n"
                    f"MAC Secret (base64): {result['mac_secret_base64']}",
                    file=sys.stderr,
                )
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error creating webhook: {e}", file=sys.stderr)
            return 1

    elif args.command == "delete":
        try:
            delete_webhook(api, args.base_id, args.webhook_id)
            if args.json:
                print(json.dumps({"id": args.webhook_id, "deleted": True}, indent=2))
            else:
                print(f"Deleted webhook: {args.webhook_id}")
            return 0
        except KeyError:
            print(f"Error: Webhook '{args.webhook_id}' not found", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error deleting webhook: {e}", file=sys.stderr)
            return 1

    elif args.command == "payloads":
        try:
            result = get_webhook_payloads(
                api, args.base_id, args.webhook_id, args.cursor
            )
            if args.json:
                print(json.dumps(result["payloads"], indent=2))
            else:
                payloads = result["payloads"]
                if not payloads:
                    print("No payloads found.")
                else:
                    for payload in payloads:
                        print(f"Cursor: {payload['cursor']}")
                        print(f"  Timestamp: {payload['timestamp']}")
                        if payload.get("action_metadata"):
                            meta = payload["action_metadata"]
                            print(f"  Source: {meta['source']}")
                            if meta.get("source_metadata"):
                                print(f"  Source Metadata: {meta['source_metadata']}")
                        if payload.get("changes"):
                            print(f"  Changes: {len(payload['changes'])} item(s)")
                            for change in payload["changes"]:
                                print(f"    - {change}")
                        print()
                    print(f"Last Cursor: {result['cursor']}")
                    if result["might_have_more"]:
                        print("(More payloads may be available)")
            return 0
        except KeyError:
            print(f"Error: Webhook '{args.webhook_id}' not found", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error getting payloads: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
