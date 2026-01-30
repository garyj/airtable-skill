"""Tests for the webhook management script."""

import json
import os

import pytest


class TestWebhooksScript:
    """Tests for scripts/webhooks.py."""

    def test_script_exists(self, scripts_dir) -> None:
        """Verify the webhooks script exists."""
        script_path = scripts_dir / "webhooks.py"
        assert script_path.exists(), "scripts/webhooks.py should exist"

    def test_script_has_pep723_metadata(self, scripts_dir) -> None:
        """Verify script has PEP 723 inline metadata."""
        script_path = scripts_dir / "webhooks.py"
        content = script_path.read_text()
        assert "# /// script" in content, "Script should have PEP 723 header"
        assert "# dependencies = [" in content, "Script should declare dependencies"
        assert "pyairtable" in content, "Script should depend on pyairtable"
        assert "# ///" in content, "Script should have PEP 723 closing marker"

    def test_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing."""
        result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--url",
                "https://example.com",
                "--spec",
                '{"options": {"filters": {"dataTypes": ["tableData"]}}}',
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_requires_base_id_url_spec_for_create(self, run_script) -> None:
        """Verify --base-id, --url, and --spec are required for create."""
        result = run_script("webhooks.py", ["create"])

        assert result.returncode != 0
        # Should mention missing required arguments
        assert (
            "--base-id" in result.stderr
            or "--url" in result.stderr
            or "--spec" in result.stderr
        )

    def test_list_requires_base_id(self, run_script) -> None:
        """Verify --base-id is required for list."""
        result = run_script("webhooks.py", ["list"])

        assert result.returncode != 0
        assert "--base-id" in result.stderr

    def test_list_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for list."""
        result = run_script(
            "webhooks.py",
            [
                "list",
                "--base-id",
                "appXXXXX",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_get_requires_base_id_and_webhook_id(self, run_script) -> None:
        """Verify --base-id and --webhook-id are required for get."""
        result = run_script("webhooks.py", ["get"])

        assert result.returncode != 0
        assert "--base-id" in result.stderr or "--webhook-id" in result.stderr

    def test_get_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for get."""
        result = run_script(
            "webhooks.py",
            [
                "get",
                "--base-id",
                "appXXXXX",
                "--webhook-id",
                "achXXXXX",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_delete_requires_base_id_and_webhook_id(self, run_script) -> None:
        """Verify --base-id and --webhook-id are required for delete."""
        result = run_script("webhooks.py", ["delete"])

        assert result.returncode != 0
        assert "--base-id" in result.stderr or "--webhook-id" in result.stderr

    def test_delete_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for delete."""
        result = run_script(
            "webhooks.py",
            [
                "delete",
                "--base-id",
                "appXXXXX",
                "--webhook-id",
                "achXXXXX",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr

    def test_create_with_invalid_json_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --spec has invalid JSON."""
        result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--url",
                "https://example.com",
                "--spec",
                "not valid json",
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "Invalid JSON" in result.stderr

    def test_create_with_non_object_spec_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --spec is not a JSON object."""
        result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--url",
                "https://example.com",
                "--spec",
                '["array"]',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "Spec must be a JSON object" in result.stderr

    def test_create_with_missing_options_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --spec is missing 'options' key."""
        result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--url",
                "https://example.com",
                "--spec",
                '{"other": "key"}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "options" in result.stderr

    def test_create_with_missing_filters_shows_error(
        self, run_script, env_with_test_token
    ) -> None:
        """Verify error message when --spec is missing 'filters' key."""
        result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                "appXXXXX",
                "--url",
                "https://example.com",
                "--spec",
                '{"options": {}}',
            ],
            env=env_with_test_token,
        )

        assert result.returncode == 1
        assert "filters" in result.stderr


class TestListWebhooksFunction:
    """Tests for the list_webhooks function."""

    def test_list_webhooks_returns_empty_list(self, scripts_dir) -> None:
        """Test that list_webhooks returns empty list when no webhooks."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import list_webhooks

            api = Mock()
            base = Mock()
            api.base.return_value = base
            base.webhooks.return_value = []

            result = list_webhooks(api, "appXXX")

            api.base.assert_called_once_with("appXXX")
            base.webhooks.assert_called_once()
            assert result == []
        finally:
            sys.path.remove(str(scripts_dir))

    def test_list_webhooks_returns_webhook_details(self, scripts_dir) -> None:
        """Test that list_webhooks returns webhook details."""
        import sys
        from datetime import datetime
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import list_webhooks

            api = Mock()
            base = Mock()
            api.base.return_value = base

            # Mock webhook
            webhook = Mock()
            webhook.id = "achXXXXXXXXXXXXXX"
            webhook.notification_url = "https://example.com/webhook"
            webhook.expiration_time = datetime(2025, 6, 1, 12, 0, 0)
            webhook.is_hook_enabled = True

            base.webhooks.return_value = [webhook]

            result = list_webhooks(api, "appXXX")

            assert len(result) == 1
            assert result[0]["id"] == "achXXXXXXXXXXXXXX"
            assert result[0]["notification_url"] == "https://example.com/webhook"
            assert result[0]["expiration_time"] == "2025-06-01T12:00:00"
            assert result[0]["is_active"] is True
        finally:
            sys.path.remove(str(scripts_dir))

    def test_list_webhooks_handles_none_expiration(self, scripts_dir) -> None:
        """Test that list_webhooks handles None expiration time."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import list_webhooks

            api = Mock()
            base = Mock()
            api.base.return_value = base

            webhook = Mock()
            webhook.id = "achXXXXXXXXXXXXXX"
            webhook.notification_url = "https://example.com/webhook"
            webhook.expiration_time = None
            webhook.is_hook_enabled = False

            base.webhooks.return_value = [webhook]

            result = list_webhooks(api, "appXXX")

            assert len(result) == 1
            assert result[0]["expiration_time"] is None
            assert result[0]["is_active"] is False
        finally:
            sys.path.remove(str(scripts_dir))


class TestGetWebhookFunction:
    """Tests for the get_webhook function."""

    def test_get_webhook_returns_full_details(self, scripts_dir) -> None:
        """Test that get_webhook returns full webhook details."""
        import sys
        from datetime import datetime
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import get_webhook

            api = Mock()
            base = Mock()
            api.base.return_value = base

            # Create a mock WebhookSpecification
            spec = Mock()
            spec.options.filters.data_types = ["tableData"]
            spec.options.filters.record_change_scope = "tbl123"
            spec.options.filters.change_types = ["add", "update"]
            spec.options.filters.from_sources = []
            spec.options.filters.watch_data_in_field_ids = ["fld123", "fld456"]
            spec.options.filters.watch_schemas_of_field_ids = []
            spec.options.filters.source_options = None
            spec.options.includes = None

            # Mock webhook
            webhook = Mock()
            webhook.id = "achXXXXXXXXXXXXXX"
            webhook.notification_url = "https://example.com/webhook"
            webhook.is_hook_enabled = True
            webhook.are_notifications_enabled = True
            webhook.cursor_for_next_payload = 42
            webhook.expiration_time = datetime(2025, 6, 1, 12, 0, 0)
            webhook.last_successful_notification_time = datetime(2025, 5, 15, 10, 30, 0)
            webhook.specification = spec

            base.webhook.return_value = webhook

            result = get_webhook(api, "appXXX", "achXXXXXXXXXXXXXX")

            api.base.assert_called_once_with("appXXX")
            base.webhook.assert_called_once_with("achXXXXXXXXXXXXXX")

            assert result["id"] == "achXXXXXXXXXXXXXX"
            assert result["notification_url"] == "https://example.com/webhook"
            assert result["is_hook_enabled"] is True
            assert result["are_notifications_enabled"] is True
            assert result["cursor_for_next_payload"] == 42
            assert result["expiration_time"] == "2025-06-01T12:00:00"
            assert result["last_successful_notification_time"] == "2025-05-15T10:30:00"

            # Verify specification
            spec_result = result["specification"]
            assert spec_result["options"]["filters"]["dataTypes"] == ["tableData"]
            assert spec_result["options"]["filters"]["recordChangeScope"] == "tbl123"
            assert spec_result["options"]["filters"]["changeTypes"] == ["add", "update"]
            assert spec_result["options"]["filters"]["watchDataInFieldIds"] == [
                "fld123",
                "fld456",
            ]
        finally:
            sys.path.remove(str(scripts_dir))

    def test_get_webhook_handles_none_expiration(self, scripts_dir) -> None:
        """Test that get_webhook handles None expiration and notification times."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import get_webhook

            api = Mock()
            base = Mock()
            api.base.return_value = base

            spec = Mock()
            spec.options.filters.data_types = ["tableData"]
            spec.options.filters.record_change_scope = None
            spec.options.filters.change_types = []
            spec.options.filters.from_sources = []
            spec.options.filters.watch_data_in_field_ids = []
            spec.options.filters.watch_schemas_of_field_ids = []
            spec.options.filters.source_options = None
            spec.options.includes = None

            webhook = Mock()
            webhook.id = "achXXXXXXXXXXXXXX"
            webhook.notification_url = "https://example.com/webhook"
            webhook.is_hook_enabled = False
            webhook.are_notifications_enabled = False
            webhook.cursor_for_next_payload = 1
            webhook.expiration_time = None
            webhook.last_successful_notification_time = None
            webhook.specification = spec

            base.webhook.return_value = webhook

            result = get_webhook(api, "appXXX", "achXXXXXXXXXXXXXX")

            assert result["expiration_time"] is None
            assert result["last_successful_notification_time"] is None
            # Specification should only have required fields
            assert "recordChangeScope" not in result["specification"]["options"]["filters"]
        finally:
            sys.path.remove(str(scripts_dir))

    def test_get_webhook_includes_specification_includes(self, scripts_dir) -> None:
        """Test that get_webhook includes specification includes when present."""
        import sys
        from datetime import datetime
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import get_webhook

            api = Mock()
            base = Mock()
            api.base.return_value = base

            spec = Mock()
            spec.options.filters.data_types = ["tableData"]
            spec.options.filters.record_change_scope = None
            spec.options.filters.change_types = []
            spec.options.filters.from_sources = []
            spec.options.filters.watch_data_in_field_ids = []
            spec.options.filters.watch_schemas_of_field_ids = []
            spec.options.filters.source_options = None

            # Add includes
            includes = Mock()
            includes.include_cell_values_in_field_ids = "all"
            includes.include_previous_cell_values = True
            includes.include_previous_field_definitions = False
            spec.options.includes = includes

            webhook = Mock()
            webhook.id = "achXXXXXXXXXXXXXX"
            webhook.notification_url = "https://example.com/webhook"
            webhook.is_hook_enabled = True
            webhook.are_notifications_enabled = True
            webhook.cursor_for_next_payload = 1
            webhook.expiration_time = datetime(2025, 6, 1, 12, 0, 0)
            webhook.last_successful_notification_time = None
            webhook.specification = spec

            base.webhook.return_value = webhook

            result = get_webhook(api, "appXXX", "achXXXXXXXXXXXXXX")

            assert "includes" in result["specification"]["options"]
            includes_result = result["specification"]["options"]["includes"]
            assert includes_result["includeCellValuesInFieldIds"] == "all"
            assert includes_result["includePreviousCellValues"] is True
        finally:
            sys.path.remove(str(scripts_dir))


class TestCreateWebhookFunction:
    """Tests for the create_webhook function."""

    def test_create_webhook_validates_json(self, scripts_dir) -> None:
        """Test that create_webhook validates JSON input."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import create_webhook

            api = Mock()

            with pytest.raises(ValueError, match="Invalid JSON"):
                create_webhook(api, "appXXX", "https://example.com", "not json")
        finally:
            sys.path.remove(str(scripts_dir))

    def test_create_webhook_validates_object(self, scripts_dir) -> None:
        """Test that create_webhook requires spec to be an object."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import create_webhook

            api = Mock()

            with pytest.raises(ValueError, match="must be a JSON object"):
                create_webhook(api, "appXXX", "https://example.com", '["array"]')
        finally:
            sys.path.remove(str(scripts_dir))

    def test_create_webhook_validates_options_key(self, scripts_dir) -> None:
        """Test that create_webhook requires 'options' key."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import create_webhook

            api = Mock()

            with pytest.raises(ValueError, match="options"):
                create_webhook(api, "appXXX", "https://example.com", '{"other": "key"}')
        finally:
            sys.path.remove(str(scripts_dir))

    def test_create_webhook_validates_filters_key(self, scripts_dir) -> None:
        """Test that create_webhook requires 'filters' key in options."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import create_webhook

            api = Mock()

            with pytest.raises(ValueError, match="filters"):
                create_webhook(api, "appXXX", "https://example.com", '{"options": {}}')
        finally:
            sys.path.remove(str(scripts_dir))

    def test_create_webhook_calls_api(self, scripts_dir) -> None:
        """Test that create_webhook calls the API correctly."""
        import sys
        from datetime import datetime
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import create_webhook

            api = Mock()
            base = Mock()
            api.base.return_value = base

            # Mock the response
            mock_response = Mock()
            mock_response.id = "achXXXXXXXXXXXXXX"
            mock_response.mac_secret_base64 = "c2VjcmV0"
            mock_response.expiration_time = datetime(2025, 6, 1, 12, 0, 0)
            base.add_webhook.return_value = mock_response

            spec_json = '{"options": {"filters": {"dataTypes": ["tableData"]}}}'
            result = create_webhook(api, "appXXX", "https://example.com/webhook", spec_json)

            api.base.assert_called_once_with("appXXX")
            base.add_webhook.assert_called_once_with(
                "https://example.com/webhook",
                {"options": {"filters": {"dataTypes": ["tableData"]}}},
            )

            assert result["id"] == "achXXXXXXXXXXXXXX"
            assert result["mac_secret_base64"] == "c2VjcmV0"
            assert result["expiration_time"] == "2025-06-01T12:00:00"
        finally:
            sys.path.remove(str(scripts_dir))


class TestDeleteWebhookFunction:
    """Tests for the delete_webhook function."""

    def test_delete_webhook_calls_api(self, scripts_dir) -> None:
        """Test that delete_webhook calls the API correctly."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import delete_webhook

            api = Mock()
            base = Mock()
            webhook = Mock()
            api.base.return_value = base
            base.webhook.return_value = webhook

            delete_webhook(api, "appXXX", "achXXXXXXXXXXXXXX")

            api.base.assert_called_once_with("appXXX")
            base.webhook.assert_called_once_with("achXXXXXXXXXXXXXX")
            webhook.delete.assert_called_once()
        finally:
            sys.path.remove(str(scripts_dir))


class TestGetWebhookPayloadsFunction:
    """Tests for the get_webhook_payloads function."""

    def test_get_webhook_payloads_returns_empty_when_no_payloads(self, scripts_dir) -> None:
        """Test that get_webhook_payloads returns empty list when no payloads."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import get_webhook_payloads

            api = Mock()
            base = Mock()
            webhook = Mock()
            api.base.return_value = base
            base.webhook.return_value = webhook
            webhook.payloads.return_value = iter([])

            result = get_webhook_payloads(api, "appXXX", "achXXXXXXXXXXXXXX")

            api.base.assert_called_once_with("appXXX")
            base.webhook.assert_called_once_with("achXXXXXXXXXXXXXX")
            webhook.payloads.assert_called_once_with(cursor=1)
            assert result["payloads"] == []
            assert result["cursor"] is None
            assert result["might_have_more"] is False
        finally:
            sys.path.remove(str(scripts_dir))

    def test_get_webhook_payloads_with_cursor(self, scripts_dir) -> None:
        """Test that get_webhook_payloads passes cursor to API."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import get_webhook_payloads

            api = Mock()
            base = Mock()
            webhook = Mock()
            api.base.return_value = base
            base.webhook.return_value = webhook
            webhook.payloads.return_value = iter([])

            get_webhook_payloads(api, "appXXX", "achXXXXXXXXXXXXXX", cursor=42)

            webhook.payloads.assert_called_once_with(cursor=42)
        finally:
            sys.path.remove(str(scripts_dir))

    def test_get_webhook_payloads_returns_payload_data(self, scripts_dir) -> None:
        """Test that get_webhook_payloads returns payload data correctly."""
        import sys
        from datetime import datetime
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import get_webhook_payloads

            api = Mock()
            base = Mock()
            webhook = Mock()
            api.base.return_value = base
            base.webhook.return_value = webhook

            # Mock a payload
            payload = Mock()
            payload.cursor = 5
            payload.timestamp = datetime(2025, 5, 15, 10, 30, 0)
            payload.action_metadata = Mock()
            payload.action_metadata.source = "client"
            payload.action_metadata.source_metadata = {"viewId": "viwXXX"}
            payload.payloads = [{"tableId": "tblXXX", "recordId": "recXXX"}]
            payload.might_have_more = True

            webhook.payloads.return_value = iter([payload])

            result = get_webhook_payloads(api, "appXXX", "achXXXXXXXXXXXXXX")

            assert len(result["payloads"]) == 1
            assert result["payloads"][0]["cursor"] == 5
            assert result["payloads"][0]["timestamp"] == "2025-05-15T10:30:00"
            assert result["payloads"][0]["action_metadata"]["source"] == "client"
            assert result["payloads"][0]["changes"] == [
                {"tableId": "tblXXX", "recordId": "recXXX"}
            ]
            assert result["cursor"] == 5
            assert result["might_have_more"] is True
        finally:
            sys.path.remove(str(scripts_dir))

    def test_get_webhook_payloads_handles_none_timestamp(self, scripts_dir) -> None:
        """Test that get_webhook_payloads handles None timestamp."""
        import sys
        from unittest.mock import Mock

        sys.path.insert(0, str(scripts_dir))
        try:
            from webhooks import get_webhook_payloads

            api = Mock()
            base = Mock()
            webhook = Mock()
            api.base.return_value = base
            base.webhook.return_value = webhook

            payload = Mock()
            payload.cursor = 3
            payload.timestamp = None
            payload.action_metadata = None
            payload.payloads = None
            payload.might_have_more = False

            webhook.payloads.return_value = iter([payload])

            result = get_webhook_payloads(api, "appXXX", "achXXXXXXXXXXXXXX")

            assert result["payloads"][0]["timestamp"] is None
            assert "action_metadata" not in result["payloads"][0]
            assert "changes" not in result["payloads"][0]
        finally:
            sys.path.remove(str(scripts_dir))


class TestPayloadsSubcommand:
    """Tests for the payloads subcommand."""

    def test_payloads_requires_base_id_and_webhook_id(self, run_script) -> None:
        """Verify --base-id and --webhook-id are required for payloads."""
        result = run_script("webhooks.py", ["payloads"])

        assert result.returncode != 0
        assert "--base-id" in result.stderr or "--webhook-id" in result.stderr

    def test_payloads_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing for payloads."""
        result = run_script(
            "webhooks.py",
            [
                "payloads",
                "--base-id",
                "appXXXXX",
                "--webhook-id",
                "achXXXXX",
            ],
            env=env_without_token,
        )

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr


@pytest.mark.integration
class TestWebhooksIntegration:
    """Integration tests that require a real Airtable token and test base."""

    @pytest.fixture
    def has_token(self) -> bool:
        """Check if we have a token for integration tests."""
        return bool(os.environ.get("AIRTABLE_API_TOKEN"))

    @pytest.fixture
    def test_base_id(self) -> str | None:
        """Get the test base ID."""
        return os.environ.get("AIRTABLE_TEST_BASE_ID")

    def test_create_webhook_with_json_output(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test creating a webhook with JSON output."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        spec = json.dumps({"options": {"filters": {"dataTypes": ["tableData"]}}})

        result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
                "--json",
            ],
        )

        assert result.returncode == 0, f"Error: {result.stderr}"

        data = json.loads(result.stdout)
        assert "id" in data
        assert data["id"].startswith("ach")
        assert "mac_secret_base64" in data
        assert "expiration_time" in data

        # Clean up - delete the webhook
        webhook_id = data["id"]
        self._cleanup_webhook(test_base_id, webhook_id)

    def test_create_webhook_human_readable_output(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test creating a webhook with human-readable output."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        spec = json.dumps({"options": {"filters": {"dataTypes": ["tableData"]}}})

        result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
            ],
        )

        assert result.returncode == 0, f"Error: {result.stderr}"
        assert "Created webhook:" in result.stdout
        assert "Expiration:" in result.stdout
        assert "MAC Secret" not in result.stdout, "MAC secret must not appear in stdout"
        assert "MAC Secret" in result.stderr
        assert "Save this secret" in result.stderr

        # Extract webhook ID from output to clean up
        for line in result.stdout.split("\n"):
            if "Created webhook:" in line:
                webhook_id = line.split(":")[-1].strip()
                self._cleanup_webhook(test_base_id, webhook_id)
                break

    def test_webhook_lifecycle(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test creating a webhook, verifying it exists, and cleaning up."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        spec = json.dumps({"options": {"filters": {"dataTypes": ["tableData"]}}})

        # Create webhook
        create_result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
                "--json",
            ],
        )

        assert create_result.returncode == 0, f"Create error: {create_result.stderr}"
        data = json.loads(create_result.stdout)
        webhook_id = data["id"]

        # Verify webhook exists using pyairtable directly
        from pyairtable import Api

        api = Api(os.environ["AIRTABLE_API_TOKEN"])
        base = api.base(test_base_id)
        webhooks = base.webhooks()
        webhook_ids = [w.id for w in webhooks]
        assert webhook_id in webhook_ids, "Created webhook should be in list"

        # Clean up
        self._cleanup_webhook(test_base_id, webhook_id)

        # Verify webhook is deleted
        webhooks_after = base.webhooks()
        webhook_ids_after = [w.id for w in webhooks_after]
        assert webhook_id not in webhook_ids_after, "Webhook should be deleted"

    def test_list_webhooks_via_script(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test creating a webhook, listing via script, verifying it appears."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        spec = json.dumps({"options": {"filters": {"dataTypes": ["tableData"]}}})

        # Create webhook
        create_result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
                "--json",
            ],
        )

        assert create_result.returncode == 0, f"Create error: {create_result.stderr}"
        create_data = json.loads(create_result.stdout)
        webhook_id = create_data["id"]

        try:
            # List webhooks using script with --json flag
            list_result = run_script(
                "webhooks.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                    "--json",
                ],
            )

            assert list_result.returncode == 0, f"List error: {list_result.stderr}"

            webhooks = json.loads(list_result.stdout)
            webhook_ids = [w["id"] for w in webhooks]
            assert webhook_id in webhook_ids, "Created webhook should appear in list"

            # Find our webhook and verify fields
            our_webhook = next(w for w in webhooks if w["id"] == webhook_id)
            assert our_webhook["notification_url"] == "https://example.com/webhook"
            assert "expiration_time" in our_webhook
            assert "is_active" in our_webhook

            # Also test human-readable output
            list_human_result = run_script(
                "webhooks.py",
                [
                    "list",
                    "--base-id",
                    test_base_id,
                ],
            )

            assert list_human_result.returncode == 0
            assert webhook_id in list_human_result.stdout
            assert "Notification URL:" in list_human_result.stdout
            assert "Expiration Time:" in list_human_result.stdout
            assert "Is Active:" in list_human_result.stdout
        finally:
            # Clean up
            self._cleanup_webhook(test_base_id, webhook_id)

    def test_get_webhook_details(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test creating a webhook, getting its details via script, verifying spec."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        # Create webhook with specific spec
        spec = json.dumps(
            {
                "options": {
                    "filters": {
                        "dataTypes": ["tableData"],
                        "changeTypes": ["add", "update"],
                    }
                }
            }
        )

        # Create webhook
        create_result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
                "--json",
            ],
        )

        assert create_result.returncode == 0, f"Create error: {create_result.stderr}"
        create_data = json.loads(create_result.stdout)
        webhook_id = create_data["id"]

        try:
            # Get webhook details with --json flag
            get_result = run_script(
                "webhooks.py",
                [
                    "get",
                    "--base-id",
                    test_base_id,
                    "--webhook-id",
                    webhook_id,
                    "--json",
                ],
            )

            assert get_result.returncode == 0, f"Get error: {get_result.stderr}"

            webhook_data = json.loads(get_result.stdout)
            assert webhook_data["id"] == webhook_id
            assert webhook_data["notification_url"] == "https://example.com/webhook"
            assert webhook_data["is_hook_enabled"] is True
            assert webhook_data["cursor_for_next_payload"] >= 1
            assert webhook_data["expiration_time"] is not None

            # Verify specification matches what we created
            spec_filters = webhook_data["specification"]["options"]["filters"]
            assert "tableData" in spec_filters["dataTypes"]
            assert "add" in spec_filters["changeTypes"]
            assert "update" in spec_filters["changeTypes"]

            # Also test human-readable output
            get_human_result = run_script(
                "webhooks.py",
                [
                    "get",
                    "--base-id",
                    test_base_id,
                    "--webhook-id",
                    webhook_id,
                ],
            )

            assert get_human_result.returncode == 0
            assert webhook_id in get_human_result.stdout
            assert "Notification URL:" in get_human_result.stdout
            assert "Cursor for Next Payload:" in get_human_result.stdout
            assert "Expiration Time:" in get_human_result.stdout
            assert "Specification:" in get_human_result.stdout
            assert "Data Types:" in get_human_result.stdout
            assert "Change Types:" in get_human_result.stdout

        finally:
            # Clean up
            self._cleanup_webhook(test_base_id, webhook_id)

    def test_delete_webhook_via_script(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test creating a webhook, deleting via script, verifying it's gone."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        spec = json.dumps({"options": {"filters": {"dataTypes": ["tableData"]}}})

        # Create webhook
        create_result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
                "--json",
            ],
        )

        assert create_result.returncode == 0, f"Create error: {create_result.stderr}"
        create_data = json.loads(create_result.stdout)
        webhook_id = create_data["id"]

        # Verify webhook exists
        from pyairtable import Api

        api = Api(os.environ["AIRTABLE_API_TOKEN"])
        base = api.base(test_base_id)
        webhooks = base.webhooks()
        webhook_ids = [w.id for w in webhooks]
        assert webhook_id in webhook_ids, "Created webhook should be in list"

        # Delete webhook using the script
        delete_result = run_script(
            "webhooks.py",
            [
                "delete",
                "--base-id",
                test_base_id,
                "--webhook-id",
                webhook_id,
            ],
        )

        assert delete_result.returncode == 0, f"Delete error: {delete_result.stderr}"
        assert f"Deleted webhook: {webhook_id}" in delete_result.stdout

        # Verify webhook is deleted
        webhooks_after = base.webhooks()
        webhook_ids_after = [w.id for w in webhooks_after]
        assert webhook_id not in webhook_ids_after, "Webhook should be deleted"

    def test_delete_webhook_json_output(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test deleting a webhook with --json returns structured output."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        spec = json.dumps({"options": {"filters": {"dataTypes": ["tableData"]}}})

        # Create webhook
        create_result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
                "--json",
            ],
        )

        assert create_result.returncode == 0, f"Create error: {create_result.stderr}"
        create_data = json.loads(create_result.stdout)
        webhook_id = create_data["id"]

        try:
            # Delete webhook with --json
            delete_result = run_script(
                "webhooks.py",
                [
                    "delete",
                    "--base-id",
                    test_base_id,
                    "--webhook-id",
                    webhook_id,
                    "--json",
                ],
            )

            assert (
                delete_result.returncode == 0
            ), f"Delete error: {delete_result.stderr}"
            data = json.loads(delete_result.stdout)
            assert data["id"] == webhook_id
            assert data["deleted"] is True

            # Verify webhook is actually deleted
            from pyairtable import Api

            api = Api(os.environ["AIRTABLE_API_TOKEN"])
            base = api.base(test_base_id)
            webhooks_after = base.webhooks()
            webhook_ids_after = [w.id for w in webhooks_after]
            assert webhook_id not in webhook_ids_after
        except Exception:
            # Clean up on failure
            self._cleanup_webhook(test_base_id, webhook_id)
            raise

    def test_get_webhook_payloads(
        self, run_script, has_token: bool, test_base_id: str | None
    ) -> None:
        """Test creating a webhook, making changes, and retrieving payloads."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set")
        if not test_base_id:
            pytest.skip("AIRTABLE_TEST_BASE_ID not set")

        spec = json.dumps({"options": {"filters": {"dataTypes": ["tableData"]}}})

        # Create webhook
        create_result = run_script(
            "webhooks.py",
            [
                "create",
                "--base-id",
                test_base_id,
                "--url",
                "https://example.com/webhook",
                "--spec",
                spec,
                "--json",
            ],
        )

        assert create_result.returncode == 0, f"Create error: {create_result.stderr}"
        create_data = json.loads(create_result.stdout)
        webhook_id = create_data["id"]

        try:
            # Get payloads with --json flag (should have at least one initial payload)
            payloads_result = run_script(
                "webhooks.py",
                [
                    "payloads",
                    "--base-id",
                    test_base_id,
                    "--webhook-id",
                    webhook_id,
                    "--json",
                ],
            )

            assert (
                payloads_result.returncode == 0
            ), f"Payloads error: {payloads_result.stderr}"

            payloads = json.loads(payloads_result.stdout)
            assert isinstance(payloads, list)

            # Also test human-readable output
            payloads_human_result = run_script(
                "webhooks.py",
                [
                    "payloads",
                    "--base-id",
                    test_base_id,
                    "--webhook-id",
                    webhook_id,
                ],
            )

            assert payloads_human_result.returncode == 0

            # Test with cursor if we got any payloads
            if payloads:
                first_cursor = payloads[0]["cursor"]
                cursor_result = run_script(
                    "webhooks.py",
                    [
                        "payloads",
                        "--base-id",
                        test_base_id,
                        "--webhook-id",
                        webhook_id,
                        "--cursor",
                        str(first_cursor),
                        "--json",
                    ],
                )

                assert (
                    cursor_result.returncode == 0
                ), f"Cursor error: {cursor_result.stderr}"

        finally:
            # Clean up
            self._cleanup_webhook(test_base_id, webhook_id)

    def _cleanup_webhook(self, base_id: str, webhook_id: str) -> None:
        """Delete a webhook for cleanup."""
        from pyairtable import Api

        api = Api(os.environ["AIRTABLE_API_TOKEN"])
        base = api.base(base_id)
        try:
            webhook = base.webhook(webhook_id)
            webhook.delete()
        except KeyError:
            pass  # Webhook already deleted
