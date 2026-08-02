"""Tests for warpgate_role module."""

from unittest.mock import MagicMock, patch

import warpgate_role
from warpgate_client.role import Role

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_params(**overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        id=None,
        name="developers",
        description="Dev team",
        is_default=None,
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    """Run the module main() and capture exit_json / fail_json."""
    with patch("warpgate_role.AnsibleModule") as mock_cls:
        mod = MagicMock()
        mod.params = params
        mod.check_mode = check_mode
        mod.debug = MagicMock()
        mock_cls.return_value = mod

        result = {}

        def capture_exit(**kwargs):
            result.update(kwargs)
            raise SystemExit(0)

        def capture_fail(**kwargs):
            result.update(kwargs)
            raise SystemExit(1)

        mod.exit_json = MagicMock(side_effect=capture_exit)
        mod.fail_json = MagicMock(side_effect=capture_fail)

        with patch("warpgate_role.WarpgateClient"):
            try:
                warpgate_role.main()
            except SystemExit:
                pass

        return result, mod


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestRoleCreate:
    def test_create_new_role(self):
        new_role = Role(id="r1", name="developers", description="Dev team")
        params = _base_params()
        with (
            patch("warpgate_role.get_roles", return_value=[]),
            patch("warpgate_role.create_role", return_value=new_role),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["id"] == "r1"
        assert result["diff"]["before"] == {}
        assert result["diff"]["after"]["name"] == "developers"

    def test_create_check_mode_no_api_call(self):
        params = _base_params()
        with (
            patch("warpgate_role.get_roles", return_value=[]),
            patch("warpgate_role.create_role") as mock_create,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert result["id"] == "new-role-id"
        assert "diff" in result


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestRoleUpdate:
    def test_update_existing_role(self):
        existing = Role(id="r1", name="developers", description="Old")
        updated = Role(id="r1", name="developers", description="Dev team")
        params = _base_params()
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.get_role", return_value=existing),
            patch("warpgate_role.update_role", return_value=updated),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["diff"]["before"]["description"] == "Old"
        assert result["diff"]["after"]["description"] == "Dev team"

    def test_no_change_when_identical(self):
        existing = Role(id="r1", name="developers", description="Dev team")
        params = _base_params()
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.get_role", return_value=existing),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is False
        assert "diff" not in result

    def test_update_check_mode(self):
        existing = Role(id="r1", name="developers", description="Old")
        params = _base_params()
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.get_role", return_value=existing),
            patch("warpgate_role.update_role") as mock_update,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True


# ---------------------------------------------------------------------------
# is_default (Warpgate >= 0.24)
# ---------------------------------------------------------------------------


class TestRoleIsDefault:
    def test_create_with_is_default(self):
        new_role = Role(
            id="r1", name="developers", description="Dev team", is_default=True
        )
        params = _base_params(is_default=True)
        with (
            patch("warpgate_role.get_roles", return_value=[]),
            patch("warpgate_role.create_role", return_value=new_role) as mock_create,
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["is_default"] is True
        assert mock_create.call_args[0][3] is True

    def test_update_sets_is_default(self):
        existing = Role(
            id="r1", name="developers", description="Dev team", is_default=False
        )
        updated = Role(
            id="r1", name="developers", description="Dev team", is_default=True
        )
        params = _base_params(is_default=True)
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.get_role", return_value=existing),
            patch("warpgate_role.update_role", return_value=updated) as mock_update,
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["diff"]["before"]["is_default"] is False
        assert result["diff"]["after"]["is_default"] is True
        assert mock_update.call_args.kwargs["is_default"] is True

    def test_is_default_unset_preserves_existing(self):
        existing = Role(
            id="r1", name="developers", description="Dev team", is_default=True
        )
        params = _base_params(is_default=None)
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.get_role", return_value=existing),
            patch("warpgate_role.update_role") as mock_update,
        ):
            result, mod = _run_module(params)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["is_default"] is True

    def test_no_change_when_is_default_matches(self):
        existing = Role(
            id="r1", name="developers", description="Dev team", is_default=True
        )
        params = _base_params(is_default=True)
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.get_role", return_value=existing),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is False


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestRoleDelete:
    def test_delete_existing_role(self):
        existing = Role(id="r1", name="developers", description="Dev team")
        params = _base_params(state="absent")
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.delete_role") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once_with(mock_del.call_args[0][0], "r1")
        assert result["changed"] is True
        assert result["diff"]["before"]["name"] == "developers"
        assert result["diff"]["after"] == {}

    def test_delete_nonexistent_is_noop(self):
        params = _base_params(state="absent")
        with patch("warpgate_role.get_roles", return_value=[]):
            result, mod = _run_module(params)
        assert result["changed"] is False

    def test_delete_check_mode(self):
        existing = Role(id="r1", name="developers", description="Dev team")
        params = _base_params(state="absent")
        with (
            patch("warpgate_role.get_roles", return_value=[existing]),
            patch("warpgate_role.delete_role") as mock_del,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert result["changed"] is True
