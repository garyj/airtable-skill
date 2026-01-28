"""Tests for the batch operations script."""

import json
import os
import uuid

import pytest


class TestBatchScript:
    """Tests for scripts/batch.py."""

    def test_script_exists(self, scripts_dir) -> None:
        """Verify the batch script exists."""
        script_path = scripts_dir / "batch.py"
        assert script_path.exists(), "scripts/batch.py should exist"

    def test_script_has_pep723_metadata(self, scripts_dir) -> None:
        """Verify script has PEP 723 inline metadata."""
        script_path = scripts_dir / "batch.py"
        content = script_path.read_text()
        assert "# /// script" in content, "Script should have PEP 723 header"
        assert "# dependencies = [" in content, "Script should declare dependencies"
        assert "pyairtable" in content, "Script should depend on pyairtable"
        assert "# ///" in content, "Script should have PEP 723 closing marker"

    def test_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing."""
        result = run_script(
            "batch.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '[{"Name": "Test"}]',
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_requires_base_id_table_records_for_create(self, run_script) -> None:
        """Verify --base-id, --table, and --records are required for create."""
        result = run_script("batch.py", ["create"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--records" in result.stderr
        )

    def test_create_with_invalid_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records has invalid JSON."""
        result = run_script(
            "batch.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "Invalid JSON" in result.stderr or "Error" in result.stderr

    def test_create_with_non_array_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records is not an array."""
        result = run_script(
            "batch.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '{"Name": "Test"}',  # object, not array
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "array" in result.stderr.lower() or "Error" in result.stderr

    def test_create_with_empty_array_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records is an empty array."""
        result = run_script(
            "batch.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                "[]",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "at least one" in result.stderr.lower() or "Error" in result.stderr

    def test_requires_base_id_table_records_for_update(self, run_script) -> None:
        """Verify --base-id, --table, and --records are required for update."""
        result = run_script("batch.py", ["update"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--records" in result.stderr
        )

    def test_update_with_invalid_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records has invalid JSON for update."""
        result = run_script(
            "batch.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "Invalid JSON" in result.stderr or "Error" in result.stderr

    def test_update_with_non_array_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records is not an array for update."""
        result = run_script(
            "batch.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '{"id": "recXXX", "fields": {"Name": "Test"}}',  # object, not array
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "array" in result.stderr.lower() or "Error" in result.stderr

    def test_update_with_empty_array_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records is an empty array for update."""
        result = run_script(
            "batch.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                "[]",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "at least one" in result.stderr.lower() or "Error" in result.stderr

    def test_update_with_missing_id_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when record is missing 'id' field."""
        result = run_script(
            "batch.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '[{"fields": {"Name": "Test"}}]',  # missing id
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "'id'" in result.stderr or "Error" in result.stderr

    def test_update_with_missing_fields_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when record is missing 'fields' object."""
        result = run_script(
            "batch.py",
            [
                "update",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '[{"id": "recXXX"}]',  # missing fields
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "'fields'" in result.stderr or "Error" in result.stderr

    def test_requires_base_id_table_records_key_fields_for_upsert(self, run_script) -> None:
        """Verify --base-id, --table, --records, and --key-fields are required for upsert."""
        result = run_script("batch.py", ["upsert"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--records" in result.stderr
            or "--key-fields" in result.stderr
        )

    def test_upsert_with_invalid_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records has invalid JSON for upsert."""
        result = run_script(
            "batch.py",
            [
                "upsert",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                "not valid json",
                "--key-fields",
                "Email",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "Invalid JSON" in result.stderr or "Error" in result.stderr

    def test_upsert_with_non_array_json_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records is not an array for upsert."""
        result = run_script(
            "batch.py",
            [
                "upsert",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '{"Email": "test@example.com"}',  # object, not array
                "--key-fields",
                "Email",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "array" in result.stderr.lower() or "Error" in result.stderr

    def test_upsert_with_empty_array_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --records is an empty array for upsert."""
        result = run_script(
            "batch.py",
            [
                "upsert",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                "[]",
                "--key-fields",
                "Email",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "at least one" in result.stderr.lower() or "Error" in result.stderr

    def test_upsert_with_empty_key_fields_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --key-fields is empty for upsert."""
        result = run_script(
            "batch.py",
            [
                "upsert",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '[{"Email": "test@example.com"}]',
                "--key-fields",
                "",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "key field" in result.stderr.lower() or "Error" in result.stderr

    def test_upsert_with_missing_key_field_in_record_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when record is missing a key field."""
        result = run_script(
            "batch.py",
            [
                "upsert",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--records",
                '[{"Name": "Test"}]',  # missing Email key field
                "--key-fields",
                "Email",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "key field" in result.stderr.lower() or "Error" in result.stderr

    def test_requires_base_id_table_record_ids_for_delete(self, run_script) -> None:
        """Verify --base-id, --table, and --record-ids are required for delete."""
        result = run_script("batch.py", ["delete"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--table" in result.stderr
            or "--record-ids" in result.stderr
        )

    def test_delete_with_empty_record_ids_shows_error(self, run_script, env_with_test_token) -> None:
        """Verify error message when --record-ids is empty."""
        result = run_script(
            "batch.py",
            [
                "delete",
                "--base-id",
                "appXXXXX",
                "--table",
                "Test",
                "--record-ids",
                "",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "at least one" in result.stderr.lower() or "Error" in result.stderr


class TestBatchCreateRecordsFunction:
    """Unit tests for batch_create_records function."""

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_create_records

        api = MagicMock()

        with pytest.raises(ValueError, match="Invalid JSON"):
            batch_create_records(api, "app123", "Table", "not json")

    def test_non_array_raises_error(self) -> None:
        """Test that non-array JSON raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_create_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must be a JSON array"):
            batch_create_records(api, "app123", "Table", '{"Name": "test"}')

    def test_empty_array_raises_error(self) -> None:
        """Test that empty array raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_create_records

        api = MagicMock()

        with pytest.raises(ValueError, match="At least one record"):
            batch_create_records(api, "app123", "Table", "[]")

    def test_non_object_record_raises_error(self) -> None:
        """Test that non-object record raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_create_records

        api = MagicMock()

        with pytest.raises(ValueError, match="Record at index 0 must be an object"):
            batch_create_records(api, "app123", "Table", '["not an object"]')

    def test_empty_object_record_raises_error(self) -> None:
        """Test that empty object record raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_create_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must have at least one field"):
            batch_create_records(api, "app123", "Table", "[{}]")


class TestBatchUpdateRecordsFunction:
    """Unit tests for batch_update_records function."""

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="Invalid JSON"):
            batch_update_records(api, "app123", "Table", "not json")

    def test_non_array_raises_error(self) -> None:
        """Test that non-array JSON raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must be a JSON array"):
            batch_update_records(
                api, "app123", "Table", '{"id": "recXXX", "fields": {"Name": "test"}}'
            )

    def test_empty_array_raises_error(self) -> None:
        """Test that empty array raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="At least one record"):
            batch_update_records(api, "app123", "Table", "[]")

    def test_non_object_record_raises_error(self) -> None:
        """Test that non-object record raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="Record at index 0 must be an object"):
            batch_update_records(api, "app123", "Table", '["not an object"]')

    def test_missing_id_raises_error(self) -> None:
        """Test that missing id raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must have an 'id' field"):
            batch_update_records(
                api, "app123", "Table", '[{"fields": {"Name": "test"}}]'
            )

    def test_empty_id_raises_error(self) -> None:
        """Test that empty id raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="non-empty string 'id'"):
            batch_update_records(
                api, "app123", "Table", '[{"id": "", "fields": {"Name": "test"}}]'
            )

    def test_missing_fields_raises_error(self) -> None:
        """Test that missing fields raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must have a 'fields' object"):
            batch_update_records(api, "app123", "Table", '[{"id": "recXXX"}]')

    def test_non_object_fields_raises_error(self) -> None:
        """Test that non-object fields raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="'fields' must be an object"):
            batch_update_records(
                api, "app123", "Table", '[{"id": "recXXX", "fields": "not an object"}]'
            )

    def test_empty_fields_raises_error(self) -> None:
        """Test that empty fields raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_update_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must have at least one field"):
            batch_update_records(
                api, "app123", "Table", '[{"id": "recXXX", "fields": {}}]'
            )


class TestBatchUpsertRecordsFunction:
    """Unit tests for batch_upsert_records function."""

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="Invalid JSON"):
            batch_upsert_records(api, "app123", "Table", "not json", "Email")

    def test_non_array_raises_error(self) -> None:
        """Test that non-array JSON raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must be a JSON array"):
            batch_upsert_records(
                api, "app123", "Table", '{"Email": "test@example.com"}', "Email"
            )

    def test_empty_array_raises_error(self) -> None:
        """Test that empty array raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="At least one record"):
            batch_upsert_records(api, "app123", "Table", "[]", "Email")

    def test_non_object_record_raises_error(self) -> None:
        """Test that non-object record raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="Record at index 0 must be an object"):
            batch_upsert_records(api, "app123", "Table", '["not an object"]', "Email")

    def test_empty_object_record_raises_error(self) -> None:
        """Test that empty object record raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must have at least one field"):
            batch_upsert_records(api, "app123", "Table", "[{}]", "Email")

    def test_empty_key_fields_raises_error(self) -> None:
        """Test that empty key fields raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="At least one key field"):
            batch_upsert_records(
                api, "app123", "Table", '[{"Email": "test@example.com"}]', ""
            )

    def test_whitespace_only_key_fields_raises_error(self) -> None:
        """Test that whitespace-only key fields raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="At least one key field"):
            batch_upsert_records(
                api, "app123", "Table", '[{"Email": "test@example.com"}]', "   "
            )

    def test_missing_key_field_in_record_raises_error(self) -> None:
        """Test that missing key field in record raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()

        with pytest.raises(ValueError, match="must contain key field 'Email'"):
            batch_upsert_records(
                api, "app123", "Table", '[{"Name": "Test"}]', "Email"
            )

    def test_successful_upsert(self) -> None:
        """Test successful upsert operation."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()
        table = MagicMock()
        api.base.return_value.table.return_value = table
        table.batch_upsert.return_value = {
            "createdRecords": ["recNew123"],
            "updatedRecords": ["recExisting456"],
            "records": [
                {"id": "recExisting456", "fields": {"Email": "existing@example.com", "Name": "Updated"}},
                {"id": "recNew123", "fields": {"Email": "new@example.com", "Name": "New"}},
            ],
        }

        result = batch_upsert_records(
            api,
            "app123",
            "Table",
            '[{"Email": "existing@example.com", "Name": "Updated"}, {"Email": "new@example.com", "Name": "New"}]',
            "Email",
        )

        assert result["created"] == ["recNew123"]
        assert result["updated"] == ["recExisting456"]
        assert len(result["records"]) == 2
        table.batch_upsert.assert_called_once_with(
            [
                {"fields": {"Email": "existing@example.com", "Name": "Updated"}},
                {"fields": {"Email": "new@example.com", "Name": "New"}},
            ],
            key_fields=["Email"],
        )

    def test_multiple_key_fields(self) -> None:
        """Test upsert with multiple key fields."""
        from unittest.mock import MagicMock

        from batch import batch_upsert_records

        api = MagicMock()
        table = MagicMock()
        api.base.return_value.table.return_value = table
        table.batch_upsert.return_value = {
            "createdRecords": [],
            "updatedRecords": ["recXXX"],
            "records": [
                {"id": "recXXX", "fields": {"Email": "test@example.com", "Name": "Test", "Age": 30}},
            ],
        }

        result = batch_upsert_records(
            api,
            "app123",
            "Table",
            '[{"Email": "test@example.com", "Name": "Test", "Age": 30}]',
            "Email,Name",
        )

        assert result["created"] == []
        assert result["updated"] == ["recXXX"]
        table.batch_upsert.assert_called_once_with(
            [{"fields": {"Email": "test@example.com", "Name": "Test", "Age": 30}}],
            key_fields=["Email", "Name"],
        )


class TestBatchDeleteRecordsFunction:
    """Unit tests for batch_delete_records function."""

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_delete_records

        api = MagicMock()

        with pytest.raises(ValueError, match="At least one record ID"):
            batch_delete_records(api, "app123", "Table", "")

    def test_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only string raises ValueError."""
        from unittest.mock import MagicMock

        from batch import batch_delete_records

        api = MagicMock()

        with pytest.raises(ValueError, match="At least one record ID"):
            batch_delete_records(api, "app123", "Table", "   ")

    def test_single_record_id(self) -> None:
        """Test deleting a single record ID."""
        from unittest.mock import MagicMock

        from batch import batch_delete_records

        api = MagicMock()
        table = MagicMock()
        api.base.return_value.table.return_value = table
        table.batch_delete.return_value = ["recXXX"]

        result = batch_delete_records(api, "app123", "Table", "recXXX")

        assert result == ["recXXX"]
        table.batch_delete.assert_called_once_with(["recXXX"])

    def test_multiple_record_ids(self) -> None:
        """Test deleting multiple record IDs."""
        from unittest.mock import MagicMock

        from batch import batch_delete_records

        api = MagicMock()
        table = MagicMock()
        api.base.return_value.table.return_value = table
        table.batch_delete.return_value = ["recXXX", "recYYY", "recZZZ"]

        result = batch_delete_records(api, "app123", "Table", "recXXX,recYYY,recZZZ")

        assert result == ["recXXX", "recYYY", "recZZZ"]
        table.batch_delete.assert_called_once_with(["recXXX", "recYYY", "recZZZ"])

    def test_record_ids_with_whitespace(self) -> None:
        """Test that whitespace around IDs is trimmed."""
        from unittest.mock import MagicMock

        from batch import batch_delete_records

        api = MagicMock()
        table = MagicMock()
        api.base.return_value.table.return_value = table
        table.batch_delete.return_value = ["recXXX", "recYYY"]

        result = batch_delete_records(api, "app123", "Table", " recXXX , recYYY ")

        assert result == ["recXXX", "recYYY"]
        table.batch_delete.assert_called_once_with(["recXXX", "recYYY"])


@pytest.mark.integration
class TestBatchIntegration:
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

    def test_batch_create_five_records(self, run_script, api, test_base_id: str | None) -> None:
        """Test batch creating 5 records and verifying all exist."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatch_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Index", "type": "number", "options": {"precision": 0}},
                ],
            )
            created_table_id = new_table.id

            # Create 5 records using batch CLI with --json flag
            records = [
                {"Name": f"Record {i}", "Index": i}
                for i in range(1, 6)
            ]
            result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(records),
                    "--json",
                ],
            )

            assert result.returncode == 0, f"Batch create failed: {result.stderr}"

            # Parse JSON output
            create_results = json.loads(result.stdout)
            assert isinstance(create_results, list), "Response should be a list"
            assert len(create_results) == 5, "Should have created 5 records"

            # Verify each record has expected structure
            created_ids = []
            for i, record in enumerate(create_results):
                assert "id" in record, "Each record should have an ID"
                assert record["id"].startswith("rec"), "Record ID should start with 'rec'"
                assert "fields" in record, "Each record should have fields"
                created_ids.append(record["id"])

            # Verify all records exist in Airtable
            table = base.table(table_name)
            all_records = table.all()
            fetched_ids = [r["id"] for r in all_records]

            for created_id in created_ids:
                assert created_id in fetched_ids, f"Record {created_id} should exist"

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

    def test_batch_create_human_readable_output(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test batch creating records without --json shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatchHuman_{uuid.uuid4().hex[:8]}"
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

            # Create records using batch CLI without --json flag
            records = [{"Title": "First"}, {"Title": "Second"}]
            result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(records),
                ],
            )

            assert result.returncode == 0, f"Batch create failed: {result.stderr}"

            # Verify human-readable output
            assert "Created 2 record(s):" in result.stdout
            # Should show record IDs
            assert "rec" in result.stdout

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

    def test_batch_update_records(self, run_script, api, test_base_id: str | None) -> None:
        """Test batch creating records, updating them, and verifying changes."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatchUpdate_{uuid.uuid4().hex[:8]}"
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

            # Step 1: Create 3 records using batch create
            create_records = [
                {"Name": "Record A", "Status": "draft"},
                {"Name": "Record B", "Status": "draft"},
                {"Name": "Record C", "Status": "draft"},
            ]
            create_result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(create_records),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, f"Batch create failed: {create_result.stderr}"
            created = json.loads(create_result.stdout)
            assert len(created) == 3

            # Step 2: Update all 3 records to change Status to "published"
            update_records = [
                {"id": created[0]["id"], "fields": {"Status": "published"}},
                {"id": created[1]["id"], "fields": {"Status": "published"}},
                {"id": created[2]["id"], "fields": {"Status": "published"}},
            ]
            update_result = run_script(
                "batch.py",
                [
                    "update",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(update_records),
                    "--json",
                ],
            )

            assert update_result.returncode == 0, f"Batch update failed: {update_result.stderr}"
            updated = json.loads(update_result.stdout)
            assert len(updated) == 3

            # Verify the updated records have the correct IDs
            updated_ids = [r["id"] for r in updated]
            for created_rec in created:
                assert created_rec["id"] in updated_ids

            # Step 3: Verify changes by fetching from Airtable
            table = base.table(table_name)
            all_records = table.all()
            assert len(all_records) == 3

            for record in all_records:
                assert record["fields"]["Status"] == "published", (
                    f"Record {record['id']} should have Status='published'"
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

    def test_batch_update_human_readable_output(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test batch updating records without --json shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatchUpdateHuman_{uuid.uuid4().hex[:8]}"
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

            # Create records first
            create_records = [{"Title": "Original"}]
            create_result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(create_records),
                    "--json",
                ],
            )

            assert create_result.returncode == 0
            created = json.loads(create_result.stdout)

            # Update the record without --json flag
            update_records = [{"id": created[0]["id"], "fields": {"Title": "Updated"}}]
            update_result = run_script(
                "batch.py",
                [
                    "update",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(update_records),
                ],
            )

            assert update_result.returncode == 0, f"Batch update failed: {update_result.stderr}"

            # Verify human-readable output
            assert "Updated 1 record(s):" in update_result.stdout
            # Should show record ID
            assert created[0]["id"] in update_result.stdout

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

    def test_batch_upsert_records(self, run_script, api, test_base_id: str | None) -> None:
        """Test batch upsert: create records, upsert with some new and some existing."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatchUpsert_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Email", "type": "singleLineText"},
                    {"name": "Name", "type": "singleLineText"},
                    {"name": "Status", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Step 1: Create 2 initial records using batch create
            create_records = [
                {"Email": "alice@example.com", "Name": "Alice", "Status": "active"},
                {"Email": "bob@example.com", "Name": "Bob", "Status": "active"},
            ]
            create_result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(create_records),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, f"Batch create failed: {create_result.stderr}"
            created = json.loads(create_result.stdout)
            assert len(created) == 2

            # Step 2: Upsert with 3 records: 1 update (Alice), 1 new (Carol), and 1 update (Bob)
            upsert_records = [
                {"Email": "alice@example.com", "Name": "Alice Updated", "Status": "inactive"},
                {"Email": "carol@example.com", "Name": "Carol", "Status": "active"},
                {"Email": "bob@example.com", "Name": "Bob Updated", "Status": "inactive"},
            ]
            upsert_result = run_script(
                "batch.py",
                [
                    "upsert",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(upsert_records),
                    "--key-fields",
                    "Email",
                    "--json",
                ],
            )

            assert upsert_result.returncode == 0, f"Batch upsert failed: {upsert_result.stderr}"
            upserted = json.loads(upsert_result.stdout)

            # Verify the response structure
            assert "created" in upserted
            assert "updated" in upserted
            assert "records" in upserted

            # Verify counts: 1 created (Carol), 2 updated (Alice, Bob)
            assert len(upserted["created"]) == 1, f"Expected 1 created, got {len(upserted['created'])}"
            assert len(upserted["updated"]) == 2, f"Expected 2 updated, got {len(upserted['updated'])}"
            assert len(upserted["records"]) == 3

            # Step 3: Verify the data in Airtable
            table = base.table(table_name)
            all_records = table.all()
            assert len(all_records) == 3, "Should have 3 records total"

            # Build a lookup by email
            records_by_email = {r["fields"]["Email"]: r for r in all_records}

            # Verify Alice was updated
            alice = records_by_email["alice@example.com"]
            assert alice["fields"]["Name"] == "Alice Updated"
            assert alice["fields"]["Status"] == "inactive"

            # Verify Bob was updated
            bob = records_by_email["bob@example.com"]
            assert bob["fields"]["Name"] == "Bob Updated"
            assert bob["fields"]["Status"] == "inactive"

            # Verify Carol was created
            assert "carol@example.com" in records_by_email
            carol = records_by_email["carol@example.com"]
            assert carol["fields"]["Name"] == "Carol"
            assert carol["fields"]["Status"] == "active"

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

    def test_batch_upsert_human_readable_output(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test batch upsert without --json shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatchUpsertHuman_{uuid.uuid4().hex[:8]}"
        created_table_id = None

        try:
            # Create a test table first
            base = api.base(test_base_id)
            new_table = base.create_table(
                name=table_name,
                fields=[
                    {"name": "Email", "type": "singleLineText"},
                    {"name": "Name", "type": "singleLineText"},
                ],
            )
            created_table_id = new_table.id

            # Create one initial record
            create_records = [{"Email": "existing@example.com", "Name": "Existing"}]
            create_result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(create_records),
                    "--json",
                ],
            )

            assert create_result.returncode == 0

            # Upsert: 1 existing (update) + 1 new (create), without --json flag
            upsert_records = [
                {"Email": "existing@example.com", "Name": "Existing Updated"},
                {"Email": "new@example.com", "Name": "New Person"},
            ]
            upsert_result = run_script(
                "batch.py",
                [
                    "upsert",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(upsert_records),
                    "--key-fields",
                    "Email",
                ],
            )

            assert upsert_result.returncode == 0, f"Batch upsert failed: {upsert_result.stderr}"

            # Verify human-readable output
            assert "Upserted 2 record(s):" in upsert_result.stdout
            assert "Created: 1" in upsert_result.stdout
            assert "Updated: 1" in upsert_result.stdout
            assert "Created record IDs:" in upsert_result.stdout
            assert "Updated record IDs:" in upsert_result.stdout

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

    def test_batch_delete_records(self, run_script, api, test_base_id: str | None) -> None:
        """Test batch creating records, deleting them, and verifying removal."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatchDelete_{uuid.uuid4().hex[:8]}"
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

            # Step 1: Create 3 records using batch create
            create_records = [
                {"Name": "Record A"},
                {"Name": "Record B"},
                {"Name": "Record C"},
            ]
            create_result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(create_records),
                    "--json",
                ],
            )

            assert create_result.returncode == 0, f"Batch create failed: {create_result.stderr}"
            created = json.loads(create_result.stdout)
            assert len(created) == 3
            created_ids = [r["id"] for r in created]

            # Step 2: Delete all 3 records using batch delete
            record_ids_str = ",".join(created_ids)
            delete_result = run_script(
                "batch.py",
                [
                    "delete",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-ids",
                    record_ids_str,
                    "--json",
                ],
            )

            assert delete_result.returncode == 0, f"Batch delete failed: {delete_result.stderr}"
            deleted = json.loads(delete_result.stdout)
            assert len(deleted) == 3

            # Verify the deleted record IDs match
            deleted_ids = [r["id"] for r in deleted]
            for created_id in created_ids:
                assert created_id in deleted_ids, f"Record {created_id} should be in deleted list"

            # Step 3: Verify records no longer exist in Airtable
            table = base.table(table_name)
            all_records = table.all()
            assert len(all_records) == 0, "Table should have no records after deletion"

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

    def test_batch_delete_human_readable_output(
        self, run_script, api, test_base_id: str | None
    ) -> None:
        """Test batch deleting records without --json shows human-readable output."""
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set, skipping integration test")

        # Generate unique table name
        table_name = f"TestBatchDeleteHuman_{uuid.uuid4().hex[:8]}"
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

            # Create records first
            create_records = [{"Title": "To Delete 1"}, {"Title": "To Delete 2"}]
            create_result = run_script(
                "batch.py",
                [
                    "create",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--records",
                    json.dumps(create_records),
                    "--json",
                ],
            )

            assert create_result.returncode == 0
            created = json.loads(create_result.stdout)
            created_ids = [r["id"] for r in created]

            # Delete records without --json flag
            record_ids_str = ",".join(created_ids)
            delete_result = run_script(
                "batch.py",
                [
                    "delete",
                    "--base-id",
                    test_base_id,
                    "--table",
                    table_name,
                    "--record-ids",
                    record_ids_str,
                ],
            )

            assert delete_result.returncode == 0, f"Batch delete failed: {delete_result.stderr}"

            # Verify human-readable output
            assert "Deleted 2 record(s):" in delete_result.stdout
            # Should show record IDs
            for created_id in created_ids:
                assert created_id in delete_result.stdout

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
