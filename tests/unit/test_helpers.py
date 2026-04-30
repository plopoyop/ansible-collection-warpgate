"""Tests for resolve_role_ids helper."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from warpgate_client.client import WarpgateAPIError
from warpgate_client.helpers import (
    find_by_exact_name,
    find_id_by_exact_name,
    resolve_role_ids,
)
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


class TestFindByExactName:
    """The search-then-list-all fallback used to look up entities by name.

    Reproduces the original bug: Warpgate's `?search=` filter returns nothing
    for names containing spaces, which previously made the modules try to
    create an entity that already existed → 409 'Name already exists'.
    """

    def _items(self, *names):
        return [SimpleNamespace(id=f"id-{n}", name=n) for n in names]

    def test_search_hit_returns_item(self, mock_client):
        list_fn = MagicMock(return_value=self._items("alpha", "beta"))
        item = find_by_exact_name(list_fn, mock_client, "alpha")
        assert item is not None
        assert item.id == "id-alpha"
        list_fn.assert_called_once_with(mock_client, search="alpha")

    def test_search_miss_falls_back_to_full_list(self, mock_client):
        """The bug case: search returns nothing, full list returns the match."""
        list_fn = MagicMock(
            side_effect=[[], self._items("One Connect Dev", "ifconfig")]
        )
        item = find_by_exact_name(list_fn, mock_client, "One Connect Dev")
        assert item is not None
        assert item.id == "id-One Connect Dev"
        assert list_fn.call_count == 2
        list_fn.assert_any_call(mock_client, search="One Connect Dev")
        list_fn.assert_any_call(mock_client)

    def test_search_returns_partial_match_no_exact(self, mock_client):
        """Search may return tokenized substrings — only exact name wins."""
        list_fn = MagicMock(
            side_effect=[
                self._items("One"),
                self._items("One", "One Connect Dev"),
            ]
        )
        item = find_by_exact_name(list_fn, mock_client, "One Connect Dev")
        assert item is not None
        assert item.id == "id-One Connect Dev"

    def test_no_match_anywhere_returns_none(self, mock_client):
        list_fn = MagicMock(return_value=self._items("alpha"))
        assert find_by_exact_name(list_fn, mock_client, "missing") is None

    def test_username_attribute_supported(self, mock_client):
        """Users expose `username` instead of `name`."""
        users = [
            SimpleNamespace(id="u1", username="bob"),
            SimpleNamespace(id="u2", username="alice"),
        ]
        list_fn = MagicMock(return_value=users)
        item = find_by_exact_name(list_fn, mock_client, "alice")
        assert item is not None
        assert item.id == "u2"

    def test_search_api_error_falls_back_to_full_list(self, mock_client):
        list_fn = MagicMock(
            side_effect=[WarpgateAPIError(500, "boom"), self._items("alpha")]
        )
        item = find_by_exact_name(list_fn, mock_client, "alpha")
        assert item is not None
        assert item.id == "id-alpha"

    def test_full_list_api_error_returns_none(self, mock_client):
        list_fn = MagicMock(side_effect=WarpgateAPIError(500, "boom"))
        assert find_by_exact_name(list_fn, mock_client, "alpha") is None


class TestFindIdByExactName:
    def test_returns_id_when_found(self, mock_client):
        list_fn = MagicMock(return_value=[SimpleNamespace(id="42", name="alpha")])
        assert find_id_by_exact_name(list_fn, mock_client, "alpha") == "42"

    def test_returns_none_when_missing(self, mock_client):
        list_fn = MagicMock(return_value=[])
        assert find_id_by_exact_name(list_fn, mock_client, "alpha") is None
