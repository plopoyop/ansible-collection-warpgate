"""Tests for warpgate_user_role module."""

from unittest.mock import patch, MagicMock


import warpgate_user_role  # noqa: E402
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
        user_id="u1",
        role_id="r1",
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    with patch("warpgate_user_role.AnsibleModule") as mock_cls:
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

        with patch("warpgate_user_role.WarpgateClient"):
            try:
                warpgate_user_role.main()
            except SystemExit:
                pass

        return result, mod


# ---------------------------------------------------------------------------
# Assign role
# ---------------------------------------------------------------------------


class TestUserRoleAssign:
    def test_assign_role_not_yet_assigned(self):
        params = _base_params()
        with (
            patch("warpgate_user_role.get_user_roles", return_value=[]),
            patch("warpgate_user_role.add_user_role") as mock_add,
        ):
            result, mod = _run_module(params)
        mock_add.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["after"]["roles"] == ["r1"]
        assert result["diff"]["before"]["roles"] == []

    def test_assign_role_already_assigned_is_noop(self):
        existing = [Role(id="r1", name="dev")]
        params = _base_params()
        with patch("warpgate_user_role.get_user_roles", return_value=existing):
            result, mod = _run_module(params)
        assert result["changed"] is False
        assert "diff" not in result

    def test_assign_check_mode(self):
        params = _base_params()
        with (
            patch("warpgate_user_role.get_user_roles", return_value=[]),
            patch("warpgate_user_role.add_user_role") as mock_add,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_add.assert_not_called()
        assert result["changed"] is True


# ---------------------------------------------------------------------------
# Remove role
# ---------------------------------------------------------------------------


class TestUserRoleRemove:
    def test_remove_assigned_role(self):
        existing = [Role(id="r1", name="dev"), Role(id="r2", name="ops")]
        params = _base_params(state="absent")
        with (
            patch("warpgate_user_role.get_user_roles", return_value=existing),
            patch("warpgate_user_role.delete_user_role") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert "r1" not in result["diff"]["after"]["roles"]

    def test_remove_unassigned_role_is_noop(self):
        existing = [Role(id="r2", name="ops")]
        params = _base_params(state="absent")
        with patch("warpgate_user_role.get_user_roles", return_value=existing):
            result, mod = _run_module(params)
        assert result["changed"] is False

    def test_remove_check_mode(self):
        existing = [Role(id="r1", name="dev")]
        params = _base_params(state="absent")
        with (
            patch("warpgate_user_role.get_user_roles", return_value=existing),
            patch("warpgate_user_role.delete_user_role") as mock_del,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert result["changed"] is True
