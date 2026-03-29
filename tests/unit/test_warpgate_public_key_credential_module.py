"""Tests for warpgate_public_key_credential module."""

from unittest.mock import patch, MagicMock


import warpgate_public_key_credential  # noqa: E402
from warpgate_client.credential import PublicKeyCredential


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
        credential_id=None,
        label="laptop",
        public_key="ssh-ed25519 AAAA...",
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    with patch("warpgate_public_key_credential.AnsibleModule") as mock_cls:
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

        with patch("warpgate_public_key_credential.WarpgateClient"):
            try:
                warpgate_public_key_credential.main()
            except SystemExit:
                pass

        return result, mod


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestPublicKeyCredentialCreate:
    def test_create_new_key(self):
        new_cred = PublicKeyCredential(
            id="pk1",
            label="laptop",
            openssh_public_key="ssh-ed25519 AAAA...",
            date_added="2024-01-01",
            last_used="",
        )
        params = _base_params()
        with patch(
            "warpgate_public_key_credential.add_public_key_credential",
            return_value=new_cred,
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["credential_id"] == "pk1"
        assert result["diff"]["before"] == {}
        assert result["diff"]["after"]["label"] == "laptop"

    def test_create_check_mode(self):
        params = _base_params()
        with patch(
            "warpgate_public_key_credential.add_public_key_credential"
        ) as mock_add:
            result, mod = _run_module(params, check_mode=True)
        mock_add.assert_not_called()
        assert result["changed"] is True
        assert result["credential_id"] == "new-credential-id"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestPublicKeyCredentialUpdate:
    def test_update_existing_key(self):
        existing = PublicKeyCredential(
            id="pk1",
            label="laptop",
            openssh_public_key="ssh-ed25519 OLD...",
        )
        updated = PublicKeyCredential(
            id="pk1",
            label="laptop",
            openssh_public_key="ssh-ed25519 AAAA...",
            date_added="2024-01-01",
            last_used="",
        )
        params = _base_params(credential_id="pk1")
        with (
            patch(
                "warpgate_public_key_credential.get_public_key_credentials",
                return_value=[existing],
            ),
            patch(
                "warpgate_public_key_credential.update_public_key_credential",
                return_value=updated,
            ),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["diff"]["before"]["public_key"] == "ssh-ed25519 OLD..."
        assert result["diff"]["after"]["public_key"] == "ssh-ed25519 AAAA..."

    def test_no_change_when_identical(self):
        existing = PublicKeyCredential(
            id="pk1",
            label="laptop",
            openssh_public_key="ssh-ed25519 AAAA...",
            date_added="2024-01-01",
            last_used="",
        )
        params = _base_params(credential_id="pk1")
        with patch(
            "warpgate_public_key_credential.get_public_key_credentials",
            return_value=[existing],
        ):
            result, mod = _run_module(params)
        assert result["changed"] is False
        assert "diff" not in result

    def test_update_check_mode(self):
        existing = PublicKeyCredential(
            id="pk1",
            label="laptop",
            openssh_public_key="ssh-ed25519 OLD...",
        )
        params = _base_params(credential_id="pk1")
        with (
            patch(
                "warpgate_public_key_credential.get_public_key_credentials",
                return_value=[existing],
            ),
            patch(
                "warpgate_public_key_credential.update_public_key_credential"
            ) as mock_update,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestPublicKeyCredentialDelete:
    def test_delete_credential(self):
        params = _base_params(state="absent", credential_id="pk1")
        with patch(
            "warpgate_public_key_credential.delete_public_key_credential"
        ) as mock_del:
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["credential_id"] == "pk1"
        assert result["diff"]["after"] == {}

    def test_delete_check_mode(self):
        params = _base_params(state="absent", credential_id="pk1")
        with patch(
            "warpgate_public_key_credential.delete_public_key_credential"
        ) as mock_del:
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert result["changed"] is True
