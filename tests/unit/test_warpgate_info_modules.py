"""Tests for the read-only warpgate_*_info modules."""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from warpgate_client.admin_role import AdminRole
from warpgate_client.client import WarpgateAPIError
from warpgate_client.role import Role
from warpgate_client.target import Target
from warpgate_client.target_group import TargetGroup
from warpgate_client.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_params(filter_key, **overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        search=None,
        insecure=False,
        timeout=30,
    )
    params[filter_key] = None
    params.update(overrides)
    return params


def _run_module(module_name, params, check_mode=False):
    module_obj = importlib.import_module(module_name)

    with patch(f"{module_name}.AnsibleModule") as mock_cls:
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

        with patch(f"{module_name}.WarpgateClient") as mock_client_cls:
            client = mock_client_cls.return_value
            try:
                module_obj.main()
            except SystemExit:
                pass

        return result, mod, client


# ``search`` is handled server-side for these four; warpgate_admin_role_info
# filters locally and is covered separately below.
SEARCHABLE = [
    pytest.param(
        "warpgate_user_info",
        "get_users",
        "users",
        "username",
        User(id="u1", username="eugene", description="Dev"),
        "eugene",
        id="user",
    ),
    pytest.param(
        "warpgate_target_info",
        "get_targets",
        "targets",
        "name",
        Target(id="t1", name="db-prod", description="Prod DB"),
        "db-prod",
        id="target",
    ),
    pytest.param(
        "warpgate_role_info",
        "get_roles",
        "roles",
        "name",
        Role(id="r1", name="developers", description="Devs"),
        "developers",
        id="role",
    ),
    pytest.param(
        "warpgate_group_info",
        "get_target_groups",
        "target_groups",
        "name",
        TargetGroup(id="g1", name="production", description="Prod", color="Danger"),
        "production",
        id="group",
    ),
]


# ---------------------------------------------------------------------------
# Behaviour shared by every info module backed by a searchable endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_name,list_fn,return_key,filter_key,entity,entity_name", SEARCHABLE
)
class TestSearchableInfoModules:
    def test_list_all(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        params = _base_params(filter_key)
        with patch(f"{module_name}.{list_fn}", return_value=[entity]) as mock_list:
            result, _mod, _client = _run_module(module_name, params)

        assert result["changed"] is False
        assert result[return_key] == [entity.to_dict()]
        assert mock_list.call_args.kwargs["search"] == ""

    def test_search_is_forwarded_to_the_api(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        params = _base_params(filter_key, search="pro")
        with patch(f"{module_name}.{list_fn}", return_value=[entity]) as mock_list:
            result, _mod, _client = _run_module(module_name, params)

        assert mock_list.call_args.kwargs["search"] == "pro"
        assert result[return_key] == [entity.to_dict()]

    def test_exact_name_returns_single_entity(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        other = TargetGroup(id="x", name="other")
        params = _base_params(filter_key, **{filter_key: entity_name})
        with patch(f"{module_name}.{list_fn}", return_value=[other, entity]):
            result, _mod, _client = _run_module(module_name, params)

        assert result[return_key] == [entity.to_dict()]

    def test_exact_name_without_match_returns_empty_list(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        params = _base_params(filter_key, **{filter_key: "does-not-exist"})
        with patch(f"{module_name}.{list_fn}", return_value=[]):
            result, _mod, _client = _run_module(module_name, params)

        assert result["changed"] is False
        assert result[return_key] == []

    def test_check_mode_still_returns_data(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        params = _base_params(filter_key)
        with patch(f"{module_name}.{list_fn}", return_value=[entity]):
            result, _mod, _client = _run_module(module_name, params, check_mode=True)

        assert result["changed"] is False
        assert result[return_key] == [entity.to_dict()]

    def test_missing_credentials_fails(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        params = _base_params(filter_key, token=None)
        with patch(f"{module_name}.{list_fn}") as mock_list:
            result, mod, _client = _run_module(module_name, params)

        mod.fail_json.assert_called_once()
        mock_list.assert_not_called()
        assert "token" in result["msg"]

    def test_api_error_is_reported(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        error = WarpgateAPIError(403, "boom")
        with patch(f"{module_name}.{list_fn}", side_effect=error):
            result, mod, _client = _run_module(module_name, _base_params(filter_key))

        mod.fail_json.assert_called_once()
        assert result["status_code"] == 403

    def test_session_is_closed(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        with patch(f"{module_name}.{list_fn}", return_value=[entity]):
            _result, _mod, client = _run_module(module_name, _base_params(filter_key))

        client.logout.assert_called_once()

    def test_session_is_closed_on_error(
        self, module_name, list_fn, return_key, filter_key, entity, entity_name
    ):
        with patch(f"{module_name}.{list_fn}", side_effect=RuntimeError("nope")):
            _result, _mod, client = _run_module(module_name, _base_params(filter_key))

        client.logout.assert_called_once()


# ---------------------------------------------------------------------------
# warpgate_admin_role_info: the endpoint has no ?search=, filtering is local
# ---------------------------------------------------------------------------


class TestAdminRoleInfo:
    MODULE = "warpgate_admin_role_info"

    @staticmethod
    def _roles():
        return [
            AdminRole(id="a1", name="auditor", permissions={"sessions_view": True}),
            AdminRole(id="a2", name="Super Auditor"),
            AdminRole(id="a3", name="operator"),
        ]

    def test_list_all(self):
        roles = self._roles()
        with patch(f"{self.MODULE}.get_admin_roles", return_value=roles) as mock_list:
            result, _mod, _client = _run_module(self.MODULE, _base_params("name"))

        mock_list.assert_called_once()
        assert result["changed"] is False
        assert [r["name"] for r in result["admin_roles"]] == [
            "auditor",
            "Super Auditor",
            "operator",
        ]
        assert result["admin_roles"][0]["permissions"]["sessions_view"] is True
        assert result["admin_roles"][0]["permissions"]["users_delete"] is False

    def test_exact_name_filter(self):
        params = _base_params("name", name="auditor")
        with patch(f"{self.MODULE}.get_admin_roles", return_value=self._roles()):
            result, _mod, _client = _run_module(self.MODULE, params)

        assert [r["id"] for r in result["admin_roles"]] == ["a1"]

    def test_exact_name_without_match_returns_empty_list(self):
        params = _base_params("name", name="nope")
        with patch(f"{self.MODULE}.get_admin_roles", return_value=self._roles()):
            result, _mod, _client = _run_module(self.MODULE, params)

        assert result["admin_roles"] == []

    def test_search_is_a_case_insensitive_substring(self):
        params = _base_params("name", search="AUDIT")
        with patch(f"{self.MODULE}.get_admin_roles", return_value=self._roles()):
            result, _mod, _client = _run_module(self.MODULE, params)

        assert [r["id"] for r in result["admin_roles"]] == ["a1", "a2"]

    def test_missing_credentials_fails(self):
        params = _base_params("name", token=None)
        with patch(f"{self.MODULE}.get_admin_roles") as mock_list:
            result, mod, _client = _run_module(self.MODULE, params)

        mod.fail_json.assert_called_once()
        mock_list.assert_not_called()
        assert "token" in result["msg"]

    def test_session_is_closed(self):
        with patch(f"{self.MODULE}.get_admin_roles", return_value=self._roles()):
            _result, _mod, client = _run_module(self.MODULE, _base_params("name"))

        client.logout.assert_called_once()
