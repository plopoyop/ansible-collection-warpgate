"""Tests for warpgate_target module: build_target_options, options_equal, resolve_group_id, manage_target_roles, and main()."""

from unittest.mock import MagicMock, patch

import pytest
import warpgate_target
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator
from warpgate_client.client import WarpgateAPIError
from warpgate_client.role import Role
from warpgate_client.target import Target
from warpgate_client.target_group import TargetGroup

# ---------------------------------------------------------------------------
# build_target_options
# ---------------------------------------------------------------------------


class TestBuildTargetOptions:
    def _make_module(self, **option_params):
        """Create a mock module with the given option parameters."""
        mod = MagicMock()
        params = {
            "ssh_options": None,
            "http_options": None,
            "mysql_options": None,
            "postgres_options": None,
            "kubernetes_options": None,
        }
        params.update(option_params)
        mod.params = params
        mod.fail_json = MagicMock(side_effect=SystemExit)
        return mod

    def test_ssh_with_password_auth(self):
        mod = self._make_module(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "allow_insecure_algos": False,
                "password_auth": {"password": "secret"},
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["kind"] == "Ssh"
        assert opts["host"] == "10.0.0.1"
        assert opts["auth"]["kind"] == "Password"
        assert opts["auth"]["password"] == "secret"

    def test_ssh_with_public_key_auth(self):
        mod = self._make_module(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "public_key_auth": {},
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["auth"]["kind"] == "PublicKey"

    def test_ssh_no_auth_fails(self):
        mod = self._make_module(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
            }
        )
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)
        mod.fail_json.assert_called_once()

    def test_http_options(self):
        mod = self._make_module(
            http_options={
                "url": "https://app.local",
                "tls": {"mode": "Required", "verify": True},
                "headers": {"X-Custom": "val"},
                "external_host": "ext.local",
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["kind"] == "Http"
        assert opts["url"] == "https://app.local"
        assert opts["headers"] == {"X-Custom": "val"}
        assert opts["external_host"] == "ext.local"

    def test_mysql_options(self):
        mod = self._make_module(
            mysql_options={
                "host": "db.local",
                "port": 3306,
                "username": "root",
                "password": "pass",
                "tls": {"mode": "Disabled", "verify": False},
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["kind"] == "MySql"
        # v0.23+: the module emits the new ``auth`` structure instead of the
        # deprecated flat ``password`` field.
        assert "password" not in opts
        assert opts["auth"] == {"kind": "Password", "password": "pass"}

    def test_mysql_options_iam_role(self):
        mod = self._make_module(
            mysql_options={
                "host": "db.local",
                "port": 3306,
                "username": "root",
                "iam_role": True,
                "tls": {"mode": "Disabled", "verify": False},
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["auth"] == {"kind": "IamRole"}

    def test_postgres_options(self):
        mod = self._make_module(
            postgres_options={
                "host": "pg.local",
                "port": 5432,
                "username": "postgres",
                "tls": {"mode": "Preferred", "verify": True},
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["kind"] == "Postgres"
        assert "password" not in opts
        assert "auth" not in opts  # no password, no iam_role → auth omitted

    def test_kubernetes_token_auth(self):
        mod = self._make_module(
            kubernetes_options={
                "cluster_url": "https://k8s.local:6443",
                "tls": {"mode": "Required", "verify": True},
                "token_auth": {"token": "my-token"},
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["kind"] == "Kubernetes"
        assert opts["auth"]["kind"] == "Token"

    def test_kubernetes_certificate_auth(self):
        mod = self._make_module(
            kubernetes_options={
                "cluster_url": "https://k8s.local:6443",
                "tls": {"mode": "Required", "verify": True},
                "certificate_auth": {
                    "certificate": "cert-pem",
                    "private_key": "key-pem",
                },
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["auth"]["kind"] == "Certificate"

    def test_kubernetes_no_auth_fails(self):
        mod = self._make_module(
            kubernetes_options={
                "cluster_url": "https://k8s.local:6443",
                "tls": {"mode": "Required", "verify": True},
            }
        )
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)

    def test_ssh_iam_role_auth(self):
        mod = self._make_module(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "iam_role": True,
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["auth"] == {"kind": "IamRole"}

    def test_ssh_iam_role_exclusive_with_password_auth(self):
        mod = self._make_module(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "iam_role": True,
                "password_auth": {"password": "secret"},
            }
        )
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)
        mod.fail_json.assert_called_once()

    def test_ssh_jump_host_passthrough(self):
        mod = self._make_module(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "public_key_auth": {},
                "jump_host": "bastion-internal",
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["jump_host"] == "bastion-internal"

    def test_kubernetes_iam_role_auth(self):
        mod = self._make_module(
            kubernetes_options={
                "cluster_url": "https://k8s.local:6443",
                "tls": {"mode": "Required", "verify": True},
                "iam_role": True,
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["auth"] == {"kind": "IamRole"}

    def test_kubernetes_iam_role_exclusive_with_token_auth(self):
        mod = self._make_module(
            kubernetes_options={
                "cluster_url": "https://k8s.local:6443",
                "tls": {"mode": "Required", "verify": True},
                "iam_role": True,
                "token_auth": {"token": "my-token"},
            }
        )
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)
        mod.fail_json.assert_called_once()

    def test_postgres_protocol_version(self):
        mod = self._make_module(
            postgres_options={
                "host": "pg.local",
                "port": 5432,
                "username": "postgres",
                "tls": {"mode": "Preferred", "verify": True},
                "protocol_version": "3.2",
            }
        )
        opts = warpgate_target.build_target_options(mod)
        assert opts["protocol_version"] == "3.2"

    def test_postgres_protocol_version_invalid_fails(self):
        mod = self._make_module(
            postgres_options={
                "host": "pg.local",
                "port": 5432,
                "username": "postgres",
                "tls": {"mode": "Preferred", "verify": True},
                "protocol_version": "2.0",
            }
        )
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)
        mod.fail_json.assert_called_once()

    def test_no_options_fails(self):
        mod = self._make_module()
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)

    def test_multiple_options_fails(self):
        mod = self._make_module(
            ssh_options={"host": "h", "port": 22, "username": "u"},
            http_options={"url": "u", "tls": {"mode": "Disabled", "verify": False}},
        )
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)


# ---------------------------------------------------------------------------
# options_equal
# ---------------------------------------------------------------------------


class TestOptionsEqual:
    def test_equal_options(self):
        a = {"kind": "Ssh", "host": "10.0.0.1"}
        b = {"kind": "Ssh", "host": "10.0.0.1"}
        assert warpgate_target.options_equal(a, b) is True

    def test_different_options(self):
        a = {"kind": "Ssh", "host": "10.0.0.1"}
        b = {"kind": "Ssh", "host": "10.0.0.2"}
        assert warpgate_target.options_equal(a, b) is False

    def test_ignores_id_and_allow_roles(self):
        a = {"kind": "Ssh", "host": "h", "id": "old", "allow_roles": ["r1"]}
        b = {"kind": "Ssh", "host": "h"}
        assert warpgate_target.options_equal(a, b) is True

    def test_none_options(self):
        assert warpgate_target.options_equal(None, None) is True
        assert warpgate_target.options_equal(None, {"kind": "Ssh"}) is False

    def test_null_optional_fields_ignored(self):
        """Warpgate echoes optional HTTP fields as null; ignore them."""
        from_api = {
            "kind": "Http",
            "url": "https://example.com/",
            "tls": {"mode": "Required", "verify": True},
            "external_host": None,
            "headers": None,
        }
        from_module = {
            "kind": "Http",
            "url": "https://example.com/",
            "tls": {"mode": "Required", "verify": True},
        }
        assert warpgate_target.options_equal(from_api, from_module) is True

    def test_explicit_null_vs_real_value_differs(self):
        """A real value must still beat a null one."""
        a = {"kind": "Http", "url": "u", "external_host": "host.example"}
        b = {"kind": "Http", "url": "u", "external_host": None}
        assert warpgate_target.options_equal(a, b) is False

    def test_nested_null_fields_ignored(self):
        a = {
            "kind": "Ssh",
            "host": "h",
            "auth": {"kind": "publickey", "password": None},
        }
        b = {"kind": "Ssh", "host": "h", "auth": {"kind": "publickey"}}
        assert warpgate_target.options_equal(a, b) is True


# ---------------------------------------------------------------------------
# resolve_group_id
# ---------------------------------------------------------------------------


class TestResolveGroupId:
    def test_empty_name_returns_empty(self, mock_client, mock_module):
        assert warpgate_target.resolve_group_id(mock_client, "", mock_module) == ""

    def test_none_name_returns_empty(self, mock_client, mock_module):
        assert warpgate_target.resolve_group_id(mock_client, None, mock_module) == ""

    def test_resolves_existing_group(self, mock_client, mock_module):
        groups = [TargetGroup(id="g1", name="prod")]
        with patch("warpgate_target.get_target_groups", return_value=groups):
            gid = warpgate_target.resolve_group_id(mock_client, "prod", mock_module)
        assert gid == "g1"

    def test_unknown_group_fails(self, mock_client, mock_module):
        with patch("warpgate_target.get_target_groups", return_value=[]):
            with pytest.raises(SystemExit):
                warpgate_target.resolve_group_id(
                    mock_client, "nonexistent", mock_module
                )
        mock_module.fail_json.assert_called_once()


class TestResolveJumpHostId:
    def test_empty_value_returns_empty(self, mock_client, mock_module):
        assert warpgate_target.resolve_jump_host_id(mock_client, "", mock_module) == ""

    def test_uuid_passed_through_without_lookup(self, mock_client, mock_module):
        uuid = "123e4567-e89b-12d3-a456-426614174000"
        with patch("warpgate_target.get_targets") as mock_get:
            resolved = warpgate_target.resolve_jump_host_id(
                mock_client, uuid, mock_module
            )
        mock_get.assert_not_called()
        assert resolved == uuid

    def test_resolves_target_name(self, mock_client, mock_module):
        targets = [Target(id="t-bastion", name="bastion-internal")]
        with patch("warpgate_target.get_targets", return_value=targets):
            resolved = warpgate_target.resolve_jump_host_id(
                mock_client, "bastion-internal", mock_module
            )
        assert resolved == "t-bastion"

    def test_unknown_jump_host_fails(self, mock_client, mock_module):
        with patch("warpgate_target.get_targets", return_value=[]):
            with pytest.raises(SystemExit):
                warpgate_target.resolve_jump_host_id(
                    mock_client, "nonexistent", mock_module
                )
        mock_module.fail_json.assert_called_once()


# ---------------------------------------------------------------------------
# manage_target_roles
# ---------------------------------------------------------------------------


class TestManageTargetRoles:
    def test_no_change_when_roles_match(self, mock_client, mock_module):
        changed, final = warpgate_target.manage_target_roles(
            mock_client,
            "t1",
            ["r1", "r2"],
            mock_module,
            current_role_ids_from_target=["r1", "r2"],
        )
        assert changed is False

    def test_add_missing_role(self, mock_client, mock_module):
        with patch("warpgate_target.add_target_role") as mock_add:
            changed, final = warpgate_target.manage_target_roles(
                mock_client,
                "t1",
                ["r1", "r2"],
                mock_module,
                current_role_ids_from_target=["r1"],
            )
        assert changed is True
        mock_add.assert_called_once()

    def test_remove_extra_role(self, mock_client, mock_module):
        with patch("warpgate_target.delete_target_role") as mock_del:
            changed, final = warpgate_target.manage_target_roles(
                mock_client,
                "t1",
                ["r1"],
                mock_module,
                current_role_ids_from_target=["r1", "r2"],
            )
        assert changed is True
        mock_del.assert_called_once()

    def test_empty_desired_removes_all(self, mock_client, mock_module):
        with patch("warpgate_target.delete_target_role"):
            changed, final = warpgate_target.manage_target_roles(
                mock_client,
                "t1",
                [],
                mock_module,
                current_role_ids_from_target=["r1"],
            )
        assert changed is True
        assert final == []

    def test_check_mode_no_api_calls(self, mock_client, mock_module):
        mock_module.check_mode = True
        with (
            patch("warpgate_target.add_target_role") as mock_add,
            patch("warpgate_target.delete_target_role") as mock_del,
        ):
            changed, final = warpgate_target.manage_target_roles(
                mock_client,
                "t1",
                ["r2"],
                mock_module,
                current_role_ids_from_target=["r1"],
            )
        assert changed is True
        mock_add.assert_not_called()
        mock_del.assert_not_called()

    def test_409_conflict_skipped(self, mock_client, mock_module):
        """409 means already assigned — should be treated as success."""
        with patch(
            "warpgate_target.add_target_role",
            side_effect=WarpgateAPIError(409, "conflict"),
        ):
            changed, _ = warpgate_target.manage_target_roles(
                mock_client,
                "t1",
                ["r1", "r2"],
                mock_module,
                current_role_ids_from_target=["r1"],
            )
        # 409 was skipped, nothing was actually_added
        assert changed is False

    def test_fallback_to_get_target_roles(self, mock_client, mock_module):
        """When current_role_ids_from_target is empty, falls back to API."""
        roles = [Role(id="r1", name="dev")]
        with patch("warpgate_target.get_target_roles", return_value=roles):
            changed, _ = warpgate_target.manage_target_roles(
                mock_client,
                "t1",
                ["r1"],
                mock_module,
                current_role_ids_from_target=None,
            )
        assert changed is False


# ---------------------------------------------------------------------------
# Module main() — integration-level
# ---------------------------------------------------------------------------


def _base_params(**overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        id=None,
        name="prod-ssh",
        description="Prod server",
        group="production",
        ssh_options={
            "host": "10.0.0.1",
            "port": 22,
            "username": "admin",
            "password_auth": {"password": "secret"},
        },
        http_options=None,
        mysql_options=None,
        postgres_options=None,
        kubernetes_options=None,
        roles=["developers"],
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    with patch("warpgate_target.AnsibleModule") as mock_cls:
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

        with patch("warpgate_target.WarpgateClient"):
            try:
                warpgate_target.main()
            except SystemExit:
                pass

        return result, mod


class TestTargetModuleCreate:
    def test_create_new_target(self):
        new_target = Target(
            id="t1", name="prod-ssh", description="Prod server", group_id="g1"
        )
        group = TargetGroup(id="g1", name="production")
        params = _base_params()
        with (
            patch("warpgate_target.get_targets", return_value=[]),
            patch("warpgate_target.get_target_groups", return_value=[group]),
            patch("warpgate_target.create_target", return_value=new_target),
            patch("warpgate_target._resolve_role_ids", return_value=["r-dev"]),
            patch("warpgate_target.add_target_role"),
            patch("warpgate_target.get_target_roles", return_value=[]),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["diff"]["before"] == {}
        assert result["diff"]["after"]["name"] == "prod-ssh"
        assert result["diff"]["after"]["options"]["auth"]["password"] == "********"

    def test_create_check_mode(self):
        group = TargetGroup(id="g1", name="production")
        params = _base_params()
        with (
            patch("warpgate_target.get_targets", return_value=[]),
            patch("warpgate_target.get_target_groups", return_value=[group]),
            patch("warpgate_target.create_target") as mock_create,
            patch("warpgate_target._resolve_role_ids", return_value=["r-dev"]),
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert result["id"] == "new-target-id"


class TestTargetModuleUpdate:
    def test_update_existing_target(self):
        existing = Target(
            id="t1",
            name="prod-ssh",
            description="Old",
            group_id="g1",
            options={
                "kind": "Ssh",
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "allow_insecure_algos": False,
                "auth": {"kind": "Password", "password": "secret"},
            },
            allow_roles=["r-dev"],
        )
        updated = Target(
            id="t1", name="prod-ssh", description="Prod server", group_id="g1"
        )
        group = TargetGroup(id="g1", name="production")
        params = _base_params()
        with (
            patch("warpgate_target.get_targets", return_value=[existing]),
            patch("warpgate_target.get_target", return_value=existing),
            patch("warpgate_target.get_target_groups", return_value=[group]),
            patch("warpgate_target.update_target", return_value=updated),
            patch("warpgate_target._resolve_role_ids", return_value=["r-dev"]),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["diff"]["before"]["description"] == "Old"
        assert result["diff"]["after"]["description"] == "Prod server"
        assert result["diff"]["before"]["options"]["auth"]["password"] == "********"
        assert result["diff"]["after"]["options"]["auth"]["password"] == "********"

    def test_no_change_when_identical(self):
        opts = {
            "kind": "Ssh",
            "host": "10.0.0.1",
            "port": 22,
            "username": "admin",
            "allow_insecure_algos": False,
            "auth": {"kind": "Password", "password": "secret"},
        }
        existing = Target(
            id="t1",
            name="prod-ssh",
            description="Prod server",
            group_id="g1",
            options=opts,
            allow_roles=["r-dev"],
        )
        group = TargetGroup(id="g1", name="production")
        params = _base_params()
        with (
            patch("warpgate_target.get_targets", return_value=[existing]),
            patch("warpgate_target.get_target", return_value=existing),
            patch("warpgate_target.get_target_groups", return_value=[group]),
            patch("warpgate_target._resolve_role_ids", return_value=["r-dev"]),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is False


class TestTargetModuleDelete:
    def test_delete_existing_target(self):
        existing = Target(id="t1", name="prod-ssh")
        params = _base_params(state="absent")
        with (
            patch("warpgate_target.get_targets", return_value=[existing]),
            patch("warpgate_target.delete_target") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["name"] == "prod-ssh"
        assert result["diff"]["after"] == {}

    def test_delete_nonexistent_is_noop(self):
        params = _base_params(state="absent")
        with patch("warpgate_target.get_targets", return_value=[]):
            result, mod = _run_module(params)
        assert result["changed"] is False

    def test_delete_lookup_error_fails(self):
        params = _base_params(state="absent")
        with (
            patch(
                "warpgate_target.get_targets",
                side_effect=WarpgateAPIError(500, "boom"),
            ),
            patch("warpgate_target.delete_target") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        mod.fail_json.assert_called_once()
        assert result.get("changed") is not True

    def test_delete_by_id_with_other_name_fails(self):
        params = _base_params(state="absent", id="t1")
        with (
            patch(
                "warpgate_target.get_target",
                return_value=Target(id="t1", name="other-target"),
            ),
            patch("warpgate_target.delete_target") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        assert "other-target" in result["msg"]

    def test_delete_by_unknown_id_with_recreated_name_fails(self):
        params = _base_params(state="absent", id="t1")
        with (
            patch("warpgate_target.get_target", return_value=None),
            patch(
                "warpgate_target.get_targets",
                return_value=[Target(id="t2", name="prod-ssh")],
            ),
            patch("warpgate_target.delete_target") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        assert "t2" in result["msg"]

    def test_delete_by_unknown_id_is_noop(self):
        params = _base_params(state="absent", id="t1")
        with (
            patch("warpgate_target.get_target", return_value=None),
            patch("warpgate_target.get_targets", return_value=[]),
            patch("warpgate_target.delete_target") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        assert result["changed"] is False


# ---------------------------------------------------------------------------
# argument_spec: secrets nested in *_options must be no_log
# ---------------------------------------------------------------------------


def _argument_spec():
    with patch("warpgate_target.AnsibleModule") as mock_cls:
        mock_cls.side_effect = SystemExit
        with pytest.raises(SystemExit):
            warpgate_target.main()
    return mock_cls.call_args.kwargs["argument_spec"]


def _validate(**params):
    base = {"host": "https://wg", "token": "api-token", "name": "t"}
    base.update(params)
    return ArgumentSpecValidator(_argument_spec()).validate(base)


_TLS = {"mode": "Required", "verify": True}


class TestArgumentSpecNoLog:
    @pytest.mark.parametrize(
        "options_key, options, secrets",
        [
            (
                "ssh_options",
                {
                    "host": "10.0.0.1",
                    "port": 22,
                    "username": "deploy",
                    "password_auth": {"password": "ssh-pass"},
                },
                ["ssh-pass"],
            ),
            (
                "mysql_options",
                {
                    "host": "db",
                    "port": 3306,
                    "username": "deploy",
                    "password": "mysql-pass",
                    "tls": _TLS,
                },
                ["mysql-pass"],
            ),
            (
                "postgres_options",
                {
                    "host": "db",
                    "port": 5432,
                    "username": "deploy",
                    "password": "pg-pass",
                    "tls": _TLS,
                },
                ["pg-pass"],
            ),
            (
                "kubernetes_options",
                {
                    "cluster_url": "https://k8s:6443",
                    "tls": _TLS,
                    "token_auth": {"token": "k8s-token"},
                },
                ["k8s-token"],
            ),
            (
                "kubernetes_options",
                {
                    "cluster_url": "https://k8s:6443",
                    "tls": _TLS,
                    "certificate_auth": {
                        "certificate": "CERT-PEM",
                        "private_key": "KEY-PEM",
                    },
                },
                ["KEY-PEM"],
            ),
        ],
    )
    def test_secrets_are_no_log(self, options_key, options, secrets):
        result = _validate(**{options_key: options})
        assert result.error_messages == []
        for secret in secrets:
            assert secret in result._no_log_values
        assert "deploy" not in result._no_log_values
        assert "CERT-PEM" not in result._no_log_values

    def test_validated_ssh_public_key_params_build(self):
        result = _validate(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "deploy",
                "public_key_auth": {},
            }
        )
        mod = MagicMock()
        mod.params = result.validated_parameters
        opts = warpgate_target.build_target_options(mod)
        assert opts["auth"] == {"kind": "PublicKey"}

    def test_validated_ssh_password_params_build(self):
        result = _validate(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "deploy",
                "password_auth": {"password": "ssh-pass"},
            }
        )
        mod = MagicMock()
        mod.params = result.validated_parameters
        mod.fail_json = MagicMock(side_effect=SystemExit)
        opts = warpgate_target.build_target_options(mod)
        assert opts["auth"] == {"kind": "Password", "password": "ssh-pass"}

    def test_unknown_suboption_rejected(self):
        result = _validate(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "deploy",
                "pasword_auth": {"password": "typo"},
            }
        )
        assert any("pasword_auth" in m for m in result.error_messages)

    def test_header_values_are_not_no_log(self):
        result = _validate(
            http_options={"url": "https://app", "tls": _TLS, "headers": {"X-A": "1"}}
        )
        assert result.error_messages == []
        assert "1" not in result._no_log_values

    def test_public_key_auth_null_is_unset(self):
        result = _validate(
            ssh_options={
                "host": "10.0.0.1",
                "port": 22,
                "username": "deploy",
                "public_key_auth": None,
            }
        )
        mod = MagicMock()
        mod.params = result.validated_parameters
        mod.fail_json = MagicMock(side_effect=SystemExit)
        with pytest.raises(SystemExit):
            warpgate_target.build_target_options(mod)

    @pytest.mark.parametrize(
        "options_key, options, server_options",
        [
            (
                "mysql_options",
                {
                    "host": "db",
                    "port": 3306,
                    "username": "deploy",
                    "password": "mysql-pass",
                    "tls": _TLS,
                },
                {
                    "kind": "MySql",
                    "host": "db",
                    "port": 3306,
                    "username": "deploy",
                    "auth": {"kind": "Password", "password": "mysql-pass"},
                    "tls": _TLS,
                    "default_database_name": None,
                },
            ),
            (
                "postgres_options",
                {
                    "host": "db",
                    "port": 5432,
                    "username": "deploy",
                    "iam_role": True,
                    "tls": _TLS,
                    "protocol_version": 3.0,
                },
                {
                    "kind": "Postgres",
                    "host": "db",
                    "port": 5432,
                    "username": "deploy",
                    "auth": {"kind": "IamRole"},
                    "tls": _TLS,
                    "protocol_version": "3.0",
                    "idle_timeout": None,
                },
            ),
            (
                "http_options",
                {"url": "https://app", "tls": _TLS},
                {
                    "kind": "Http",
                    "url": "https://app",
                    "tls": _TLS,
                    "headers": None,
                    "external_host": None,
                },
            ),
            (
                "kubernetes_options",
                {
                    "cluster_url": "https://k8s:6443",
                    "tls": _TLS,
                    "token_auth": {"token": "k8s-token"},
                },
                {
                    "kind": "Kubernetes",
                    "cluster_url": "https://k8s:6443",
                    "tls": _TLS,
                    "auth": {"kind": "Token", "token": "k8s-token"},
                },
            ),
        ],
    )
    def test_validated_params_match_server_echo(
        self, options_key, options, server_options
    ):
        result = _validate(**{options_key: options})
        assert result.error_messages == []
        mod = MagicMock()
        mod.params = result.validated_parameters
        mod.fail_json = MagicMock(side_effect=SystemExit)
        opts = warpgate_target.build_target_options(mod)
        assert warpgate_target.options_equal(server_options, opts)


class TestTargetRolesPartialFailure:
    def test_second_role_removal_failure_reports_changed(
        self, mock_client, mock_module
    ):
        result = {"changed": False}
        with (
            patch(
                "warpgate_target.delete_target_role",
                side_effect=[None, WarpgateAPIError(500, "boom")],
            ),
            pytest.raises(SystemExit),
        ):
            warpgate_target.manage_target_roles(
                mock_client,
                "t1",
                [],
                mock_module,
                current_role_ids_from_target=["r1", "r2"],
                result=result,
            )
        assert result["changed"] is True
        assert mock_module.fail_json.call_args.kwargs["changed"] is True

    def test_role_listing_404_fails(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_target.get_target_roles",
                side_effect=WarpgateAPIError(404, "gone"),
            ),
            pytest.raises(SystemExit),
        ):
            warpgate_target.manage_target_roles(mock_client, "t1", [], mock_module)
