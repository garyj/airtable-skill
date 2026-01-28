"""Tests for the schema management script."""

import json
import os
import uuid

import pytest


class TestSchemaScript:
    """Tests for scripts/schema.py."""

    def test_script_exists(self, scripts_dir) -> None:
        """Verify the schema script exists."""
        script_path = scripts_dir / "schema.py"
        assert script_path.exists(), "scripts/schema.py should exist"

    def test_script_has_pep723_metadata(self, scripts_dir) -> None:
        """Verify script has PEP 723 inline metadata."""
        script_path = scripts_dir / "schema.py"
        content = script_path.read_text()
        assert "# /// script" in content, "Script should have PEP 723 header"
        assert "# dependencies = [" in content, "Script should declare dependencies"
        assert "pyairtable" in content, "Script should depend on pyairtable"
        assert "# ///" in content, "Script should have PEP 723 closing marker"

    def test_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing."""
        result = run_script(
            "schema.py",
            ["tables", "list", "--base-id", "appXXXXX"],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_requires_base_id_for_list(self, run_script) -> None:
        """Verify --base-id is required for tables list."""
        result = run_script("schema.py", ["tables", "list"])

        assert result.returncode != 0
        assert "--base-id" in result.stderr

    def test_requires_base_id_and_table_for_describe(self, run_script) -> None:
        """Verify --base-id and --table are required for tables describe."""
        result = run_script("schema.py", ["tables", "describe"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert "--base-id" in result.stderr or "--table" in result.stderr

    def test_requires_base_id_name_fields_for_create(self, run_script) -> None:
        """Verify --base-id, --name, and --fields are required for tables create."""
        result = run_script("schema.py", ["tables", "create"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert "--base-id" in result.stderr or "--name" in result.stderr or "--fields" in result.stderr

    def test_create_with_invalid_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --fields has invalid JSON."""
        result = run_script(
            "schema.py",
            [
                "tables",
                "create",
                "--base-id",
                "appXXXXX",
                "--name",
                "TestTable",
                "--fields",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "invalid json" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_create_with_unsupported_field_type_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --fields has unsupported type."""
        result = run_script(
            "schema.py",
            [
                "tables",
                "create",
                "--base-id",
                "appXXXXX",
                "--name",
                "TestTable",
                "--fields",
                '[{"name": "Title", "type": "multilineText"}]',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "unsupported" in result.stderr.lower()

    def test_create_with_empty_fields_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --fields is empty array."""
        result = run_script(
            "schema.py",
            [
                "tables",
                "create",
                "--base-id",
                "appXXXXX",
                "--name",
                "TestTable",
                "--fields",
                "[]",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "at least one field" in result.stderr.lower() or "error" in result.stderr.lower()


class TestSchemaFunctions:
    """Unit tests for schema module functions."""

    def test_format_tables_table_empty(self, scripts_dir) -> None:
        """Test table formatting with empty list."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import format_tables_table

        result = format_tables_table([])
        assert result == "No tables found."

    def test_format_tables_table_with_data(self, scripts_dir) -> None:
        """Test table formatting with data."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import format_tables_table

        tables = [
            {"id": "tblABC123", "name": "Contacts", "field_count": 5},
            {"id": "tblDEF456", "name": "Projects", "field_count": 10},
        ]
        result = format_tables_table(tables)

        assert "Table ID" in result
        assert "Table Name" in result
        assert "Field Count" in result
        assert "tblABC123" in result
        assert "Contacts" in result
        assert "5" in result
        assert "tblDEF456" in result
        assert "Projects" in result
        assert "10" in result

    def test_format_fields_table_with_data(self, scripts_dir) -> None:
        """Test fields formatting with data."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import format_fields_table

        table_info = {
            "id": "tblABC123",
            "name": "Contacts",
            "fields": [
                {"id": "fldXYZ789", "name": "Name", "type": "singleLineText"},
                {"id": "fldQRS456", "name": "Email", "type": "email"},
            ],
        }
        result = format_fields_table(table_info)

        assert "Contacts" in result
        assert "tblABC123" in result
        assert "Field Name" in result
        assert "Field Type" in result
        assert "Field ID" in result
        assert "Name" in result
        assert "singleLineText" in result
        assert "fldXYZ789" in result
        assert "Email" in result
        assert "email" in result
        assert "fldQRS456" in result

    def test_validate_field_definition_valid(self, scripts_dir) -> None:
        """Test field validation with valid fields."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition

        valid_fields = [
            {"name": "Title", "type": "singleLineText"},
            {"name": "Count", "type": "number"},
            {"name": "Status", "type": "singleSelect"},
            {"name": "Active", "type": "checkbox"},
            {"name": "DueDate", "type": "date"},
            {"name": "CreatedAt", "type": "dateTime"},
            {"name": "Email", "type": "email"},
            {"name": "Website", "type": "url"},
        ]

        for field in valid_fields:
            result = validate_field_definition(field)
            assert result is None, f"Field {field} should be valid"

    def test_validate_field_definition_missing_name(self, scripts_dir) -> None:
        """Test field validation with missing name."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition

        result = validate_field_definition({"type": "singleLineText"})
        assert result is not None
        assert "name" in result.lower()

    def test_validate_field_definition_missing_type(self, scripts_dir) -> None:
        """Test field validation with missing type."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition

        result = validate_field_definition({"name": "Title"})
        assert result is not None
        assert "type" in result.lower()

    def test_validate_field_definition_unsupported_type(self, scripts_dir) -> None:
        """Test field validation with unsupported type."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition

        result = validate_field_definition({"name": "Title", "type": "multilineText"})
        assert result is not None
        assert "unsupported" in result.lower()
        assert "multilineText" in result

    def test_supported_field_types(self, scripts_dir) -> None:
        """Test that all required field types are supported."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import TABLE_CREATION_FIELD_TYPES

        required_types = {
            "singleLineText",
            "number",
            "singleSelect",
            "checkbox",
            "date",
            "dateTime",
            "email",
            "url",
        }
        assert required_types == TABLE_CREATION_FIELD_TYPES


@pytest.mark.integration
class TestSchemaIntegration:
    """Integration tests that require a real Airtable token and test base."""

    @pytest.fixture
    def has_token(self) -> bool:
        """Check if we have a token for integration tests."""
        return bool(os.environ.get("AIRTABLE_API_TOKEN"))

    @pytest.fixture
    def test_base_id(self) -> str | None:
        """Get the test base ID."""
        return os.environ.get("AIRTABLE_TEST_BASE_ID")

    @pytest.fixture
    def api(self, has_token: bool):
        """Create an API instance for integration tests."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")

        from pyairtable import Api

        return Api(os.environ["AIRTABLE_API_TOKEN"])

    def test_tables_list_with_real_token(self, run_script, has_token: bool, test_base_id: str | None) -> None:
        """Test tables listing with real token."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set, skipping integration test")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        result = run_script("schema.py", ["tables", "list", "--base-id", test_base_id])

        assert result.returncode == 0
        # Should have table headers or empty message
        assert "Table ID" in result.stdout or "No tables found" in result.stdout

    def test_tables_list_json_with_real_token(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test tables listing with JSON output."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set, skipping integration test")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        result = run_script(
            "schema.py",
            ["tables", "list", "--base-id", test_base_id, "--json"],
        )

        assert result.returncode == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        # Each item should have id, name, and field_count
        for item in data:
            assert "id" in item
            assert "name" in item
            assert "field_count" in item

    def test_create_list_describe_cleanup_table(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test full workflow: create table, list it, describe it, clean up."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestTable_{uuid.uuid4().hex[:8]}"

        try:
            # Create a test table using pyairtable directly
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Status", "type": "singleSelect", "options": {
                        "choices": [{"name": "Active"}, {"name": "Inactive"}]
                    }},
                    {"name": "Count", "type": "number", "options": {"precision": 0}},
                ],
                description="Test table for integration testing",
            )

            # List tables and verify our table appears
            result = run_script(
                "schema.py",
                ["tables", "list", "--base-id", test_base_id, "--json"],
            )

            assert result.returncode == 0
            tables = json.loads(result.stdout)
            table_names = [t["name"] for t in tables]
            assert table_name in table_names, f"Created table '{table_name}' should appear in list"

            # Find our table in the list
            our_table = next(t for t in tables if t["name"] == table_name)
            # Should have 3 fields we created, but Airtable may add a primary field
            assert our_table["field_count"] >= 3

            # Describe the table
            result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table_name, "--json"],
            )

            assert result.returncode == 0
            table_info = json.loads(result.stdout)
            assert table_info["name"] == table_name
            assert "fields" in table_info

            # Check fields
            field_names = [f["name"] for f in table_info["fields"]]
            assert "Name" in field_names
            assert "Status" in field_names
            assert "Count" in field_names

            # Check field details
            for field in table_info["fields"]:
                assert "id" in field
                assert "name" in field
                assert "type" in field

        finally:
            # Clean up: delete the test table
            try:
                base = api.base(test_base_id)
                # Get table ID from the created table
                table = base.table(table_name)
                table_schema = table.schema()
                # Delete using the Airtable API
                api.request(
                    method="DELETE",
                    url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_schema.id}",
                )
            except Exception:
                # Best effort cleanup
                pass

    def test_tables_describe_with_real_token(
        self, run_script, has_token: bool, test_base_id: str | None, api
    ) -> None:
        """Test tables describe command."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set, skipping integration test")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # First get a table name from the list
        result = run_script(
            "schema.py",
            ["tables", "list", "--base-id", test_base_id, "--json"],
        )

        if result.returncode != 0:
            pytest.skip("Could not list tables")

        tables = json.loads(result.stdout)
        if not tables:
            pytest.skip("No tables in test base to describe")

        table_name = tables[0]["name"]

        # Now describe that table
        result = run_script(
            "schema.py",
            ["tables", "describe", "--base-id", test_base_id, "--table", table_name],
        )

        assert result.returncode == 0
        assert table_name in result.stdout
        assert "Field Name" in result.stdout
        assert "Field Type" in result.stdout
        assert "Field ID" in result.stdout

    def test_tables_describe_json_with_real_token(
        self, run_script, has_token: bool, test_base_id: str | None, api
    ) -> None:
        """Test tables describe command with JSON output."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set, skipping integration test")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # First get a table name from the list
        result = run_script(
            "schema.py",
            ["tables", "list", "--base-id", test_base_id, "--json"],
        )

        if result.returncode != 0:
            pytest.skip("Could not list tables")

        tables = json.loads(result.stdout)
        if not tables:
            pytest.skip("No tables in test base to describe")

        table_name = tables[0]["name"]

        # Now describe that table with JSON output
        result = run_script(
            "schema.py",
            ["tables", "describe", "--base-id", test_base_id, "--table", table_name, "--json"],
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "id" in data
        assert "name" in data
        assert data["name"] == table_name
        assert "fields" in data
        assert isinstance(data["fields"], list)
        for field in data["fields"]:
            assert "id" in field
            assert "name" in field
            assert "type" in field

    def test_tables_create_with_multiple_field_types(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a table with all supported field types via CLI."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestCreate_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        # Define fields with all supported types
        fields = [
            {"name": "Title", "type": "singleLineText"},
            {"name": "Count", "type": "number", "options": {"precision": 0}},
            {
                "name": "Status",
                "type": "singleSelect",
                "options": {"choices": [{"name": "Active"}, {"name": "Inactive"}]},
            },
            {"name": "IsComplete", "type": "checkbox", "options": {"color": "greenBright", "icon": "check"}},
            {"name": "DueDate", "type": "date", "options": {"dateFormat": {"name": "local"}}},
            {"name": "CreatedAt", "type": "dateTime", "options": {"dateFormat": {"name": "local"}, "timeFormat": {"name": "24hour"}, "timeZone": "utc"}},
            {"name": "ContactEmail", "type": "email"},
            {"name": "Website", "type": "url"},
        ]

        try:
            # Create table using CLI with --json flag
            result = run_script(
                "schema.py",
                [
                    "tables",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--name",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Parse JSON output
            create_result = json.loads(result.stdout)
            assert "id" in create_result
            assert "name" in create_result
            assert "fields" in create_result
            assert create_result["name"] == table_name

            created_table_id = create_result["id"]

            # Verify all fields have IDs
            for field in create_result["fields"]:
                assert "id" in field, f"Field {field.get('name')} missing ID"
                assert "name" in field
                assert "type" in field

            # Verify field names match what we requested
            created_field_names = {f["name"] for f in create_result["fields"]}
            requested_field_names = {f["name"] for f in fields}
            assert requested_field_names.issubset(created_field_names), (
                f"Missing fields: {requested_field_names - created_field_names}"
            )

            # Verify schema using describe command
            result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table_name, "--json"],
            )

            assert result.returncode == 0
            table_info = json.loads(result.stdout)
            assert table_info["name"] == table_name

            # Verify field types match
            field_types = {f["name"]: f["type"] for f in table_info["fields"]}
            for field in fields:
                assert field["name"] in field_types, f"Field {field['name']} not found"
                assert field_types[field["name"]] == field["type"], (
                    f"Field {field['name']} type mismatch: "
                    f"expected {field['type']}, got {field_types[field['name']]}"
                )

        finally:
            # Clean up: delete the test table
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    # Best effort cleanup
                    pass

    def test_tables_create_human_readable_output(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a table without --json flag shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestHuman_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        fields = [{"name": "Title", "type": "singleLineText"}]

        try:
            # Create table using CLI without --json flag
            result = run_script(
                "schema.py",
                [
                    "tables",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--name",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                ],
            )

            assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Verify human-readable output
            assert f"Created table '{table_name}'" in result.stdout
            assert "ID:" in result.stdout
            assert "Fields created:" in result.stdout

            # Get table ID for cleanup using JSON output from list
            list_result = run_script(
                "schema.py",
                ["tables", "list", "--base-id", test_base_id, "--json"],
            )

            if list_result.returncode == 0:
                tables = json.loads(list_result.stdout)
                for table in tables:
                    if table["name"] == table_name:
                        created_table_id = table["id"]
                        break

        finally:
            # Clean up: delete the test table
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    # Best effort cleanup
                    pass


class TestFieldsUpdateCommand:
    """Tests for the fields update command."""

    def test_requires_base_id_table_field_id_for_update(self, run_script) -> None:
        """Verify --base-id, --table, and --field-id are required for fields update."""
        result = run_script("schema.py", ["fields", "update"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert "--base-id" in result.stderr or "--table" in result.stderr or "--field-id" in result.stderr

    def test_fields_update_requires_name_or_description(self, run_script, env_with_test_token) -> None:
        """Verify error when neither --name nor --description is provided."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field-id",
                "fldXXXXX",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "name" in result.stderr.lower() or "description" in result.stderr.lower()


class TestFieldsCreateCommand:
    """Tests for the fields create command."""

    def test_requires_base_id_table_field_for_create(self, run_script) -> None:
        """Verify --base-id, --table, and --field are required for fields create."""
        result = run_script("schema.py", ["fields", "create"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert "--base-id" in result.stderr or "--table" in result.stderr or "--field" in result.stderr

    def test_fields_create_with_invalid_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --field has invalid JSON."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "invalid json" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_fields_create_with_unsupported_type_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --field has unsupported type."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field",
                '{"name": "Test", "type": "unknownType"}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "unsupported" in result.stderr.lower()

    def test_fields_create_missing_name_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --field is missing name."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field",
                '{"type": "singleLineText"}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "name" in result.stderr.lower()

    def test_fields_create_missing_type_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --field is missing type."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field",
                '{"name": "TestField"}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "type" in result.stderr.lower()

    def test_fields_create_multipleRecordLinks_requires_linkedTableId(self, run_script, env_with_test_token) -> None:
        """Verify multipleRecordLinks requires linkedTableId in options."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field",
                '{"name": "Links", "type": "multipleRecordLinks"}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "linkedTableId" in result.stderr


class TestFieldsUpdateValidation:
    """Unit tests for fields update validation."""

    def test_update_field_requires_name_or_description(self, scripts_dir) -> None:
        """Test that update_field raises error without name or description."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from unittest.mock import MagicMock

        from schema import update_field

        mock_api = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            update_field(mock_api, "appXXX", "Table", "fldXXX")

        assert "name" in str(exc_info.value).lower() or "description" in str(exc_info.value).lower()


class TestFieldsCreateValidation:
    """Unit tests for fields create validation functions."""

    def test_validate_create_field_definition_valid_simple(self, scripts_dir) -> None:
        """Test field validation with simple valid fields."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        valid_fields = [
            {"name": "Title", "type": "singleLineText"},
            {"name": "Description", "type": "multilineText"},
            {"name": "Count", "type": "number"},
            {"name": "Phone", "type": "phoneNumber"},
            {"name": "Rating", "type": "rating"},
        ]

        for field in valid_fields:
            result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
            assert result is None, f"Field {field} should be valid"

    def test_validate_create_field_definition_multipleRecordLinks_valid(self, scripts_dir) -> None:
        """Test multipleRecordLinks validation with linkedTableId."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "LinkedRecords",
            "type": "multipleRecordLinks",
            "options": {"linkedTableId": "tblXXXXXXXX"},
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_multipleRecordLinks_with_linkedTableName(self, scripts_dir) -> None:
        """Test multipleRecordLinks validation with linkedTableName."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "LinkedRecords",
            "type": "multipleRecordLinks",
            "options": {"linkedTableName": "OtherTable"},
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_multipleRecordLinks_with_prefersSingleRecordLink(self, scripts_dir) -> None:
        """Test multipleRecordLinks validation with prefersSingleRecordLink option."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "LinkedRecord",
            "type": "multipleRecordLinks",
            "options": {
                "linkedTableId": "tblXXXXXXXX",
                "prefersSingleRecordLink": True,
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_multipleRecordLinks_missing_options(self, scripts_dir) -> None:
        """Test multipleRecordLinks validation fails without linkedTableId or linkedTableName."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {"name": "LinkedRecords", "type": "multipleRecordLinks"}
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "linkedTableId" in result or "linkedTableName" in result

    def test_validate_create_field_definition_multipleRecordLinks_empty_options(self, scripts_dir) -> None:
        """Test multipleRecordLinks validation fails with empty options."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {"name": "LinkedRecords", "type": "multipleRecordLinks", "options": {}}
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "linkedTableId" in result or "linkedTableName" in result

    def test_supported_create_field_types(self, scripts_dir) -> None:
        """Test that multipleRecordLinks is in supported types."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import FIELD_CREATION_FIELD_TYPES

        assert "multipleRecordLinks" in FIELD_CREATION_FIELD_TYPES
        assert "singleLineText" in FIELD_CREATION_FIELD_TYPES
        assert "multilineText" in FIELD_CREATION_FIELD_TYPES
        assert "multipleAttachments" in FIELD_CREATION_FIELD_TYPES


@pytest.mark.integration
class TestFieldsCreateIntegration:
    """Integration tests for fields create command."""

    @pytest.fixture
    def has_token(self) -> bool:
        """Check if we have a token for integration tests."""
        return bool(os.environ.get("AIRTABLE_API_TOKEN"))

    @pytest.fixture
    def test_base_id(self) -> str | None:
        """Get the test base ID."""
        return os.environ.get("AIRTABLE_TEST_BASE_ID")

    @pytest.fixture
    def api(self, has_token: bool):
        """Create an API instance for integration tests."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")

        from pyairtable import Api

        return Api(os.environ["AIRTABLE_API_TOKEN"])

    def test_fields_create_add_field_to_table(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a field on an existing table."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestFieldsCreate_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # First create a table with a single field
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            created_table_id = new_table.id

            # Now add a field using the CLI
            field_json = json.dumps({"name": "Email", "type": "email"})
            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--field",
                    field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "Email"
            assert field_result["type"] == "email"

            # Verify field exists using describe
            describe_result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table_name, "--json"],
            )

            assert describe_result.returncode == 0
            table_info = json.loads(describe_result.stdout)
            field_names = [f["name"] for f in table_info["fields"]]
            assert "Email" in field_names

        finally:
            # Clean up
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_fields_create_multipleRecordLinks(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a multipleRecordLinks field linking two tables."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLinks1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLinks2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "LinkedRecords"
            assert field_result["type"] == "multipleRecordLinks"

            # Verify field exists
            describe_result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table1_name, "--json"],
            )

            assert describe_result.returncode == 0
            table_info = json.loads(describe_result.stdout)
            field_names = [f["name"] for f in table_info["fields"]]
            assert "LinkedRecords" in field_names

            # Find the field and verify its type
            link_field = next(f for f in table_info["fields"] if f["name"] == "LinkedRecords")
            assert link_field["type"] == "multipleRecordLinks"

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    def test_fields_create_multipleRecordLinks_with_linkedTableName(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a multipleRecordLinks field using linkedTableName instead of linkedTableId."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLinksName1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLinksName2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field using linkedTableName
            field_json = json.dumps({
                "name": "LinkedByName",
                "type": "multipleRecordLinks",
                "options": {"linkedTableName": table2_name},
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "LinkedByName"
            assert field_result["type"] == "multipleRecordLinks"

            # Verify options contain linkedTableId (resolved from name)
            assert "options" in field_result
            assert "linkedTableId" in field_result["options"]
            assert field_result["options"]["linkedTableId"] == table2_id

            # Verify field exists
            describe_result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table1_name, "--json"],
            )

            assert describe_result.returncode == 0
            table_info = json.loads(describe_result.stdout)
            field_names = [f["name"] for f in table_info["fields"]]
            assert "LinkedByName" in field_names

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    @pytest.mark.xfail(reason="Airtable API removed prefersSingleRecordLink option")
    def test_fields_create_multipleRecordLinks_with_prefersSingleRecordLink(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a multipleRecordLinks field with prefersSingleRecordLink option."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLinksSingle1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLinksSingle2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field with prefersSingleRecordLink
            field_json = json.dumps({
                "name": "SingleLink",
                "type": "multipleRecordLinks",
                "options": {
                    "linkedTableId": table2_id,
                    "prefersSingleRecordLink": True,
                },
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "SingleLink"
            assert field_result["type"] == "multipleRecordLinks"

            # Verify options contain prefersSingleRecordLink
            assert "options" in field_result
            assert "linkedTableId" in field_result["options"]
            assert field_result["options"]["linkedTableId"] == table2_id
            assert field_result["options"].get("prefersSingleRecordLink") is True

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    def test_fields_create_multipleRecordLinks_returns_link_configuration(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test that creating a multipleRecordLinks field returns link configuration."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLinksConfig1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLinksConfig2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field
            field_json = json.dumps({
                "name": "ConfiguredLink",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"

            # Parse JSON output and verify link configuration is returned
            field_result = json.loads(result.stdout)
            assert "id" in field_result, "Response should include field ID"
            assert "options" in field_result, "Response should include options for link fields"
            assert "linkedTableId" in field_result["options"], "Response should include linkedTableId"
            assert field_result["options"]["linkedTableId"] == table2_id

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    def test_fields_create_multipleRecordLinks_verifies_link_works(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test that a created link field actually works by creating linked records."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLinksWork1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLinksWork2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed to create link field: {result.stderr}"

            # Create a record in table2 that we'll link to
            table2_obj = base.table(table2_id)
            record2 = table2_obj.create({"Title": "Linked Record"})
            record2_id = record2["id"]

            # Create a record in table1 with a link to the table2 record
            table1_obj = base.table(table1_id)
            record1 = table1_obj.create({
                "Name": "Parent Record",
                "LinkedRecords": [record2_id],
            })

            # Verify the link was created by reading the record
            fetched_record = table1_obj.get(record1["id"])
            assert "LinkedRecords" in fetched_record["fields"]
            assert record2_id in fetched_record["fields"]["LinkedRecords"]

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    def test_fields_update_name(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test updating a field's name."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestFieldsUpdate_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a table with a field
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[{"name": "OriginalName", "type": "singleLineText"}],
            )
            created_table_id = new_table.id

            # Get the field ID
            table = base.table(table_name)
            table_schema = table.schema()
            field = next(f for f in table_schema.fields if f.name == "OriginalName")
            field_id = field.id

            # Update the field name using CLI
            result = run_script(
                "schema.py",
                [
                    "fields",
                    "update",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--field-id",
                    field_id,
                    "--name",
                    "UpdatedName",
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"

            # Parse JSON output
            update_result = json.loads(result.stdout)
            assert update_result["id"] == field_id
            assert update_result["name"] == "UpdatedName"
            assert update_result["type"] == "singleLineText"

            # Verify the change using describe
            describe_result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table_name, "--json"],
            )

            assert describe_result.returncode == 0
            table_info = json.loads(describe_result.stdout)
            field_names = [f["name"] for f in table_info["fields"]]
            assert "UpdatedName" in field_names
            assert "OriginalName" not in field_names

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_fields_create_human_readable_output(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test fields create without --json flag shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestFieldsHuman_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            created_table_id = new_table.id

            field_json = json.dumps({"name": "Notes", "type": "multilineText"})
            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--field",
                    field_json,
                ],
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"
            assert "Created field 'Notes'" in result.stdout
            assert "ID:" in result.stdout
            assert "Type: multilineText" in result.stdout

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass


class TestTablesDeleteCommand:
    """Tests for the tables delete command."""

    def test_requires_base_id_and_table_for_delete(self, run_script) -> None:
        """Verify --base-id and --table are required for tables delete."""
        result = run_script("schema.py", ["tables", "delete"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert "--base-id" in result.stderr or "--table" in result.stderr


@pytest.mark.integration
class TestTablesDeleteIntegration:
    """Integration tests for tables delete command."""

    @pytest.fixture
    def has_token(self) -> bool:
        """Check if we have a token for integration tests."""
        return bool(os.environ.get("AIRTABLE_API_TOKEN"))

    @pytest.fixture
    def test_base_id(self) -> str | None:
        """Get the test base ID."""
        return os.environ.get("AIRTABLE_TEST_BASE_ID")

    @pytest.fixture
    def api(self, has_token: bool):
        """Create an API instance for integration tests."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")

        from pyairtable import Api

        return Api(os.environ["AIRTABLE_API_TOKEN"])

    @pytest.mark.xfail(reason="API token lacks schema.bases:write scope for table deletion")
    def test_tables_delete_creates_and_deletes_table(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a table, deleting it, and verifying it's gone."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestDelete_{uuid.uuid4().hex[:8]}"

        # Create a table first
        base = api.base(test_base_id)
        new_table = base.create_table(
            name=table_name,
            fields=[{"name": "Name", "type": "singleLineText"}],
        )
        created_table_id = new_table.id

        # Verify table exists
        list_result = run_script(
            "schema.py",
            ["tables", "list", "--base-id", test_base_id, "--json"],
        )
        assert list_result.returncode == 0
        tables_before = json.loads(list_result.stdout)
        table_names_before = [t["name"] for t in tables_before]
        assert table_name in table_names_before, "Table should exist before deletion"

        # Delete the table using CLI
        delete_result = run_script(
            "schema.py",
            ["tables", "delete", "--base-id", test_base_id, "--table", table_name],
        )

        assert delete_result.returncode == 0, f"Delete failed: {delete_result.stderr}"
        assert f"Deleted table '{table_name}'" in delete_result.stdout

        # Verify table is gone
        list_result_after = run_script(
            "schema.py",
            ["tables", "list", "--base-id", test_base_id, "--json"],
        )
        assert list_result_after.returncode == 0
        tables_after = json.loads(list_result_after.stdout)
        table_names_after = [t["name"] for t in tables_after]
        assert table_name not in table_names_after, "Table should be gone after deletion"


class TestLookupFieldCommand:
    """Tests for creating lookup fields via the fields create command."""

    def test_fields_create_multipleLookupValues_requires_recordLinkFieldId(self, run_script, env_with_test_token) -> None:
        """Verify multipleLookupValues requires recordLinkFieldId in options."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field",
                '{"name": "Lookup", "type": "multipleLookupValues"}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "recordLinkFieldId" in result.stderr or "recordLinkFieldName" in result.stderr

    def test_fields_create_multipleLookupValues_requires_fieldIdInLinkedTable(self, run_script, env_with_test_token) -> None:
        """Verify multipleLookupValues requires fieldIdInLinkedTable in options."""
        result = run_script(
            "schema.py",
            [
                "fields",
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--field",
                '{"name": "Lookup", "type": "multipleLookupValues", "options": {"recordLinkFieldId": "fldXXXXX"}}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "fieldIdInLinkedTable" in result.stderr or "fieldNameInLinkedTable" in result.stderr


class TestLookupFieldValidation:
    """Unit tests for lookup field validation functions."""

    def test_validate_create_field_definition_multipleLookupValues_valid(self, scripts_dir) -> None:
        """Test multipleLookupValues validation with valid options."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "LookupField",
            "type": "multipleLookupValues",
            "options": {
                "recordLinkFieldId": "fldXXXXXXXX",
                "fieldIdInLinkedTable": "fldYYYYYYYY",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_multipleLookupValues_with_field_names(self, scripts_dir) -> None:
        """Test multipleLookupValues validation with field names instead of IDs."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "LookupField",
            "type": "multipleLookupValues",
            "options": {
                "recordLinkFieldName": "LinkedRecords",
                "fieldNameInLinkedTable": "Name",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_multipleLookupValues_missing_recordLinkField(self, scripts_dir) -> None:
        """Test multipleLookupValues validation fails without recordLinkFieldId."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "LookupField",
            "type": "multipleLookupValues",
            "options": {"fieldIdInLinkedTable": "fldYYYYYYYY"},
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "recordLinkFieldId" in result or "recordLinkFieldName" in result

    def test_validate_create_field_definition_multipleLookupValues_missing_fieldInLinkedTable(self, scripts_dir) -> None:
        """Test multipleLookupValues validation fails without fieldIdInLinkedTable."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "LookupField",
            "type": "multipleLookupValues",
            "options": {"recordLinkFieldId": "fldXXXXXXXX"},
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "fieldIdInLinkedTable" in result or "fieldNameInLinkedTable" in result

    def test_validate_create_field_definition_multipleLookupValues_no_options(self, scripts_dir) -> None:
        """Test multipleLookupValues validation fails without options."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {"name": "LookupField", "type": "multipleLookupValues"}
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None

    def test_supported_create_field_types_includes_lookup(self, scripts_dir) -> None:
        """Test that multipleLookupValues is in supported types."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import FIELD_CREATION_FIELD_TYPES

        assert "multipleLookupValues" in FIELD_CREATION_FIELD_TYPES


@pytest.mark.integration
class TestLookupFieldIntegration:
    """Integration tests for lookup field creation."""

    @pytest.fixture
    def has_token(self) -> bool:
        """Check if we have a token for integration tests."""
        return bool(os.environ.get("AIRTABLE_API_TOKEN"))

    @pytest.fixture
    def test_base_id(self) -> str | None:
        """Get the test base ID."""
        return os.environ.get("AIRTABLE_TEST_BASE_ID")

    @pytest.fixture
    def api(self, has_token: bool):
        """Create an API instance for integration tests."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")

        from pyairtable import Api

        return Api(os.environ["AIRTABLE_API_TOKEN"])

    @pytest.mark.xfail(reason="Airtable API does not support creating multipleLookupValues fields")
    def test_fields_create_multipleLookupValues(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a multipleLookupValues lookup field."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLookup1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLookup2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            link_field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            link_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    link_field_json,
                    "--json",
                ],
            )

            assert link_result.returncode == 0, f"Failed to create link field: {link_result.stderr}"
            link_field_data = json.loads(link_result.stdout)
            link_field_id = link_field_data["id"]

            # Get the Title field ID from table2
            table2_obj = base.table(table2_id)
            table2_schema = table2_obj.schema()
            title_field = next(f for f in table2_schema.fields if f.name == "Title")
            title_field_id = title_field.id

            # Create a lookup field that looks up the Title field via the linked records
            lookup_field_json = json.dumps({
                "name": "LookedUpTitle",
                "type": "multipleLookupValues",
                "options": {
                    "recordLinkFieldId": link_field_id,
                    "fieldIdInLinkedTable": title_field_id,
                },
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    lookup_field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed to create lookup field: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "LookedUpTitle"
            assert field_result["type"] == "multipleLookupValues"

            # Verify options in response
            assert "options" in field_result
            assert field_result["options"]["recordLinkFieldId"] == link_field_id
            assert field_result["options"]["fieldIdInLinkedTable"] == title_field_id

            # Verify field exists using describe
            describe_result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table1_name, "--json"],
            )

            assert describe_result.returncode == 0
            table_info = json.loads(describe_result.stdout)
            field_names = [f["name"] for f in table_info["fields"]]
            assert "LookedUpTitle" in field_names

            # Find the lookup field and verify its type
            lookup_field = next(f for f in table_info["fields"] if f["name"] == "LookedUpTitle")
            assert lookup_field["type"] == "multipleLookupValues"

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    @pytest.mark.xfail(reason="Airtable API does not support creating multipleLookupValues fields")
    def test_fields_create_lookup_and_verify_data_appears(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test that a created lookup field actually shows data from linked records."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLookupData1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLookupData2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            link_field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            link_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    link_field_json,
                    "--json",
                ],
            )

            assert link_result.returncode == 0, f"Failed to create link field: {link_result.stderr}"
            link_field_data = json.loads(link_result.stdout)
            link_field_id = link_field_data["id"]

            # Get the Title field ID from table2
            table2_obj = base.table(table2_id)
            table2_schema = table2_obj.schema()
            title_field = next(f for f in table2_schema.fields if f.name == "Title")
            title_field_id = title_field.id

            # Create a lookup field
            lookup_field_json = json.dumps({
                "name": "LookedUpTitle",
                "type": "multipleLookupValues",
                "options": {
                    "recordLinkFieldId": link_field_id,
                    "fieldIdInLinkedTable": title_field_id,
                },
            })

            lookup_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    lookup_field_json,
                    "--json",
                ],
            )

            assert lookup_result.returncode == 0, f"Failed to create lookup field: {lookup_result.stderr}"

            # Create a record in table2
            record2 = table2_obj.create({"Title": "Looked Up Value"})
            record2_id = record2["id"]

            # Create a record in table1 with a link to the table2 record
            table1_obj = base.table(table1_id)
            record1 = table1_obj.create({
                "Name": "Parent Record",
                "LinkedRecords": [record2_id],
            })

            # Verify the lookup field shows the data
            fetched_record = table1_obj.get(record1["id"])
            assert "LookedUpTitle" in fetched_record["fields"]
            assert "Looked Up Value" in fetched_record["fields"]["LookedUpTitle"]

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    @pytest.mark.xfail(reason="Airtable API does not support creating multipleLookupValues fields")
    def test_fields_create_lookup_with_field_names(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a lookup field using field names instead of IDs."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestLookupName1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestLookupName2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[{"name": "Title", "type": "singleLineText"}],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            link_field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            link_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    link_field_json,
                    "--json",
                ],
            )

            assert link_result.returncode == 0, f"Failed to create link field: {link_result.stderr}"
            link_field_data = json.loads(link_result.stdout)
            link_field_id = link_field_data["id"]

            # Get the Title field ID from table2 (for verification later)
            table2_obj = base.table(table2_id)
            table2_schema = table2_obj.schema()
            title_field = next(f for f in table2_schema.fields if f.name == "Title")
            title_field_id = title_field.id

            # Create a lookup field using field NAMES instead of IDs
            lookup_field_json = json.dumps({
                "name": "LookedUpTitle",
                "type": "multipleLookupValues",
                "options": {
                    "recordLinkFieldName": "LinkedRecords",
                    "fieldNameInLinkedTable": "Title",
                },
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    lookup_field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed to create lookup field: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "LookedUpTitle"
            assert field_result["type"] == "multipleLookupValues"

            # Verify options contain resolved IDs (not names)
            assert "options" in field_result
            assert field_result["options"]["recordLinkFieldId"] == link_field_id
            assert field_result["options"]["fieldIdInLinkedTable"] == title_field_id

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass


class TestRollupFieldValidation:
    """Unit tests for rollup field validation functions."""

    def test_validate_create_field_definition_rollup_valid(self, scripts_dir) -> None:
        """Test rollup validation with valid options."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "TotalAmount",
            "type": "rollup",
            "options": {
                "recordLinkFieldId": "fldXXXXXXXX",
                "fieldIdInLinkedTable": "fldYYYYYYYY",
                "aggregationFunction": "SUM",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_rollup_with_field_names(self, scripts_dir) -> None:
        """Test rollup validation with field names instead of IDs."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "TotalAmount",
            "type": "rollup",
            "options": {
                "recordLinkFieldName": "LinkedRecords",
                "fieldNameInLinkedTable": "Amount",
                "aggregationFunction": "COUNT",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_rollup_with_formula(self, scripts_dir) -> None:
        """Test rollup validation with raw formula instead of aggregationFunction."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "TotalAmount",
            "type": "rollup",
            "options": {
                "recordLinkFieldId": "fldXXXXXXXX",
                "fieldIdInLinkedTable": "fldYYYYYYYY",
                "formula": "SUM(values)",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is None

    def test_validate_create_field_definition_rollup_missing_recordLinkField(self, scripts_dir) -> None:
        """Test rollup validation fails without recordLinkFieldId."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "TotalAmount",
            "type": "rollup",
            "options": {
                "fieldIdInLinkedTable": "fldYYYYYYYY",
                "aggregationFunction": "SUM",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "recordLinkFieldId" in result or "recordLinkFieldName" in result

    def test_validate_create_field_definition_rollup_missing_fieldInLinkedTable(self, scripts_dir) -> None:
        """Test rollup validation fails without fieldIdInLinkedTable."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "TotalAmount",
            "type": "rollup",
            "options": {
                "recordLinkFieldId": "fldXXXXXXXX",
                "aggregationFunction": "SUM",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "fieldIdInLinkedTable" in result or "fieldNameInLinkedTable" in result

    def test_validate_create_field_definition_rollup_missing_aggregation(self, scripts_dir) -> None:
        """Test rollup validation fails without aggregation function or formula."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "TotalAmount",
            "type": "rollup",
            "options": {
                "recordLinkFieldId": "fldXXXXXXXX",
                "fieldIdInLinkedTable": "fldYYYYYYYY",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "formula" in result or "aggregationFunction" in result

    def test_validate_create_field_definition_rollup_invalid_aggregation(self, scripts_dir) -> None:
        """Test rollup validation fails with invalid aggregation function."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {
            "name": "TotalAmount",
            "type": "rollup",
            "options": {
                "recordLinkFieldId": "fldXXXXXXXX",
                "fieldIdInLinkedTable": "fldYYYYYYYY",
                "aggregationFunction": "INVALID_FUNC",
            },
        }
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None
        assert "unsupported aggregation function" in result

    def test_validate_create_field_definition_rollup_no_options(self, scripts_dir) -> None:
        """Test rollup validation fails without options."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import validate_field_definition, FIELD_CREATION_FIELD_TYPES

        field = {"name": "TotalAmount", "type": "rollup"}
        result = validate_field_definition(field, allowed_types=FIELD_CREATION_FIELD_TYPES)
        assert result is not None

    def test_supported_create_field_types_includes_rollup(self, scripts_dir) -> None:
        """Test that rollup is in supported types."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import FIELD_CREATION_FIELD_TYPES

        assert "rollup" in FIELD_CREATION_FIELD_TYPES

    def test_supported_rollup_functions(self, scripts_dir) -> None:
        """Test that all expected rollup functions are supported."""
        import sys
        sys.path.insert(0, str(scripts_dir))
        from schema import SUPPORTED_ROLLUP_FUNCTIONS

        expected_functions = {"SUM", "COUNT", "AVERAGE", "MAX", "MIN", "COUNTA"}
        assert expected_functions.issubset(SUPPORTED_ROLLUP_FUNCTIONS)


@pytest.mark.integration
class TestRollupFieldIntegration:
    """Integration tests for rollup field creation."""

    @pytest.fixture
    def has_token(self) -> bool:
        """Check if we have a token for integration tests."""
        return bool(os.environ.get("AIRTABLE_API_TOKEN"))

    @pytest.fixture
    def test_base_id(self) -> str | None:
        """Get the test base ID."""
        return os.environ.get("AIRTABLE_TEST_BASE_ID")

    @pytest.fixture
    def api(self, has_token: bool):
        """Create an API instance for integration tests."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")

        from pyairtable import Api

        return Api(os.environ["AIRTABLE_API_TOKEN"])

    @pytest.mark.xfail(reason="Airtable API does not support creating rollup fields")
    def test_fields_create_rollup_sum(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a rollup field with SUM aggregation."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestRollup1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestRollup2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables - table2 has a numeric field to aggregate
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[
                    {"name": "Title", "type": "singleLineText"},
                    {"name": "Amount", "type": "number", "options": {"precision": 0}},
                ],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            link_field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            link_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    link_field_json,
                    "--json",
                ],
            )

            assert link_result.returncode == 0, f"Failed to create link field: {link_result.stderr}"
            link_field_data = json.loads(link_result.stdout)
            link_field_id = link_field_data["id"]

            # Get the Amount field ID from table2
            table2_obj = base.table(table2_id)
            table2_schema = table2_obj.schema()
            amount_field = next(f for f in table2_schema.fields if f.name == "Amount")
            amount_field_id = amount_field.id

            # Create a rollup field that sums the Amount field
            rollup_field_json = json.dumps({
                "name": "TotalAmount",
                "type": "rollup",
                "options": {
                    "recordLinkFieldId": link_field_id,
                    "fieldIdInLinkedTable": amount_field_id,
                    "aggregationFunction": "SUM",
                },
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    rollup_field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed to create rollup field: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "TotalAmount"
            assert field_result["type"] == "rollup"

            # Verify options in response
            assert "options" in field_result
            assert field_result["options"]["recordLinkFieldId"] == link_field_id
            assert field_result["options"]["fieldIdInLinkedTable"] == amount_field_id
            assert "SUM" in field_result["options"]["formula"]

            # Verify field exists using describe
            describe_result = run_script(
                "schema.py",
                ["tables", "describe", "--base-id", test_base_id, "--table", table1_name, "--json"],
            )

            assert describe_result.returncode == 0
            table_info = json.loads(describe_result.stdout)
            field_names = [f["name"] for f in table_info["fields"]]
            assert "TotalAmount" in field_names

            # Find the rollup field and verify its type
            rollup_field = next(f for f in table_info["fields"] if f["name"] == "TotalAmount")
            assert rollup_field["type"] == "rollup"

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    @pytest.mark.xfail(reason="Airtable API does not support creating rollup fields")
    def test_fields_create_rollup_and_verify_calculation(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test that a created rollup field actually calculates aggregated data."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestRollupData1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestRollupData2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[
                    {"name": "Title", "type": "singleLineText"},
                    {"name": "Amount", "type": "number", "options": {"precision": 0}},
                ],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            link_field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            link_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    link_field_json,
                    "--json",
                ],
            )

            assert link_result.returncode == 0, f"Failed to create link field: {link_result.stderr}"
            link_field_data = json.loads(link_result.stdout)
            link_field_id = link_field_data["id"]

            # Get the Amount field ID from table2
            table2_obj = base.table(table2_id)
            table2_schema = table2_obj.schema()
            amount_field = next(f for f in table2_schema.fields if f.name == "Amount")
            amount_field_id = amount_field.id

            # Create a rollup field
            rollup_field_json = json.dumps({
                "name": "TotalAmount",
                "type": "rollup",
                "options": {
                    "recordLinkFieldId": link_field_id,
                    "fieldIdInLinkedTable": amount_field_id,
                    "aggregationFunction": "SUM",
                },
            })

            rollup_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    rollup_field_json,
                    "--json",
                ],
            )

            assert rollup_result.returncode == 0, f"Failed to create rollup field: {rollup_result.stderr}"

            # Create records in table2 with amounts
            record2a = table2_obj.create({"Title": "Item A", "Amount": 10})
            record2b = table2_obj.create({"Title": "Item B", "Amount": 25})
            record2c = table2_obj.create({"Title": "Item C", "Amount": 15})

            # Create a record in table1 with links to table2 records
            table1_obj = base.table(table1_id)
            record1 = table1_obj.create({
                "Name": "Parent Record",
                "LinkedRecords": [record2a["id"], record2b["id"], record2c["id"]],
            })

            # Verify the rollup field shows the calculated sum
            fetched_record = table1_obj.get(record1["id"])
            assert "TotalAmount" in fetched_record["fields"]
            # Sum of 10 + 25 + 15 = 50
            assert fetched_record["fields"]["TotalAmount"] == 50

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass

    @pytest.mark.xfail(reason="Airtable API does not support creating rollup fields")
    def test_fields_create_rollup_with_field_names(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test creating a rollup field using field names instead of IDs."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        table1_name = f"TestRollupName1_{uuid.uuid4().hex[:8]}"
        table2_name = f"TestRollupName2_{uuid.uuid4().hex[:8]}"
        table1_id = None
        table2_id = None

        try:
            # Create two tables
            base = api.base(test_base_id)
            table1 = base.create_table(
                name=table1_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            table1_id = table1.id

            table2 = base.create_table(
                name=table2_name,
                fields=[
                    {"name": "Title", "type": "singleLineText"},
                    {"name": "Amount", "type": "number", "options": {"precision": 0}},
                ],
            )
            table2_id = table2.id

            # Add a multipleRecordLinks field to table1 linking to table2
            link_field_json = json.dumps({
                "name": "LinkedRecords",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": table2_id},
            })

            link_result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    link_field_json,
                    "--json",
                ],
            )

            assert link_result.returncode == 0, f"Failed to create link field: {link_result.stderr}"
            link_field_data = json.loads(link_result.stdout)
            link_field_id = link_field_data["id"]

            # Get the Amount field ID from table2 (for verification later)
            table2_obj = base.table(table2_id)
            table2_schema = table2_obj.schema()
            amount_field = next(f for f in table2_schema.fields if f.name == "Amount")
            amount_field_id = amount_field.id

            # Create a rollup field using field NAMES instead of IDs
            rollup_field_json = json.dumps({
                "name": "TotalAmount",
                "type": "rollup",
                "options": {
                    "recordLinkFieldName": "LinkedRecords",
                    "fieldNameInLinkedTable": "Amount",
                    "aggregationFunction": "AVERAGE",
                },
            })

            result = run_script(
                "schema.py",
                [
                    "fields",
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table1_name,
                    "--field",
                    rollup_field_json,
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Failed to create rollup field: {result.stderr}"

            # Parse JSON output
            field_result = json.loads(result.stdout)
            assert "id" in field_result
            assert field_result["name"] == "TotalAmount"
            assert field_result["type"] == "rollup"

            # Verify options contain resolved IDs (not names)
            assert "options" in field_result
            assert field_result["options"]["recordLinkFieldId"] == link_field_id
            assert field_result["options"]["fieldIdInLinkedTable"] == amount_field_id
            assert "AVERAGE" in field_result["options"]["formula"]

        finally:
            # Clean up both tables
            for table_id in [table1_id, table2_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        pass
