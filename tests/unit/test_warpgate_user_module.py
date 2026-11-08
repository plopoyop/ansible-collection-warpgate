"""Tests for warpgate_user module logic: normalize_credential_policy, manage_* functions."""

from unittest.mock import MagicMock, patch

import pytest

# Import module-level functions — conftest.py wires up ansible.module_utils
import warpgate_user
from warpgate_client.user import User
from warpgate_client.client import WarpgateAPIError, WarpgateClientError
from warpgate_client.credential import (
    PasswordCredential,
    PublicKeyCredential,
    SsoCredential,
)
from warpgate_client.role import Role

# ---------------------------------------------------------------------------
# normalize_credential_policy
# ---------------------------------------------------------------------------


class TestNormalizeCredentialPolicy:
    def test_none_returns_none(self):
        assert warpgate_user.normalize_credential_policy(None) is None

    def test_empty_dict_returns_none(self):
        assert warpgate_user.normalize_credential_policy({}) is None

    def test_all_empty_lists_returns_none(self):
        """This is the idempotence bug scenario — empty lists must yield None."""
        policy = {"http": [], "ssh": [], "mysql": [], "postgres": []}
        assert warpgate_user.normalize_credential_policy(policy) is None

    def test_mixed_empty_and_none_returns_none(self):
        policy = {"http": None, "ssh": [], "mysql": None, "postgres": []}
        assert warpgate_user.normalize_credential_policy(policy) is None

    def test_with_http_values(self):
        policy = {"http": ["Password"]}
        result = warpgate_user.normalize_credential_policy(policy)
        assert result is not None
        assert result.to_dict() == {"http": ["Password"]}

    def test_with_multiple_protocols(self):
        policy = {
            "http": ["Password"],
            "ssh": ["PublicKey", "Password"],
            "mysql": [],
            "postgres": None,
        }
        result = warpgate_user.normalize_credential_policy(policy)
        assert result is not None
        d = result.to_dict()
        assert d == {"http": ["Password"], "ssh": ["PublicKey", "Password"]}
        assert "mysql" not in d
        assert "postgres" not in d

    def test_empty_list_treated_as_none_field(self):
        """An empty list for one field shouldn't create a policy if others are also empty."""
        policy = {"http": [], "ssh": ["Password"]}
        result = warpgate_user.normalize_credential_policy(policy)
        assert result is not None
        assert result.http is None  # empty list → None
        assert result.ssh == ["Password"]


# ---------------------------------------------------------------------------
# manage_password_credentials
# ---------------------------------------------------------------------------


class TestManagePasswordCredentials:
    def test_empty_passwords_returns_false(self, mock_client, mock_module):
        assert (
            warpgate_user.manage_password_credentials(
                mock_client, "u1", [], mock_module
            )
            is False
        )

    def test_none_passwords_returns_false(self, mock_client, mock_module):
        """Falsy input → no change."""
        assert (
            warpgate_user.manage_password_credentials(
                mock_client, "u1", None, mock_module
            )
            is False
        )

    # -- on_create (default) -----------------------------------------------

    def test_on_create_existing_creds_is_noop(self, mock_client, mock_module):
        """on_create: user already has credentials → no change."""
        existing = [PasswordCredential(id="c1"), PasswordCredential(id="c2")]
        with patch("warpgate_user.get_password_credentials", return_value=existing):
            result = warpgate_user.manage_password_credentials(
                mock_client,
                "u1",
                ["pw1", "pw2"],
                mock_module,
                update_password="on_create",
            )
        assert result is False

    def test_on_create_no_existing_creates(self, mock_client, mock_module):
        """on_create: no existing credentials → create them."""
        new_cred = PasswordCredential(id="c1")
        with (
            patch("warpgate_user.get_password_credentials", return_value=[]),
            patch("warpgate_user.add_password_credential", return_value=new_cred),
        ):
            result = warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module, update_password="on_create"
            )
        assert result is True

    # -- always ------------------------------------------------------------

    def test_always_replaces_all_credentials(self, mock_client, mock_module):
        """always: even if credentials exist, delete and recreate."""
        existing = [PasswordCredential(id="c1"), PasswordCredential(id="c2")]
        new_cred = PasswordCredential(id="c3")
        with (
            patch("warpgate_user.get_password_credentials", return_value=existing),
            patch("warpgate_user.delete_password_credential") as mock_del,
            patch("warpgate_user.add_password_credential", return_value=new_cred),
        ):
            result = warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1", "pw2"], mock_module, update_password="always"
            )
        assert result is True
        assert mock_del.call_count == 2

    def test_always_no_existing_creates(self, mock_client, mock_module):
        """always: no existing credentials → create without delete."""
        new_cred = PasswordCredential(id="c1")
        with (
            patch("warpgate_user.get_password_credentials", return_value=[]),
            patch("warpgate_user.delete_password_credential") as mock_del,
            patch("warpgate_user.add_password_credential", return_value=new_cred),
        ):
            result = warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module, update_password="always"
            )
        assert result is True
        mock_del.assert_not_called()

    def test_always_check_mode_no_api_calls(self, mock_client, mock_module):
        """always + check_mode: reports changed but no API mutations."""
        mock_module.check_mode = True
        existing = [PasswordCredential(id="c1")]
        with (
            patch("warpgate_user.get_password_credentials", return_value=existing),
            patch("warpgate_user.delete_password_credential") as mock_del,
            patch("warpgate_user.add_password_credential") as mock_add,
        ):
            result = warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module, update_password="always"
            )
        assert result is True
        mock_del.assert_not_called()
        mock_add.assert_not_called()

    # -- error handling ----------------------------------------------------

    def test_api_error_on_list_fails(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_user.get_password_credentials",
                side_effect=WarpgateAPIError(500, "fail"),
            ),
            patch("warpgate_user.add_password_credential") as mock_add,
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module, update_password="always"
            )
        mock_add.assert_not_called()

    def test_always_adds_before_deleting(self, mock_client, mock_module):
        calls = []
        with (
            patch(
                "warpgate_user.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch(
                "warpgate_user.delete_password_credential",
                side_effect=lambda *a: calls.append("delete"),
            ),
            patch(
                "warpgate_user.add_password_credential",
                side_effect=lambda *a: calls.append("add"),
            ),
        ):
            warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module, update_password="always"
            )
        assert calls == ["add", "delete"]

    def test_always_delete_error_fails(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_user.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch(
                "warpgate_user.delete_password_credential",
                side_effect=WarpgateAPIError(500, "fail"),
            ),
            patch("warpgate_user.add_password_credential"),
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module, update_password="always"
            )
        assert mock_module.fail_json.call_args.kwargs["changed"] is True

    def test_check_mode_no_api_calls(self, mock_client, mock_module):
        mock_module.check_mode = True
        existing = []
        with (
            patch("warpgate_user.get_password_credentials", return_value=existing),
            patch("warpgate_user.add_password_credential") as mock_add,
        ):
            result = warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module
            )
        assert result is True
        mock_add.assert_not_called()


# ---------------------------------------------------------------------------
# manage_public_key_credentials
# ---------------------------------------------------------------------------


class TestManagePublicKeyCredentials:
    def _make_pk(self, id, label, key):
        return PublicKeyCredential(id=id, label=label, openssh_public_key=key)

    def test_empty_desired_no_existing_no_change(self, mock_client, mock_module):
        with patch("warpgate_user.get_public_key_credentials", return_value=[]):
            changed, creds = warpgate_user.manage_public_key_credentials(
                mock_client, "u1", [], mock_module
            )
        assert changed is False
        assert creds == []

    def test_add_new_key(self, mock_client, mock_module):
        new_cred = self._make_pk("pk1", "laptop", "ssh-ed25519 AAAA...")
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=[]),
            patch("warpgate_user.add_public_key_credential", return_value=new_cred),
        ):
            changed, creds = warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [{"label": "laptop", "public_key": "ssh-ed25519 AAAA..."}],
                mock_module,
            )
        assert changed is True
        assert len(creds) == 1
        assert creds[0]["label"] == "laptop"

    def test_existing_key_same_value_no_change(self, mock_client, mock_module):
        existing = self._make_pk("pk1", "laptop", "ssh-ed25519 AAAA... user@host")
        with patch("warpgate_user.get_public_key_credentials", return_value=[existing]):
            changed, creds = warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [
                    {
                        "label": "laptop",
                        "public_key": "ssh-ed25519 AAAA... other-comment",
                    }
                ],
                mock_module,
            )
        # Key part (type + data) is the same; only comment differs → no change
        assert changed is False

    def test_existing_key_different_value_triggers_update(
        self, mock_client, mock_module
    ):
        existing = self._make_pk("pk1", "laptop", "ssh-ed25519 AAAA...")
        updated = self._make_pk("pk1", "laptop", "ssh-ed25519 BBBB...")
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=[existing]),
            patch("warpgate_user.update_public_key_credential", return_value=updated),
        ):
            changed, creds = warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [{"label": "laptop", "public_key": "ssh-ed25519 BBBB..."}],
                mock_module,
            )
        assert changed is True

    def test_extra_keys_removed(self, mock_client, mock_module):
        existing = self._make_pk("pk1", "old-key", "ssh-ed25519 OLD...")
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=[existing]),
            patch("warpgate_user.delete_public_key_credential") as mock_del,
        ):
            changed, _ = warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [],
                mock_module,
            )
        assert changed is True
        mock_del.assert_called_once()

    def test_check_mode_reports_change_but_no_api(self, mock_client, mock_module):
        mock_module.check_mode = True
        with patch("warpgate_user.get_public_key_credentials", return_value=[]):
            changed, creds = warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [{"label": "laptop", "public_key": "ssh-ed25519 AAAA..."}],
                mock_module,
            )
        assert changed is True
        assert creds[0]["id"] == "new-credential-id"

    def test_key_comparison_ignores_whitespace(self, mock_client, mock_module):
        existing = self._make_pk("pk1", "laptop", "  ssh-ed25519 AAAA...  \r\n")
        with patch("warpgate_user.get_public_key_credentials", return_value=[existing]):
            changed, _ = warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [{"label": "laptop", "public_key": "ssh-ed25519 AAAA..."}],
                mock_module,
            )
        assert changed is False


# ---------------------------------------------------------------------------
# manage_sso_credentials
# ---------------------------------------------------------------------------


class TestManagePublicKeyCredentialsErrors:
    def test_api_error_on_list_fails(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_user.get_public_key_credentials",
                side_effect=WarpgateAPIError(500, "fail"),
            ),
            patch("warpgate_user.delete_public_key_credential") as mock_del,
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_public_key_credentials(
                mock_client, "u1", [], mock_module
            )
        mock_del.assert_not_called()


class TestManageSsoCredentials:
    def _make_sso(self, id, provider, email):
        return SsoCredential(id=id, provider=provider, email=email)

    def test_none_desired_no_existing_no_change(self, mock_client, mock_module):
        with patch("warpgate_user.get_sso_credentials", return_value=[]):
            changed, creds = warpgate_user.manage_sso_credentials(
                mock_client, "u1", None, mock_module
            )
        assert changed is False
        assert creds == []

    def test_empty_desired_removes_all(self, mock_client, mock_module):
        existing = [self._make_sso("s1", "microsoft", "user@example.com")]
        with (
            patch("warpgate_user.get_sso_credentials", return_value=existing),
            patch("warpgate_user.delete_sso_credential") as mock_del,
        ):
            changed, creds = warpgate_user.manage_sso_credentials(
                mock_client, "u1", [], mock_module
            )
        assert changed is True
        mock_del.assert_called_once_with(mock_client, "u1", "s1")
        assert creds == []

    def test_add_missing_credential(self, mock_client, mock_module):
        new_cred = self._make_sso("s1", "microsoft", "user@example.com")
        with (
            patch("warpgate_user.get_sso_credentials", return_value=[]),
            patch(
                "warpgate_user.add_sso_credential", return_value=new_cred
            ) as mock_add,
        ):
            changed, creds = warpgate_user.manage_sso_credentials(
                mock_client,
                "u1",
                [{"email": "user@example.com", "provider": "microsoft"}],
                mock_module,
            )
        assert changed is True
        mock_add.assert_called_once_with(
            mock_client, "u1", "user@example.com", "microsoft"
        )
        assert creds == [
            {"id": "s1", "provider": "microsoft", "email": "user@example.com"}
        ]

    def test_existing_matching_credential_no_change(self, mock_client, mock_module):
        existing = [self._make_sso("s1", "microsoft", "user@example.com")]
        with (
            patch("warpgate_user.get_sso_credentials", return_value=existing),
            patch("warpgate_user.add_sso_credential") as mock_add,
            patch("warpgate_user.delete_sso_credential") as mock_del,
        ):
            changed, creds = warpgate_user.manage_sso_credentials(
                mock_client,
                "u1",
                [{"email": "user@example.com", "provider": "microsoft"}],
                mock_module,
            )
        assert changed is False
        mock_add.assert_not_called()
        mock_del.assert_not_called()
        assert creds[0]["id"] == "s1"

    def test_mismatched_email_deletes_and_recreates(self, mock_client, mock_module):
        existing = [self._make_sso("s1", "microsoft", "old@example.com")]
        new_cred = self._make_sso("s2", "microsoft", "new@example.com")
        with (
            patch("warpgate_user.get_sso_credentials", return_value=existing),
            patch("warpgate_user.delete_sso_credential") as mock_del,
            patch(
                "warpgate_user.add_sso_credential", return_value=new_cred
            ) as mock_add,
        ):
            changed, _ = warpgate_user.manage_sso_credentials(
                mock_client,
                "u1",
                [{"email": "new@example.com", "provider": "microsoft"}],
                mock_module,
            )
        assert changed is True
        mock_del.assert_called_once_with(mock_client, "u1", "s1")
        mock_add.assert_called_once_with(
            mock_client, "u1", "new@example.com", "microsoft"
        )

    def test_provider_empty_defaults_to_wildcard(self, mock_client, mock_module):
        """Provider "" is kept as-is and POSTed without the field (done in client lib)."""
        new_cred = self._make_sso("s1", "", "user@example.com")
        with (
            patch("warpgate_user.get_sso_credentials", return_value=[]),
            patch(
                "warpgate_user.add_sso_credential", return_value=new_cred
            ) as mock_add,
        ):
            changed, _ = warpgate_user.manage_sso_credentials(
                mock_client, "u1", [{"email": "user@example.com"}], mock_module
            )
        assert changed is True
        mock_add.assert_called_once_with(mock_client, "u1", "user@example.com", "")

    def test_check_mode_no_api_calls(self, mock_client, mock_module):
        mock_module.check_mode = True
        with (
            patch("warpgate_user.get_sso_credentials", return_value=[]),
            patch("warpgate_user.add_sso_credential") as mock_add,
        ):
            changed, creds = warpgate_user.manage_sso_credentials(
                mock_client,
                "u1",
                [{"email": "user@example.com", "provider": "microsoft"}],
                mock_module,
            )
        assert changed is True
        mock_add.assert_not_called()
        assert creds[0]["id"] == "new-sso-credential-id"

    def test_api_error_on_list_fails(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_user.get_sso_credentials",
                side_effect=WarpgateAPIError(500, "fail"),
            ),
            patch("warpgate_user.delete_sso_credential") as mock_del,
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_sso_credentials(mock_client, "u1", [], mock_module)
        mock_del.assert_not_called()


# ---------------------------------------------------------------------------
# manage_user_roles
# ---------------------------------------------------------------------------


class TestManageUserRoles:
    def test_no_change_when_roles_match(self, mock_client, mock_module):
        current = [Role(id="r1", name="dev"), Role(id="r2", name="ops")]
        with patch("warpgate_user.get_user_roles", return_value=current):
            changed, final = warpgate_user.manage_user_roles(
                mock_client, "u1", ["r1", "r2"], mock_module
            )
        assert changed is False
        assert set(final) == {"r1", "r2"}

    def test_add_missing_role(self, mock_client, mock_module):
        current = [Role(id="r1", name="dev")]
        with (
            patch("warpgate_user.get_user_roles", return_value=current),
            patch("warpgate_user.add_user_role") as mock_add,
        ):
            changed, final = warpgate_user.manage_user_roles(
                mock_client, "u1", ["r1", "r2"], mock_module
            )
        assert changed is True
        mock_add.assert_called_once_with(mock_client, "u1", "r2")
        assert set(final) == {"r1", "r2"}

    def test_remove_extra_role(self, mock_client, mock_module):
        current = [Role(id="r1", name="dev"), Role(id="r2", name="ops")]
        with (
            patch("warpgate_user.get_user_roles", return_value=current),
            patch("warpgate_user.delete_user_role") as mock_del,
        ):
            changed, final = warpgate_user.manage_user_roles(
                mock_client, "u1", ["r1"], mock_module
            )
        assert changed is True
        mock_del.assert_called_once_with(mock_client, "u1", "r2")

    def test_empty_desired_removes_all(self, mock_client, mock_module):
        current = [Role(id="r1", name="dev")]
        with (
            patch("warpgate_user.get_user_roles", return_value=current),
            patch("warpgate_user.delete_user_role") as mock_del,
        ):
            changed, final = warpgate_user.manage_user_roles(
                mock_client, "u1", [], mock_module
            )
        assert changed is True
        mock_del.assert_called_once()
        assert final == []

    def test_none_desired_treated_as_empty(self, mock_client, mock_module):
        current = [Role(id="r1", name="dev")]
        with (
            patch("warpgate_user.get_user_roles", return_value=current),
            patch("warpgate_user.delete_user_role"),
        ):
            changed, final = warpgate_user.manage_user_roles(
                mock_client, "u1", None, mock_module
            )
        assert changed is True

    def test_check_mode_no_api_mutations(self, mock_client, mock_module):
        mock_module.check_mode = True
        current = [Role(id="r1", name="dev")]
        with (
            patch("warpgate_user.get_user_roles", return_value=current),
            patch("warpgate_user.add_user_role") as mock_add,
            patch("warpgate_user.delete_user_role") as mock_del,
        ):
            changed, _ = warpgate_user.manage_user_roles(
                mock_client, "u1", ["r2"], mock_module
            )
        assert changed is True
        mock_add.assert_not_called()
        mock_del.assert_not_called()

    def test_api_error_calls_fail_json(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_user.get_user_roles",
                side_effect=WarpgateAPIError(500, "server error"),
            ),
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_user_roles(mock_client, "u1", ["r1"], mock_module)
        mock_module.fail_json.assert_called_once()


class TestDuplicateCredentials:
    def _pk(self, id, label, key):
        return PublicKeyCredential(id=id, label=label, openssh_public_key=key)

    def test_all_keys_with_an_unwanted_label_are_removed(
        self, mock_client, mock_module
    ):
        existing = [
            self._pk("k1", "Public Key", "ssh-ed25519 AAA1"),
            self._pk("k2", "Public Key", "ssh-ed25519 AAA2"),
        ]
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=existing),
            patch("warpgate_user.delete_public_key_credential") as mock_del,
        ):
            changed, _ = warpgate_user.manage_public_key_credentials(
                mock_client, "u1", [], mock_module
            )
        assert changed is True
        assert sorted(c.args[2] for c in mock_del.call_args_list) == ["k1", "k2"]

    def test_duplicate_label_keeps_the_matching_key(self, mock_client, mock_module):
        existing = [
            self._pk("k1", "Public Key", "ssh-ed25519 OLD"),
            self._pk("k2", "Public Key", "ssh-ed25519 NEW"),
        ]
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=existing),
            patch("warpgate_user.delete_public_key_credential") as mock_del,
            patch("warpgate_user.update_public_key_credential") as mock_upd,
        ):
            changed, creds = warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [{"label": "Public Key", "public_key": "ssh-ed25519 NEW comment"}],
                mock_module,
            )
        assert changed is True
        assert [c.args[2] for c in mock_del.call_args_list] == ["k1"]
        mock_upd.assert_not_called()
        assert creds[0]["id"] == "k2"

    def test_duplicate_sso_credential_is_removed(self, mock_client, mock_module):
        existing = [
            SsoCredential(id="s1", provider="google", email="a@example.com"),
            SsoCredential(id="s2", provider="google", email="a@example.com"),
        ]
        with (
            patch("warpgate_user.get_sso_credentials", return_value=existing),
            patch("warpgate_user.delete_sso_credential") as mock_del,
            patch("warpgate_user.add_sso_credential") as mock_add,
        ):
            changed, _ = warpgate_user.manage_sso_credentials(
                mock_client,
                "u1",
                [{"email": "a@example.com", "provider": "google"}],
                mock_module,
            )
        assert changed is True
        assert [c.args[2] for c in mock_del.call_args_list] == ["s2"]
        mock_add.assert_not_called()


class TestManageUserRolesErrors:
    def test_list_error_fails_in_check_mode(self, mock_client, mock_module):
        mock_module.check_mode = True
        with (
            patch(
                "warpgate_user.get_user_roles",
                side_effect=WarpgateAPIError(500, "fail"),
            ),
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_user_roles(mock_client, "u1", [], mock_module)


class _Params(dict):
    def __missing__(self, key):
        return None


def _run_user_module(**params):
    base = _Params(
        host="https://wg",
        token="tok",
        username="alice",
        state="absent",
        insecure=False,
        timeout=30,
        update_password="on_create",
    )
    base.update(params)
    result = {}
    with patch("warpgate_user.AnsibleModule") as mock_cls:
        mod = MagicMock()
        mod.params = base
        mod.check_mode = False

        def capture(**kwargs):
            result.update(kwargs)
            raise SystemExit

        mod.exit_json = MagicMock(side_effect=capture)
        mod.fail_json = MagicMock(side_effect=capture)
        mock_cls.return_value = mod
        with patch("warpgate_user.WarpgateClient"):
            try:
                warpgate_user.main()
            except SystemExit:
                pass
    return result


class TestUserDeleteById:
    def test_name_match_ignores_case(self):
        with (
            patch(
                "warpgate_user.get_user", return_value=User(id="u1", username="Alice")
            ),
            patch("warpgate_user.delete_user") as mock_del,
        ):
            result = _run_user_module(id="u1")
        mock_del.assert_called_once()
        assert result["changed"] is True

    def test_other_name_fails(self):
        with (
            patch("warpgate_user.get_user", return_value=User(id="u1", username="bob")),
            patch("warpgate_user.delete_user") as mock_del,
        ):
            result = _run_user_module(id="u1")
        mock_del.assert_not_called()
        assert "bob" in result["msg"]

    def test_unknown_id_with_recreated_user_fails(self):
        with (
            patch("warpgate_user.get_user", return_value=None),
            patch(
                "warpgate_user.get_users",
                return_value=[User(id="u2", username="alice")],
            ),
            patch("warpgate_user.delete_user") as mock_del,
        ):
            result = _run_user_module(id="u1")
        mock_del.assert_not_called()
        assert "u2" in result["msg"]


class TestPasswordRevocation:
    def test_empty_list_with_always_removes_passwords(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_user.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch("warpgate_user.delete_password_credential") as mock_del,
        ):
            changed = warpgate_user.manage_password_credentials(
                mock_client, "u1", [], mock_module, update_password="always"
            )
        assert changed is True
        mock_del.assert_called_once()

    def test_empty_list_with_always_and_no_password_is_noop(
        self, mock_client, mock_module
    ):
        with patch("warpgate_user.get_password_credentials", return_value=[]):
            changed = warpgate_user.manage_password_credentials(
                mock_client, "u1", [], mock_module, update_password="always"
            )
        assert changed is False

    def test_empty_list_on_create_keeps_passwords(self, mock_client, mock_module):
        with patch("warpgate_user.delete_password_credential") as mock_del:
            changed = warpgate_user.manage_password_credentials(
                mock_client, "u1", [], mock_module
            )
        assert changed is False
        mock_del.assert_not_called()


class TestCredentialOrder:
    def test_new_public_key_added_before_old_one_removed(
        self, mock_client, mock_module
    ):
        calls = []
        old = PublicKeyCredential(
            id="k1", label="laptop-2025", openssh_public_key="ssh-ed25519 OLD"
        )
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=[old]),
            patch(
                "warpgate_user.add_public_key_credential",
                side_effect=lambda *a: (
                    calls.append("add")
                    or PublicKeyCredential(
                        id="k2",
                        label="laptop-2026",
                        openssh_public_key="ssh-ed25519 NEW",
                    )
                ),
            ),
            patch(
                "warpgate_user.delete_public_key_credential",
                side_effect=lambda *a: calls.append("delete"),
            ),
        ):
            warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [{"label": "laptop-2026", "public_key": "ssh-ed25519 NEW"}],
                mock_module,
            )
        assert calls == ["add", "delete"]

    def test_rejected_new_key_keeps_old_one(self, mock_client, mock_module):
        old = PublicKeyCredential(
            id="k1", label="laptop-2025", openssh_public_key="ssh-ed25519 OLD"
        )
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=[old]),
            patch(
                "warpgate_user.add_public_key_credential",
                side_effect=WarpgateAPIError(400, "bad key"),
            ),
            patch("warpgate_user.delete_public_key_credential") as mock_del,
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [{"label": "laptop-2026", "public_key": "garbage"}],
                mock_module,
            )
        mock_del.assert_not_called()


class TestUserDeleteByUnknownId:
    def test_unknown_id_and_name_is_noop(self):
        with (
            patch("warpgate_user.get_user", return_value=None),
            patch("warpgate_user.get_users", return_value=[]),
            patch("warpgate_user.delete_user") as mock_del,
        ):
            result = _run_user_module(id="u1")
        mock_del.assert_not_called()
        assert result["changed"] is False


class TestSsoOrder:
    def test_new_sso_added_before_old_one_removed(self, mock_client, mock_module):
        calls = []
        old = SsoCredential(id="s1", provider="google", email="old@example.com")
        with (
            patch("warpgate_user.get_sso_credentials", return_value=[old]),
            patch(
                "warpgate_user.add_sso_credential",
                side_effect=lambda *a: (
                    calls.append("add")
                    or SsoCredential(
                        id="s2", provider="google", email="new@example.com"
                    )
                ),
            ),
            patch(
                "warpgate_user.delete_sso_credential",
                side_effect=lambda *a: calls.append("delete"),
            ),
        ):
            warpgate_user.manage_sso_credentials(
                mock_client,
                "u1",
                [{"email": "new@example.com", "provider": "google"}],
                mock_module,
            )
        assert calls == ["add", "delete"]


class TestChangedOnFailure:
    def test_earlier_change_reported_on_listing_failure(self, mock_client, mock_module):
        with (
            patch(
                "warpgate_user.get_public_key_credentials",
                side_effect=WarpgateAPIError(500, "fail"),
            ),
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_public_key_credentials(
                mock_client, "u1", [], mock_module, changed_before=True
            )
        assert mock_module.fail_json.call_args.kwargs["changed"] is True

    def test_duplicate_labels_rejected(self, mock_client, mock_module):
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=[]),
            patch("warpgate_user.add_public_key_credential") as mock_add,
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_public_key_credentials(
                mock_client,
                "u1",
                [
                    {"label": "L", "public_key": "ssh-ed25519 A"},
                    {"label": "L", "public_key": "ssh-ed25519 B"},
                ],
                mock_module,
            )
        mock_add.assert_not_called()
        assert "several times" in mock_module.fail_json.call_args.kwargs["msg"]


class TestPartialFailure:
    def test_second_key_removal_failure_reports_changed(self, mock_client, mock_module):
        existing = [
            PublicKeyCredential(id="k1", label="a", openssh_public_key="ssh-ed25519 A"),
            PublicKeyCredential(id="k2", label="b", openssh_public_key="ssh-ed25519 B"),
        ]
        with (
            patch("warpgate_user.get_public_key_credentials", return_value=existing),
            patch(
                "warpgate_user.delete_public_key_credential",
                side_effect=[None, WarpgateAPIError(500, "fail")],
            ),
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_public_key_credentials(
                mock_client, "u1", [], mock_module
            )
        assert mock_module.fail_json.call_args.kwargs["changed"] is True

    def test_second_role_removal_failure_reports_changed(
        self, mock_client, mock_module
    ):
        current = [Role(id="r1", name="a"), Role(id="r2", name="b")]
        with (
            patch("warpgate_user.get_user_roles", return_value=current),
            patch(
                "warpgate_user.delete_user_role",
                side_effect=[None, WarpgateAPIError(500, "fail")],
            ),
            pytest.raises(SystemExit),
        ):
            warpgate_user.manage_user_roles(mock_client, "u1", [], mock_module)
        assert mock_module.fail_json.call_args.kwargs["changed"] is True

    def test_creation_then_rejected_password_reports_changed(self):
        with (
            patch("warpgate_user.get_users", return_value=[]),
            patch(
                "warpgate_user.create_user",
                return_value=User(id="u1", username="alice"),
            ),
            patch(
                "warpgate_user.update_user",
                return_value=User(id="u1", username="alice"),
            ),
            patch("warpgate_user.get_password_credentials", return_value=[]),
            patch(
                "warpgate_user.add_password_credential",
                side_effect=WarpgateAPIError(422, "too short"),
            ),
        ):
            result = _run_user_module(state="present", password_credentials=["x"])
        assert result["changed"] is True
        assert "too short" in result["msg"]


class TestTransportErrorAfterChange:
    def test_rotation_client_error_after_add_reports_changed(self):
        with (
            patch(
                "warpgate_user.get_user", return_value=User(id="u1", username="alice")
            ),
            patch(
                "warpgate_user.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch("warpgate_user.add_password_credential"),
            patch(
                "warpgate_user.delete_password_credential",
                side_effect=WarpgateClientError("timeout"),
            ),
            patch("warpgate_user.get_public_key_credentials", return_value=[]),
            patch("warpgate_user.get_sso_credentials", return_value=[]),
            patch("warpgate_user.get_user_roles", return_value=[]),
            patch("warpgate_user.get_user_admin_roles", return_value=[]),
        ):
            result = _run_user_module(
                state="present",
                id="u1",
                password_credentials=["new"],
                update_password="always",
            )
        assert "timeout" in result["msg"]
        assert result["changed"] is True
