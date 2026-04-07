"""Tests for the record management script."""

import json
import os
import uuid

import pytest


class TestParseSortSpec:
    """Tests for parse_sort_spec function."""

    def test_single_field_ascending(self) -> None:
        """Test parsing a single field for ascending sort."""
        from records import parse_sort_spec

        result = parse_sort_spec("Name")
        assert result == ["Name"]

    def test_single_field_descending(self) -> None:
        """Test parsing a single field for descending sort."""
        from records import parse_sort_spec

        result = parse_sort_spec("Name:desc")
        assert result == ["-Name"]

    def test_multiple_fields_ascending(self) -> None:
        """Test parsing multiple fields for ascending sort."""
        from records import parse_sort_spec

        result = parse_sort_spec("Name,Age")
        assert result == ["Name", "Age"]

    def test_multiple_fields_mixed(self) -> None:
        """Test parsing multiple fields with mixed sort directions."""
        from records import parse_sort_spec

        result = parse_sort_spec("Name,Age:desc,Score")
        assert result == ["Name", "-Age", "Score"]

    def test_handles_whitespace(self) -> None:
        """Test that whitespace around fields is handled."""
        from records import parse_sort_spec

        result = parse_sort_spec(" Name , Age:desc ")
        assert result == ["Name", "-Age"]

    def test_empty_string(self) -> None:
        """Test parsing empty string returns empty list."""
        from records import parse_sort_spec

        result = parse_sort_spec("")
        assert result == []


class TestRecordsScript:
    """Tests for scripts/records.py."""

    def test_script_exists(self, scripts_dir) -> None:
        """Verify the records script exists."""
        script_path = scripts_dir / "records.py"
        assert script_path.exists(), "scripts/records.py should exist"

    def test_script_has_pep723_metadata(self, scripts_dir) -> None:
        """Verify script has PEP 723 inline metadata."""
        script_path = scripts_dir / "records.py"
        content = script_path.read_text()
        assert "# /// script" in content, "Script should have PEP 723 header"
        assert "# dependencies = [" in content, "Script should declare dependencies"
        assert "pyairtable" in content, "Script should depend on pyairtable"
        assert "# ///" in content, "Script should have PEP 723 closing marker"

    def test_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing."""
        result = run_script(
            "records.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--fields",
                '{"Name": "Test"}',
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_requires_base_id_table_fields_for_create(self, run_script) -> None:
        """Verify --base-id, --table, and --fields are required for create."""
        result = run_script("records.py", ["create"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--fields" in result.stderr
        )

    def test_requires_base_id_table_record_id_for_get(self, run_script) -> None:
        """Verify --base-id, --table, and --record-id are required for get."""
        result = run_script("records.py", ["get"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--record-id" in result.stderr
        )

    def test_requires_base_id_table_for_list(self, run_script) -> None:
        """Verify --base-id and --table are required for list."""
        result = run_script("records.py", ["list"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert "--base-id" in result.stderr or "--table" in result.stderr

    def test_list_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for list."""
        result = run_script(
            "records.py",
            [
                "list",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_get_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for get."""
        result = run_script(
            "records.py",
            [
                "get",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--record-id",
                "recXXXXX",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_create_with_invalid_json_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --fields has invalid JSON."""
        result = run_script(
            "records.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--fields",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert (
            "invalid json" in result.stderr.lower() or "error" in result.stderr.lower()
        )

    def test_create_with_non_object_json_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --fields is not a JSON object."""
        result = run_script(
            "records.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--fields",
                '["array", "not", "object"]',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "object" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_create_with_empty_fields_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --fields is empty object."""
        result = run_script(
            "records.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--fields",
                "{}",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert (
            "at least one field" in result.stderr.lower()
            or "error" in result.stderr.lower()
        )

    def test_requires_base_id_table_record_id_fields_for_update(
        self, run_script
    ) -> None:
        """Verify --base-id, --table, --record-id, and --fields are required for update."""
        result = run_script("records.py", ["update"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--record-id" in result.stderr
            or "--fields" in result.stderr
        )

    def test_update_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for update."""
        result = run_script(
            "records.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--record-id",
                "recXXXXX",
                "--fields",
                '{"Name": "New"}',
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_update_with_invalid_json_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --fields has invalid JSON for update."""
        result = run_script(
            "records.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--record-id",
                "recXXXXX",
                "--fields",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert (
            "invalid json" in result.stderr.lower() or "error" in result.stderr.lower()
        )

    def test_update_with_empty_fields_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --fields is empty object for update."""
        result = run_script(
            "records.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--record-id",
                "recXXXXX",
                "--fields",
                "{}",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert (
            "at least one field" in result.stderr.lower()
            or "error" in result.stderr.lower()
        )

    def test_requires_base_id_table_record_id_for_delete(self, run_script) -> None:
        """Verify --base-id, --table, and --record-id are required for delete."""
        result = run_script("records.py", ["delete"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--record-id" in result.stderr
        )

    def test_delete_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for delete."""
        result = run_script(
            "records.py",
            [
                "delete",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--record-id",
                "recXXXXX",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_requires_base_id_table_for_query(self, run_script) -> None:
        """Verify --base-id and --table are required for query."""
        result = run_script("records.py", ["query"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert "--base-id" in result.stderr or "--table" in result.stderr

    def test_query_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for query."""
        result = run_script(
            "records.py",
            [
                "query",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--formula",
                "{Name}='Test'",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_query_requires_formula_or_match(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when neither --formula nor --match is provided."""
        result = run_script(
            "records.py",
            [
                "query",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "formula" in result.stderr.lower() or "match" in result.stderr.lower()

    def test_query_with_invalid_match_json_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --match has invalid JSON."""
        result = run_script(
            "records.py",
            [
                "query",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--match",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert (
            "invalid json" in result.stderr.lower() or "error" in result.stderr.lower()
        )

    def test_query_with_non_object_match_json_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --match is not a JSON object."""
        result = run_script(
            "records.py",
            [
                "query",
                "--base-id",
                "appXXXXX",
                "--table",
                "TestTable",
                "--match",
                '["array", "not", "object"]',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "object" in result.stderr.lower() or "error" in result.stderr.lower()


@pytest.mark.integration
class TestRecordsIntegration:
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

    def test_create_record_and_verify(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test creating a table, creating a record, verifying it exists, and cleaning up."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestRecords_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Email", "type": "email"},
                    {"name": "Count", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create a record using CLI with --json flag
            fields = {"Name": "Test User", "Email": "test@example.com", "Count": 42}
            result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Parse JSON output
            create_result = json.loads(result.stdout)
            assert "id" in create_result, "Response should contain record ID"
            assert create_result["id"].startswith("rec"), (
                "Record ID should start with 'rec'"
            )
            assert "fields" in create_result, "Response should contain fields"
            assert create_result["fields"]["Name"] == "Test User"
            assert create_result["fields"]["Email"] == "test@example.com"
            assert create_result["fields"]["Count"] == 42

            # Verify record exists by fetching it
            table = base.table(table_name)
            fetched = table.get(create_result["id"])
            assert fetched["id"] == create_result["id"]
            assert fetched["fields"]["Name"] == "Test User"

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

    def test_create_record_human_readable_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test creating a record without --json flag shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestRecordsHuman_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Title", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create a record using CLI without --json flag
            fields = {"Title": "My Test Record"}
            result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                ],
            )

            assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Verify human-readable output
            assert "Created record:" in result.stdout
            assert "rec" in result.stdout  # Record ID starts with 'rec'
            assert "Fields:" in result.stdout
            assert "Title:" in result.stdout
            assert "My Test Record" in result.stdout

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

    def test_create_record_with_various_field_types(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test creating a record with multiple field types."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestRecordsTypes_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table with various field types
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Count", "type": "number", "options": {"precision": 0}},
                    {"name": "Email", "type": "email"},
                    {"name": "Website", "type": "url"},
                ],
            )
            created_table_id = new_table.id

            # Create a record with various field types
            fields = {
                "Name": "Test Record",
                "Count": 123,
                "Email": "test@example.com",
                "Website": "https://example.com",
            }
            result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
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
            assert create_result["fields"]["Name"] == "Test Record"
            assert create_result["fields"]["Count"] == 123
            assert create_result["fields"]["Email"] == "test@example.com"
            assert create_result["fields"]["Website"] == "https://example.com"

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

    def test_get_record_by_id(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test creating a record, retrieving it by ID, and verifying fields match."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestGetRecord_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Email", "type": "email"},
                    {"name": "Count", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create a record using CLI with --json flag
            fields = {
                "Name": "Get Test User",
                "Email": "gettest@example.com",
                "Count": 99,
            }
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, (
                f"Create failed: {create_result.stderr}"
            )
            created_record = json.loads(create_result.stdout)
            record_id = created_record["id"]

            # Now retrieve the record using get command with --json flag
            get_result = run_script(
                "records.py",
                [
                    "get",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--json",
                ],
            )

            assert get_result.returncode == 0, f"Get failed: {get_result.stderr}"

            # Parse JSON output and verify fields match
            retrieved_record = json.loads(get_result.stdout)
            assert retrieved_record["id"] == record_id
            assert "createdTime" in retrieved_record
            assert retrieved_record["fields"]["Name"] == "Get Test User"
            assert retrieved_record["fields"]["Email"] == "gettest@example.com"
            assert retrieved_record["fields"]["Count"] == 99

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

    def test_get_record_human_readable_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test getting a record without --json flag shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestGetRecordHuman_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Title", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create a record using CLI with --json flag
            fields = {"Title": "Human Readable Test"}
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, (
                f"Create failed: {create_result.stderr}"
            )
            created_record = json.loads(create_result.stdout)
            record_id = created_record["id"]

            # Now retrieve the record using get command without --json flag
            get_result = run_script(
                "records.py",
                [
                    "get",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                ],
            )

            assert get_result.returncode == 0, f"Get failed: {get_result.stderr}"

            # Verify human-readable output
            assert "Record ID:" in get_result.stdout
            assert record_id in get_result.stdout
            assert "Created:" in get_result.stdout
            assert "Fields:" in get_result.stdout
            assert "Title:" in get_result.stdout
            assert "Human Readable Test" in get_result.stdout

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

    def test_list_records_and_verify_count(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test creating multiple records, listing them, and verifying count."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestListRecords_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Email", "type": "email"},
                    {"name": "Count", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create 3 records
            created_ids = []
            for i in range(3):
                fields = {
                    "Name": f"Test User {i + 1}",
                    "Email": f"user{i + 1}@example.com",
                    "Count": (i + 1) * 10,
                }
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"
                created = json.loads(result.stdout)
                created_ids.append(created["id"])

            # List all records with --json flag
            list_result = run_script(
                "records.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--json",
                ],
            )

            assert list_result.returncode == 0, f"List failed: {list_result.stderr}"

            # Parse JSON output and verify count
            records = json.loads(list_result.stdout)
            assert len(records) == 3, f"Expected 3 records, got {len(records)}"

            # Verify all created IDs are present
            listed_ids = [r["id"] for r in records]
            for created_id in created_ids:
                assert created_id in listed_ids, (
                    f"Record {created_id} not found in list"
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

    def test_list_records_with_max_records(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test listing records with --max-records option."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestListMaxRecords_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create 5 records
            for i in range(5):
                fields = {"Name": f"Record {i + 1}"}
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # List with max-records=2
            list_result = run_script(
                "records.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--max-records",
                    "2",
                    "--json",
                ],
            )

            assert list_result.returncode == 0, f"List failed: {list_result.stderr}"

            # Parse JSON output and verify count is limited
            records = json.loads(list_result.stdout)
            assert len(records) == 2, f"Expected 2 records (max), got {len(records)}"

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

    def test_list_records_with_fields_filter(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test listing records with --fields option to limit returned fields."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestListFields_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Email", "type": "email"},
                    {"name": "Phone", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create a record with all fields
            fields = {
                "Name": "Test User",
                "Email": "test@example.com",
                "Phone": "555-1234",
            }
            result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )
            assert result.returncode == 0, f"Create failed: {result.stderr}"

            # List with only Name and Email fields
            list_result = run_script(
                "records.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    "Name,Email",
                    "--json",
                ],
            )

            assert list_result.returncode == 0, f"List failed: {list_result.stderr}"

            # Parse JSON output and verify only requested fields are present
            records = json.loads(list_result.stdout)
            assert len(records) == 1
            record_fields = records[0]["fields"]
            assert "Name" in record_fields
            assert "Email" in record_fields
            assert "Phone" not in record_fields, "Phone field should be excluded"

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

    def test_list_records_table_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test listing records without --json shows table format with IDs in first column."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestListTable_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Value", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create 2 records
            for i, name in enumerate(["Alice", "Bob"]):
                fields = {"Name": name, "Value": (i + 1) * 100}
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # List without --json flag
            list_result = run_script(
                "records.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                ],
            )

            assert list_result.returncode == 0, f"List failed: {list_result.stderr}"

            # Verify table format
            output = list_result.stdout
            lines = output.strip().split("\n")

            # Should have header, separator, and 2 data rows
            assert len(lines) >= 4, f"Expected at least 4 lines, got {len(lines)}"

            # First line should be header with ID first
            header = lines[0]
            assert header.startswith("ID"), "Header should start with ID column"
            assert "Name" in header
            assert "Value" in header

            # Second line should be separator
            assert "---" in lines[1], "Second line should be separator"

            # Data rows should start with record IDs
            for line in lines[2:]:
                assert line.startswith("rec"), (
                    f"Data row should start with record ID: {line}"
                )

            # Verify data values are present
            assert "Alice" in output
            assert "Bob" in output
            assert "100" in output
            assert "200" in output

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

    def test_update_record_and_verify(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test creating a record, updating a field, and verifying the new value."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestUpdateRecord_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Email", "type": "email"},
                    {"name": "Count", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create a record using CLI with --json flag
            fields = {
                "Name": "Original Name",
                "Email": "original@example.com",
                "Count": 10,
            }
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, (
                f"Create failed: {create_result.stderr}"
            )
            created_record = json.loads(create_result.stdout)
            record_id = created_record["id"]

            # Update only the Name field (partial update)
            update_fields = {"Name": "Updated Name"}
            update_result = run_script(
                "records.py",
                [
                    "update",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--fields",
                    json.dumps(update_fields),
                    "--json",
                ],
            )

            assert update_result.returncode == 0, (
                f"Update failed: {update_result.stderr}"
            )

            # Parse JSON output and verify update
            updated_record = json.loads(update_result.stdout)
            assert updated_record["id"] == record_id
            assert updated_record["fields"]["Name"] == "Updated Name"
            # Verify other fields were NOT modified (partial update)
            assert updated_record["fields"]["Email"] == "original@example.com"
            assert updated_record["fields"]["Count"] == 10

            # Verify by fetching the record again
            get_result = run_script(
                "records.py",
                [
                    "get",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--json",
                ],
            )

            assert get_result.returncode == 0, f"Get failed: {get_result.stderr}"
            fetched_record = json.loads(get_result.stdout)
            assert fetched_record["fields"]["Name"] == "Updated Name"

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

    def test_update_record_human_readable_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test updating a record without --json flag shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestUpdateHuman_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Title", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create a record using CLI with --json flag
            fields = {"Title": "Original Title"}
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, (
                f"Create failed: {create_result.stderr}"
            )
            created_record = json.loads(create_result.stdout)
            record_id = created_record["id"]

            # Update using CLI without --json flag
            update_fields = {"Title": "New Title"}
            update_result = run_script(
                "records.py",
                [
                    "update",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--fields",
                    json.dumps(update_fields),
                ],
            )

            assert update_result.returncode == 0, (
                f"Update failed: {update_result.stderr}"
            )

            # Verify human-readable output
            assert "Updated record:" in update_result.stdout
            assert record_id in update_result.stdout
            assert "Fields:" in update_result.stdout
            assert "Title:" in update_result.stdout
            assert "New Title" in update_result.stdout

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

    def test_update_linked_record_field(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test updating a linked record field (array of record IDs)."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table names
        parent_table_name = f"TestParent_{uuid.uuid4().hex[:8]}"
        child_table_name = f"TestChild_{uuid.uuid4().hex[:8]}"
        parent_table_id = None
        child_table_id = None

        try:
            base = api.base(test_base_id)

            # Create parent table first
            parent_table = base.create_table(
                name=parent_table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                ],
            )
            parent_table_id = parent_table.id

            # Create child table with link to parent
            child_table = base.create_table(
                name=child_table_name,
                fields=[
                    {"name": "Title", "type": "singleLineText"},
                    {
                        "name": "Parent",
                        "type": "multipleRecordLinks",
                        "options": {"linkedTableId": parent_table_id},
                    },
                ],
            )
            child_table_id = child_table.id

            # Create parent records
            parent1 = base.table(parent_table_name).create({"Name": "Parent 1"})
            parent2 = base.table(parent_table_name).create({"Name": "Parent 2"})

            # Create child record with first parent link
            child_fields = {"Title": "Child Record", "Parent": [parent1["id"]]}
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    child_table_name,
                    "--fields",
                    json.dumps(child_fields),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, (
                f"Create failed: {create_result.stderr}"
            )
            created_record = json.loads(create_result.stdout)
            record_id = created_record["id"]

            # Update to link to both parents (array of record IDs)
            update_fields = {"Parent": [parent1["id"], parent2["id"]]}
            update_result = run_script(
                "records.py",
                [
                    "update",
                    "--base-id",
                    test_base_id,
                    "--table",
                    child_table_name,
                    "--record-id",
                    record_id,
                    "--fields",
                    json.dumps(update_fields),
                    "--json",
                ],
            )

            assert update_result.returncode == 0, (
                f"Update failed: {update_result.stderr}"
            )

            # Verify the linked records were updated
            updated_record = json.loads(update_result.stdout)
            assert "Parent" in updated_record["fields"]
            assert len(updated_record["fields"]["Parent"]) == 2
            assert parent1["id"] in updated_record["fields"]["Parent"]
            assert parent2["id"] in updated_record["fields"]["Parent"]

        finally:
            # Clean up: delete the test tables (child first due to link)
            for table_id in [child_table_id, parent_table_id]:
                if table_id:
                    try:
                        api.request(
                            method="DELETE",
                            url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{table_id}",
                        )
                    except Exception:
                        # Best effort cleanup
                        pass

    def test_delete_record_and_verify(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test creating a record, deleting it, and verifying it no longer exists."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestDeleteRecord_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create a record using CLI with --json flag
            fields = {"Name": "Record to Delete"}
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps(fields),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, (
                f"Create failed: {create_result.stderr}"
            )
            created_record = json.loads(create_result.stdout)
            record_id = created_record["id"]

            # Delete the record using CLI
            delete_result = run_script(
                "records.py",
                [
                    "delete",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                ],
            )

            assert delete_result.returncode == 0, (
                f"Delete failed: {delete_result.stderr}"
            )
            assert f"Deleted record: {record_id}" in delete_result.stdout

            # Verify the record no longer exists by trying to get it
            get_result = run_script(
                "records.py",
                [
                    "get",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--json",
                ],
            )

            # Get should fail because record no longer exists
            assert get_result.returncode == 1, "Get should fail for deleted record"
            assert (
                "error" in get_result.stderr.lower()
                or "not found" in get_result.stderr.lower()
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

    def test_delete_record_json_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test deleting a record with --json flag outputs valid JSON."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestDeleteJson_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            created_table_id = new_table.id

            # Create a record
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps({"Name": "To Delete"}),
                    "--json",
                ],
            )
            assert create_result.returncode == 0, f"Create failed: {create_result.stderr}"
            record_id = json.loads(create_result.stdout)["id"]

            # Delete with --json
            delete_result = run_script(
                "records.py",
                [
                    "delete",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--json",
                ],
            )

            assert delete_result.returncode == 0, f"Delete failed: {delete_result.stderr}"
            data = json.loads(delete_result.stdout)
            assert data["id"] == record_id
            assert data["deleted"] is True

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_add_comment_json_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test adding a comment with --json flag outputs valid JSON."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestCommentJson_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            created_table_id = new_table.id

            # Create a record to comment on
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps({"Name": "Commentable"}),
                    "--json",
                ],
            )
            assert create_result.returncode == 0, f"Create failed: {create_result.stderr}"
            record_id = json.loads(create_result.stdout)["id"]

            # Add comment with --json
            comment_result = run_script(
                "records.py",
                [
                    "add-comment",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--text",
                    "Test comment via JSON",
                    "--json",
                ],
            )

            assert comment_result.returncode == 0, f"Add comment failed: {comment_result.stderr}"
            data = json.loads(comment_result.stdout)
            assert "id" in data
            assert data["text"] == "Test comment via JSON"

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_delete_comment_json_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test deleting a comment with --json flag outputs valid JSON."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestDelCommentJson_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[{"name": "Name", "type": "singleLineText"}],
            )
            created_table_id = new_table.id

            # Create a record
            create_result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    json.dumps({"Name": "Commentable"}),
                    "--json",
                ],
            )
            assert create_result.returncode == 0, f"Create failed: {create_result.stderr}"
            record_id = json.loads(create_result.stdout)["id"]

            # Add a comment first
            add_result = run_script(
                "records.py",
                [
                    "add-comment",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--text",
                    "Comment to delete",
                    "--json",
                ],
            )
            assert add_result.returncode == 0, f"Add comment failed: {add_result.stderr}"
            comment_id = json.loads(add_result.stdout)["id"]

            # Delete comment with --json
            delete_result = run_script(
                "records.py",
                [
                    "delete-comment",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-id",
                    record_id,
                    "--comment-id",
                    comment_id,
                    "--json",
                ],
            )

            assert delete_result.returncode == 0, f"Delete comment failed: {delete_result.stderr}"
            data = json.loads(delete_result.stdout)
            assert data["id"] == comment_id
            assert data["deleted"] is True

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_records_with_formula(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records with Airtable formula syntax."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestQueryFormula_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Score", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create records with different scores
            test_data = [
                {"Name": "Alice", "Score": 10},
                {"Name": "Bob", "Score": 25},
                {"Name": "Charlie", "Score": 30},
                {"Name": "Diana", "Score": 15},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query records where Score > 20
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "{Score}>20",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            # Parse JSON output
            records = json.loads(query_result.stdout)
            assert len(records) == 2, (
                f"Expected 2 records with Score > 20, got {len(records)}"
            )

            # Verify the correct records were returned
            names = {r["fields"]["Name"] for r in records}
            assert names == {"Bob", "Charlie"}, f"Expected Bob and Charlie, got {names}"

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

    def test_query_records_with_match(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records with --match for equality matching."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestQueryMatch_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "City", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create records with different cities
            test_data = [
                {"Name": "Alice", "City": "New York"},
                {"Name": "Bob", "City": "London"},
                {"Name": "Charlie", "City": "New York"},
                {"Name": "Diana", "City": "Paris"},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query records where City = "New York"
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--match",
                    '{"City": "New York"}',
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            # Parse JSON output
            records = json.loads(query_result.stdout)
            assert len(records) == 2, (
                f"Expected 2 records in New York, got {len(records)}"
            )

            # Verify the correct records were returned
            names = {r["fields"]["Name"] for r in records}
            assert names == {"Alice", "Charlie"}, (
                f"Expected Alice and Charlie, got {names}"
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

    def test_query_records_with_string_formula(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records with string equality formula."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestQueryString_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Status", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create records with different statuses
            test_data = [
                {"Name": "Task 1", "Status": "active"},
                {"Name": "Task 2", "Status": "completed"},
                {"Name": "Task 3", "Status": "active"},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query records where Status = 'active'
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "{Status}='active'",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            # Parse JSON output
            records = json.loads(query_result.stdout)
            assert len(records) == 2, f"Expected 2 active records, got {len(records)}"

            # Verify the correct records were returned
            names = {r["fields"]["Name"] for r in records}
            assert names == {"Task 1", "Task 3"}, (
                f"Expected Task 1 and Task 3, got {names}"
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

    def test_query_records_human_readable_output(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records without --json shows table format."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestQueryHuman_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Value", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create records
            test_data = [
                {"Name": "Low", "Value": 5},
                {"Name": "High", "Value": 100},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query records where Value >= 50 without --json flag
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "{Value}>=50",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            # Verify table format
            output = query_result.stdout
            lines = output.strip().split("\n")

            # Should have header, separator, and 1 data row
            assert len(lines) >= 3, f"Expected at least 3 lines, got {len(lines)}"

            # First line should be header with ID first
            header = lines[0]
            assert header.startswith("ID"), "Header should start with ID column"
            assert "Name" in header
            assert "Value" in header

            # Second line should be separator
            assert "---" in lines[1], "Second line should be separator"

            # Should contain High record (Value=100 >= 50)
            assert "High" in output
            assert "100" in output
            # Should NOT contain Low record
            assert "Low" not in output

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

    def test_query_records_no_matches(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records with no matches returns empty result."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestQueryNoMatch_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Value", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create a record
            result = run_script(
                "records.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--fields",
                    '{"Name": "Test", "Value": 10}',
                    "--json",
                ],
            )
            assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query with formula that matches nothing
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "{Value}>1000",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            # Parse JSON output - should be empty array
            records = json.loads(query_result.stdout)
            assert records == [], f"Expected empty array, got {records}"

            # Test human-readable output for no matches
            query_result_human = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "{Value}>1000",
                ],
            )

            assert query_result_human.returncode == 0
            assert "No matching records found" in query_result_human.stdout

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

    def test_list_records_sort_ascending(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test listing records sorted by a field ascending."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestSortAsc_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Score", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create records in non-sorted order
            test_data = [
                {"Name": "Charlie", "Score": 30},
                {"Name": "Alice", "Score": 10},
                {"Name": "Bob", "Score": 20},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # List with sort by Score ascending (default)
            list_result = run_script(
                "records.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--sort",
                    "Score",
                    "--json",
                ],
            )

            assert list_result.returncode == 0, f"List failed: {list_result.stderr}"

            # Parse JSON output and verify order
            records = json.loads(list_result.stdout)
            assert len(records) == 3
            names_in_order = [r["fields"]["Name"] for r in records]
            assert names_in_order == ["Alice", "Bob", "Charlie"], (
                f"Expected ascending order by Score, got {names_in_order}"
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

    def test_list_records_sort_descending(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test listing records sorted by a field descending."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestSortDesc_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Score", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create records in non-sorted order
            test_data = [
                {"Name": "Charlie", "Score": 30},
                {"Name": "Alice", "Score": 10},
                {"Name": "Bob", "Score": 20},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # List with sort by Score descending
            list_result = run_script(
                "records.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--sort",
                    "Score:desc",
                    "--json",
                ],
            )

            assert list_result.returncode == 0, f"List failed: {list_result.stderr}"

            # Parse JSON output and verify order
            records = json.loads(list_result.stdout)
            assert len(records) == 3
            names_in_order = [r["fields"]["Name"] for r in records]
            assert names_in_order == ["Charlie", "Bob", "Alice"], (
                f"Expected descending order by Score, got {names_in_order}"
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

    def test_list_records_sort_multiple_fields(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test listing records sorted by multiple fields."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestSortMulti_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Category", "type": "singleLineText"},
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Score", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create records with same category but different scores
            test_data = [
                {"Category": "B", "Name": "Item1", "Score": 20},
                {"Category": "A", "Name": "Item2", "Score": 30},
                {"Category": "A", "Name": "Item3", "Score": 10},
                {"Category": "B", "Name": "Item4", "Score": 40},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # List with sort by Category ascending, then Score descending
            list_result = run_script(
                "records.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--sort",
                    "Category,Score:desc",
                    "--json",
                ],
            )

            assert list_result.returncode == 0, f"List failed: {list_result.stderr}"

            # Parse JSON output and verify order
            records = json.loads(list_result.stdout)
            assert len(records) == 4
            names_in_order = [r["fields"]["Name"] for r in records]
            # Category A first (ascending), then within A, Score descending (30, 10)
            # Category B second, then within B, Score descending (40, 20)
            assert names_in_order == ["Item2", "Item3", "Item4", "Item1"], (
                f"Expected Category asc, Score desc order, got {names_in_order}"
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

    def test_query_with_if_conditional_formula(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records using IF() conditional formulas."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestIfFormula_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Score", "type": "number", "options": {"precision": 0}},
                    {"name": "Category", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create records with different scores
            test_data = [
                {"Name": "Alice", "Score": 85, "Category": ""},
                {"Name": "Bob", "Score": 45, "Category": ""},
                {"Name": "Charlie", "Score": 75, "Category": ""},
                {"Name": "Diana", "Score": 30, "Category": ""},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query using IF formula: find records where IF(Score>=70, 'Pass', 'Fail') = 'Pass'
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "IF({Score}>=70,'Pass','Fail')='Pass'",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            assert len(records) == 2, (
                f"Expected 2 records with Score >= 70, got {len(records)}"
            )

            names = {r["fields"]["Name"] for r in records}
            assert names == {"Alice", "Charlie"}, (
                f"Expected Alice and Charlie, got {names}"
            )

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_with_dateadd_formula(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records using DATEADD() for date arithmetic."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestDateAdd_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "LeaseStart", "type": "date", "options": {"dateFormat": {"name": "local"}}},
                ],
            )
            created_table_id = new_table.id

            # Create records with different lease start dates
            # Use dates relative to today for predictable test results
            from datetime import date, timedelta

            today = date.today()
            three_years_ago = today - timedelta(days=3 * 365)
            one_year_ago = today - timedelta(days=365)
            six_months_ago = today - timedelta(days=180)

            test_data = [
                {"Name": "Property A", "LeaseStart": three_years_ago.isoformat()},
                {"Name": "Property B", "LeaseStart": one_year_ago.isoformat()},
                {"Name": "Property C", "LeaseStart": six_months_ago.isoformat()},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query: Find leases where lease start + 2 years is before today (renewal due)
            # DATEADD({LeaseStart}, 2, 'years') < TODAY()
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "IS_BEFORE(DATEADD({LeaseStart},2,'years'),TODAY())",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            # Property A started 3 years ago, so 3 years ago + 2 years = 1 year ago (before today)
            assert len(records) == 1, (
                f"Expected 1 record with renewal due, got {len(records)}"
            )
            assert records[0]["fields"]["Name"] == "Property A"

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_with_datetime_format_formula(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records using DATETIME_FORMAT() for date formatting."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestDateFormat_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "EventDate", "type": "date", "options": {"dateFormat": {"name": "local"}}},
                ],
            )
            created_table_id = new_table.id

            # Create records with dates in specific months
            test_data = [
                {"Name": "Event A", "EventDate": "2024-01-15"},
                {"Name": "Event B", "EventDate": "2024-03-20"},
                {"Name": "Event C", "EventDate": "2024-01-25"},
                {"Name": "Event D", "EventDate": "2024-06-10"},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query: Find events in January using DATETIME_FORMAT
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "DATETIME_FORMAT({EventDate},'MM')='01'",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            assert len(records) == 2, (
                f"Expected 2 events in January, got {len(records)}"
            )

            names = {r["fields"]["Name"] for r in records}
            assert names == {"Event A", "Event C"}, (
                f"Expected Event A and Event C, got {names}"
            )

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_with_datetime_parse_formula(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records using DATETIME_PARSE() for parsing date strings."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestDateParse_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "DateString", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create records with date strings
            test_data = [
                {"Name": "Record A", "DateString": "2023-06-15"},
                {"Name": "Record B", "DateString": "2024-01-20"},
                {"Name": "Record C", "DateString": "2023-12-25"},
                {"Name": "Record D", "DateString": "2024-03-10"},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query: Find records where parsed date is in 2024
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "YEAR(DATETIME_PARSE({DateString},'YYYY-MM-DD'))=2024",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            assert len(records) == 2, f"Expected 2 records in 2024, got {len(records)}"

            names = {r["fields"]["Name"] for r in records}
            assert names == {"Record B", "Record D"}, (
                f"Expected Record B and Record D, got {names}"
            )

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_with_is_before_is_after_formulas(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records using IS_BEFORE() and IS_AFTER() for date comparisons."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestDateCompare_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "DueDate", "type": "date", "options": {"dateFormat": {"name": "local"}}},
                ],
            )
            created_table_id = new_table.id

            from datetime import date, timedelta

            today = date.today()
            past_date = today - timedelta(days=30)
            future_date = today + timedelta(days=30)
            far_future = today + timedelta(days=90)

            test_data = [
                {"Name": "Past Task", "DueDate": past_date.isoformat()},
                {"Name": "Upcoming Task", "DueDate": future_date.isoformat()},
                {"Name": "Far Future Task", "DueDate": far_future.isoformat()},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query with IS_BEFORE: Find overdue tasks (DueDate before today)
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "IS_BEFORE({DueDate},TODAY())",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            assert len(records) == 1, f"Expected 1 overdue task, got {len(records)}"
            assert records[0]["fields"]["Name"] == "Past Task"

            # Query with IS_AFTER: Find tasks due after today
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "IS_AFTER({DueDate},TODAY())",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            assert len(records) == 2, f"Expected 2 future tasks, got {len(records)}"

            names = {r["fields"]["Name"] for r in records}
            assert names == {"Upcoming Task", "Far Future Task"}

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_with_is_same_formula(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records using IS_SAME() for date comparisons by unit."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestIsSame_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "EventDate", "type": "date", "options": {"dateFormat": {"name": "local"}}},
                ],
            )
            created_table_id = new_table.id

            from datetime import date

            today = date.today()

            # Create records with dates in the same month, different months
            test_data = [
                {"Name": "Event Today", "EventDate": today.isoformat()},
                {
                    "Name": "Event Same Month",
                    "EventDate": today.replace(day=1).isoformat(),
                },
                {"Name": "Event Different Year", "EventDate": "2020-06-15"},
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Query: Find events in the same month as today
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "IS_SAME({EventDate},TODAY(),'month')",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            # Both "Event Today" and "Event Same Month" should match
            assert len(records) == 2, (
                f"Expected 2 events in same month, got {len(records)}"
            )

            names = {r["fields"]["Name"] for r in records}
            assert names == {"Event Today", "Event Same Month"}

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_with_nested_date_formulas(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test querying records with complex nested date formulas."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestNestedDate_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "ContractDate", "type": "date", "options": {"dateFormat": {"name": "local"}}},
                ],
            )
            created_table_id = new_table.id

            from datetime import date, timedelta

            today = date.today()

            test_data = [
                {
                    "Name": "Contract A",
                    "ContractDate": (today - timedelta(days=800)).isoformat(),
                },  # ~2.2 years ago
                {
                    "Name": "Contract B",
                    "ContractDate": (today - timedelta(days=400)).isoformat(),
                },  # ~1.1 years ago
                {
                    "Name": "Contract C",
                    "ContractDate": (today - timedelta(days=100)).isoformat(),
                },  # ~3 months ago
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Complex nested formula: IF condition with DATEADD and date comparison
            # Find contracts where renewal (contract + 2 years) is already past
            # IF({ContractDate}, IS_BEFORE(DATEADD({ContractDate}, 2, 'years'), TODAY()), FALSE())
            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    "IF({ContractDate},IS_BEFORE(DATEADD({ContractDate},2,'years'),TODAY()),FALSE())",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            # Only Contract A (started ~2.2 years ago) should have renewal past
            assert len(records) == 1, (
                f"Expected 1 contract with renewal past, got {len(records)}"
            )
            assert records[0]["fields"]["Name"] == "Contract A"

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass

    def test_query_with_combined_datetime_format_parse_formulas(
        self, api, test_base_id: str | None, run_script
    ) -> None:
        """Test combined DATETIME_FORMAT and DATETIME_PARSE formulas."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        table_name = f"TestCombinedDate_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "DateField", "type": "date", "options": {"dateFormat": {"name": "local"}}},
                ],
            )
            created_table_id = new_table.id

            from datetime import date, timedelta

            today = date.today()
            two_years_future = today + timedelta(days=730)

            test_data = [
                {"Name": "Record A", "DateField": today.isoformat()},
                {"Name": "Record B", "DateField": two_years_future.isoformat()},
                {"Name": "Record C", "DateField": "2022-02-28"},  # Past date
            ]

            for fields in test_data:
                result = run_script(
                    "records.py",
                    [
                        "create",
                        "--base-id",
                        test_base_id,
                        "--table",
                        table_name,
                        "--fields",
                        json.dumps(fields),
                        "--json",
                    ],
                )
                assert result.returncode == 0, f"Create failed: {result.stderr}"

            # Complex formula: Format the date after adding 2 years, then compare year
            # DATETIME_FORMAT(DATEADD({DateField}, 2, 'years'), 'YYYY')
            # Find records where date + 2 years is in the future (year > current year)
            current_year = today.year

            query_result = run_script(
                "records.py",
                [
                    "query",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--formula",
                    f"VALUE(DATETIME_FORMAT(DATEADD({{DateField}},2,'years'),'YYYY'))>{current_year}",
                    "--json",
                ],
            )

            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"

            records = json.loads(query_result.stdout)
            # Record A (today + 2 years) and Record B (2 years future + 2 years = 4 years future)
            # should both have year > current_year
            # Record C (2022 + 2 = 2024) depends on current year
            assert len(records) >= 2, (
                f"Expected at least 2 records with future year, got {len(records)}"
            )

        finally:
            if created_table_id:
                try:
                    api.request(
                        method="DELETE",
                        url=f"https://api.airtable.com/v0/meta/bases/{test_base_id}/tables/{created_table_id}",
                    )
                except Exception:
                    pass


class TestDeleteCommentCLI:
    """Tests for delete-comment CLI subcommand argument validation."""

    def test_requires_base_id_table_record_id_comment_id(self, run_script) -> None:
        """Verify --base-id, --table, --record-id, and --comment-id are required."""
        result = run_script("records.py", ["delete-comment"])

        assert result.returncode != 0
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--record-id" in result.stderr
            or "--comment-id" in result.stderr
        )

    def test_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing."""
        result = run_script(
            "records.py",
            [
                "delete-comment",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--record-id",
                "recXXXXX",
                "--comment-id",
                "comXXXXX",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr


class TestDeleteCommentFunction:
    """Tests for the delete_comment function."""

    def test_comment_not_found_raises_value_error(self) -> None:
        """Verify ValueError when comment ID doesn't match any comment on record."""
        from unittest.mock import MagicMock

        from records import delete_comment

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value

        # Return comments that don't match the target ID
        mock_comment = MagicMock()
        mock_comment.id = "comOTHER"
        mock_table.comments.return_value = [mock_comment]

        with pytest.raises(ValueError, match="not found"):
            delete_comment(api, "appXXX", "TestTable", "recXXX", "comTARGET")

    def test_successful_delete(self) -> None:
        """Verify delete is called on the matching comment and result is returned."""
        from unittest.mock import MagicMock

        from records import delete_comment

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value

        # Return a comment that matches the target ID
        mock_comment = MagicMock()
        mock_comment.id = "comTARGET"
        mock_table.comments.return_value = [mock_comment]

        result = delete_comment(api, "appXXX", "TestTable", "recXXX", "comTARGET")

        mock_comment.delete.assert_called_once()
        assert result == {"id": "comTARGET", "deleted": True}

    def test_delete_finds_correct_comment_among_multiple(self) -> None:
        """Verify the correct comment is deleted when multiple comments exist."""
        from unittest.mock import MagicMock

        from records import delete_comment

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value

        mock_comment1 = MagicMock()
        mock_comment1.id = "comFIRST"
        mock_comment2 = MagicMock()
        mock_comment2.id = "comTARGET"
        mock_comment3 = MagicMock()
        mock_comment3.id = "comTHIRD"
        mock_table.comments.return_value = [mock_comment1, mock_comment2, mock_comment3]

        result = delete_comment(api, "appXXX", "TestTable", "recXXX", "comTARGET")

        mock_comment1.delete.assert_not_called()
        mock_comment2.delete.assert_called_once()
        mock_comment3.delete.assert_not_called()
        assert result == {"id": "comTARGET", "deleted": True}


class TestListRecordsViewFilter:
    """Tests for the --view parameter in list_records."""

    def test_view_passed_to_api(self) -> None:
        """Verify view kwarg is passed through to table.all()."""
        from unittest.mock import MagicMock

        from records import list_records

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value
        mock_table.all.return_value = []

        list_records(api, "appXXX", "TestTable", view="My View")

        mock_table.all.assert_called_once_with(view="My View")

    def test_view_not_passed_when_none(self) -> None:
        """Verify view kwarg is omitted when not provided."""
        from unittest.mock import MagicMock

        from records import list_records

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value
        mock_table.all.return_value = []

        list_records(api, "appXXX", "TestTable")

        mock_table.all.assert_called_once_with()

    def test_view_combined_with_other_options(self) -> None:
        """Verify view works alongside max_records, fields, and sort."""
        from unittest.mock import MagicMock

        from records import list_records

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value
        mock_table.all.return_value = []

        list_records(
            api,
            "appXXX",
            "TestTable",
            max_records=10,
            fields=["Name", "Email"],
            sort=["Name"],
            view="Grid view",
        )

        mock_table.all.assert_called_once_with(
            max_records=10,
            fields=["Name", "Email"],
            sort=["Name"],
            view="Grid view",
        )


class TestQueryRecordsViewFilter:
    """Tests for the --view parameter in query_records."""

    def test_view_passed_to_api_with_formula(self) -> None:
        """Verify view kwarg is passed through to table.all() with formula."""
        from unittest.mock import MagicMock

        from records import query_records

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value
        mock_table.all.return_value = []

        query_records(
            api, "appXXX", "TestTable", formula="{Status}='Active'", view="My View"
        )

        mock_table.all.assert_called_once_with(
            formula="{Status}='Active'", view="My View"
        )

    def test_view_not_passed_when_none(self) -> None:
        """Verify view kwarg is omitted when not provided."""
        from unittest.mock import MagicMock

        from records import query_records

        api = MagicMock()
        mock_table = api.base.return_value.table.return_value
        mock_table.all.return_value = []

        query_records(api, "appXXX", "TestTable", formula="{Status}='Active'")

        mock_table.all.assert_called_once_with(formula="{Status}='Active'")
