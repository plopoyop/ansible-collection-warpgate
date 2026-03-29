"""Tests for warpgate_user module logic: normalize_credential_policy, manage_* functions."""

from unittest.mock import patch

import pytest

# Import module-level functions — conftest.py wires up ansible.module_utils
import warpgate_user  # noqa: E402
from warpgate_client.client import WarpgateAPIError
from warpgate_client.credential import PasswordCredential, PublicKeyCredential
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

    def test_api_error_on_list_still_creates(self, mock_client, mock_module):
        """If we can't list credentials, assume change is needed."""
        new_cred = PasswordCredential(id="c1")
        with (
            patch(
                "warpgate_user.get_password_credentials",
                side_effect=WarpgateAPIError(500, "fail"),
            ),
            patch("warpgate_user.add_password_credential", return_value=new_cred),
        ):
            result = warpgate_user.manage_password_credentials(
                mock_client, "u1", ["pw1"], mock_module
            )
        assert result is True

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
        with patch(
            "warpgate_user.get_user_roles",
            side_effect=WarpgateAPIError(500, "server error"),
        ):
            with pytest.raises(SystemExit):
                warpgate_user.manage_user_roles(mock_client, "u1", ["r1"], mock_module)
        mock_module.fail_json.assert_called_once()
