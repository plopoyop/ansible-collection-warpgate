"""Tests for warpgate_user_admin_role module main()."""

from unittest.mock import MagicMock, patch

import warpgate_user_admin_role
from warpgate_client.admin_role import AdminRole


def _base_params(**overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        user_id="u1",
        admin_role="ar1",
        state="absent",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    with patch("warpgate_user_admin_role.AnsibleModule") as mock_cls:
        mod = MagicMock()
        mod.params = params
        mod.check_mode = check_mode
        mock_cls.return_value = mod

        result = {}

        def capture(**kwargs):
            result.update(kwargs)
            raise SystemExit

        mod.exit_json = MagicMock(side_effect=capture)
        mod.fail_json = MagicMock(side_effect=capture)

        with (
            patch("warpgate_user_admin_role.WarpgateClient"),
            patch(
                "warpgate_user_admin_role.resolve_admin_role_id",
                return_value="ar1",
            ),
        ):
            try:
                warpgate_user_admin_role.main()
            except SystemExit:
                pass

        return result, mod


class TestUserAdminRoleAbsent:
    def test_unknown_user_fails(self):
        with (
            patch("warpgate_user_admin_role.get_user_admin_roles", return_value=[]),
            patch("warpgate_user_admin_role.get_user", return_value=None),
            patch("warpgate_user_admin_role.delete_user_admin_role") as mock_del,
        ):
            result, mod = _run_module(_base_params())
        mock_del.assert_not_called()
        assert "not found" in result["msg"]

    def test_role_id_match_ignores_case(self):
        with (
            patch(
                "warpgate_user_admin_role.get_user_admin_roles",
                return_value=[AdminRole(id="AR1", name="auditor")],
            ),
            patch("warpgate_user_admin_role.get_user", return_value=None),
            patch("warpgate_user_admin_role.delete_user_admin_role") as mock_del,
        ):
            result, mod = _run_module(_base_params())
        mock_del.assert_called_once()
        assert result["changed"] is True
