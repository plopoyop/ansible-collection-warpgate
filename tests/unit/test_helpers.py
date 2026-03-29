"""Tests for resolve_role_ids helper."""

from unittest.mock import patch

import pytest
from warpgate_client.client import WarpgateAPIError
from warpgate_client.helpers import resolve_role_ids
from warpgate_client.role import Role


class TestResolveRoleIds:
    def test_empty_list(self, mock_client):
        assert resolve_role_ids(mock_client, []) == []

    def test_resolve_by_name(self, mock_client):
        roles = [
            Role(id="id-dev", name="developers"),
            Role(id="id-ops", name="ops"),
        ]
        with patch("warpgate_client.helpers.get_roles", return_value=roles):
            result = resolve_role_ids(mock_client, ["developers"])
        assert result == ["id-dev"]

    def test_resolve_multiple_names(self, mock_client):
        roles = [
            Role(id="id-dev", name="developers"),
            Role(id="id-ops", name="ops"),
        ]
        with patch("warpgate_client.helpers.get_roles", return_value=roles):
            result = resolve_role_ids(mock_client, ["developers", "ops"])
        assert set(result) == {"id-dev", "id-ops"}

    def test_resolve_by_uuid(self, mock_client):
        uuid = "12345678-1234-1234-1234-123456789abc"
        role = Role(id=uuid, name="some-role")
        with patch("warpgate_client.helpers.get_role", return_value=role):
            result = resolve_role_ids(mock_client, [uuid])
        assert result == [uuid]

    def test_uuid_fallback_to_name_lookup(self, mock_client):
        """If UUID lookup returns None, fall back to name search."""
        uuid = "12345678-1234-1234-1234-123456789abc"
        roles = [Role(id="actual-id", name=uuid)]
        with (
            patch("warpgate_client.helpers.get_role", return_value=None),
            patch("warpgate_client.helpers.get_roles", return_value=roles),
        ):
            result = resolve_role_ids(mock_client, [uuid])
        assert result == ["actual-id"]

    def test_unknown_name_raises(self, mock_client):
        roles = [Role(id="id-dev", name="developers")]
        with patch("warpgate_client.helpers.get_roles", return_value=roles):
            with pytest.raises(ValueError, match="not found"):
                resolve_role_ids(mock_client, ["nonexistent"])

    def test_get_roles_called_once_for_multiple_names(self, mock_client):
        roles = [
            Role(id="id-dev", name="developers"),
            Role(id="id-ops", name="ops"),
        ]
        with patch("warpgate_client.helpers.get_roles", return_value=roles) as mock_get:
            resolve_role_ids(mock_client, ["developers", "ops"])
        mock_get.assert_called_once()

    def test_uuid_api_error_falls_back_to_name(self, mock_client):
        """If UUID lookup raises an API error, fall back to name resolution."""
        uuid = "12345678-1234-1234-1234-123456789abc"
        roles = [Role(id="real-id", name=uuid)]
        with (
            patch(
                "warpgate_client.helpers.get_role",
                side_effect=WarpgateAPIError(500, "error"),
            ),
            patch("warpgate_client.helpers.get_roles", return_value=roles),
        ):
            result = resolve_role_ids(mock_client, [uuid])
        assert result == ["real-id"]
