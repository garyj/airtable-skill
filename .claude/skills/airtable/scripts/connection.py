#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyairtable>=3.3.0",
# ]
# ///
"""
Airtable connection utility script.

Verify connection and list accessible bases.

Usage:
    uv run connection.py test
    uv run connection.py bases
    uv run connection.py bases --json
"""

import argparse
import json
import os
import sys

from pyairtable import Api


def get_api_token() -> str | None:
    """Get the Airtable API token from environment."""
    return os.environ.get("AIRTABLE_API_TOKEN")


def test_connection(api: Api) -> bool:
    """Test the Airtable connection by listing bases."""
    try:
        # Attempt to list bases to verify the token works
        api.bases()
        return True
    except Exception:
        return False


def list_bases(api: Api) -> list[dict]:
    """List all accessible bases with IDs and names."""
    bases = api.bases()
    return [{"id": base.id, "name": base.name} for base in bases]


def format_table(bases: list[dict]) -> str:
    """Format bases as a table with columns: Base ID, Name."""
    if not bases:
        return "No bases found."

    # Calculate column widths
    id_width = max(len("Base ID"), max(len(b["id"]) for b in bases))
    name_width = max(len("Name"), max(len(b["name"]) for b in bases))

    # Build table
    lines = []
    header = f"{'Base ID':<{id_width}}  {'Name':<{name_width}}"
    separator = f"{'-' * id_width}  {'-' * name_width}"
    lines.append(header)
    lines.append(separator)

    for base in bases:
        lines.append(f"{base['id']:<{id_width}}  {base['name']:<{name_width}}")

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Airtable connection utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # test subcommand
    subparsers.add_parser("test", help="Test Airtable connection")

    # bases subcommand
    bases_parser = subparsers.add_parser("bases", help="List accessible bases")
    bases_parser.add_argument(
        "--json", action="store_true", help="Output as JSON array"
    )

    args = parser.parse_args()

    # Check for API token
    token = get_api_token()
    if not token:
        print("Error: AIRTABLE_API_TOKEN environment variable is not set.", file=sys.stderr)
        print("Set it with: export AIRTABLE_API_TOKEN=your_token", file=sys.stderr)
        return 1

    api = Api(token)

    if args.command == "test":
        if test_connection(api):
            print("Connection successful! Your Airtable token is valid.")
            return 0
        else:
            print("Connection failed. Please check your token.", file=sys.stderr)
            return 1

    elif args.command == "bases":
        try:
            bases = list_bases(api)
            if args.json:
                print(json.dumps(bases, indent=2))
            else:
                print(format_table(bases))
            return 0
        except Exception as e:
            print(f"Error listing bases: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
