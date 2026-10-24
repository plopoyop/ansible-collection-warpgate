"""Tests for the warpgate_secret_backend module."""

from unittest.mock import MagicMock, patch

import warpgate_secret_backend
from warpgate_client.secret_backend import SecretBackend


def _base_params(**overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        id=None,
        name="vault-prod",
        backend_type="vault",
        address="https://vault.example.com:8200",
        namespace="",
        auth={"method": "Token", "token": "s.secret"},
        tls_skip_verify=False,
        allowed_paths=["secret/data/warpgate"],
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False, client_mock=None):
    with patch("warpgate_secret_backend.AnsibleModule") as mock_cls:
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

        with patch("warpgate_secret_backend.WarpgateClient") as mock_client_cls:
            if client_mock is not None:
                mock_client_cls.return_value = client_mock
            try:
                warpgate_secret_backend.main()
            except SystemExit:
                pass

        return result, mod


def _existing(**overrides):
    kwargs = dict(
        id="sb1",
        name="vault-prod",
        backend_type="vault",
        address="https://vault.example.com:8200",
        namespace="",
        # GET blanks the stored secret:
        auth={"method": "Token", "token": ""},
        tls_skip_verify=False,
        allowed_paths=["secret/data/warpgate"],
    )
    kwargs.update(overrides)
    return SecretBackend(**kwargs)


class TestCreate:
    def test_create_new_backend(self):
        created = _existing()
        params = _base_params()
        with (
            patch("warpgate_secret_backend.get_secret_backends", return_value=[]),
            patch(
                "warpgate_secret_backend.create_secret_backend", return_value=created
            ) as mock_create,
        ):
            result, mod = _run_module(params)
        mock_create.assert_called_once()
        assert result["changed"] is True
        assert result["id"] == "sb1"
        assert result["diff"]["before"] == {}
        assert result["diff"]["after"]["backend_type"] == "vault"

    def test_create_check_mode(self):
        params = _base_params()
        with (
            patch("warpgate_secret_backend.get_secret_backends", return_value=[]),
            patch("warpgate_secret_backend.create_secret_backend") as mock_create,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert result["id"] == "new-secret-backend-id"


class TestUpdate:
    def test_idempotent_when_only_secret_differs(self):
        # The server blanks the stored token, so re-applying the same config
        # (with the real token) must not report a change.
        existing = _existing()
        params = _base_params()
        with (
            patch(
                "warpgate_secret_backend.get_secret_backends", return_value=[existing]
            ),
            patch("warpgate_secret_backend.update_secret_backend") as mock_update,
        ):
            result, mod = _run_module(params)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert "diff" not in result

    def test_update_on_field_change(self):
        existing = _existing(address="https://old.example.com:8200")
        updated = _existing()
        params = _base_params()
        with (
            patch(
                "warpgate_secret_backend.get_secret_backends", return_value=[existing]
            ),
            patch(
                "warpgate_secret_backend.update_secret_backend", return_value=updated
            ) as mock_update,
        ):
            result, mod = _run_module(params)
        mock_update.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["address"] == "https://old.example.com:8200"
        assert result["diff"]["after"]["address"] == "https://vault.example.com:8200"

    def test_update_on_auth_method_change(self):
        existing = _existing(
            auth={"method": "AppRole", "role_id": "r", "secret_id": ""}
        )
        params = _base_params()
        with (
            patch(
                "warpgate_secret_backend.get_secret_backends", return_value=[existing]
            ),
            patch(
                "warpgate_secret_backend.update_secret_backend", return_value=existing
            ) as mock_update,
        ):
            result, mod = _run_module(params)
        mock_update.assert_called_once()
        assert result["changed"] is True


class TestDelete:
    def test_delete_existing(self):
        existing = _existing()
        params = _base_params(state="absent")
        with (
            patch(
                "warpgate_secret_backend.get_secret_backends", return_value=[existing]
            ),
            patch("warpgate_secret_backend.delete_secret_backend") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["after"] == {}

    def test_delete_nonexistent_is_noop(self):
        params = _base_params(state="absent")
        with patch("warpgate_secret_backend.get_secret_backends", return_value=[]):
            result, mod = _run_module(params)
        assert result["changed"] is False


class TestSession:
    def test_logout_called_on_success(self):
        client = MagicMock()
        params = _base_params()
        with patch(
            "warpgate_secret_backend.get_secret_backends", return_value=[_existing()]
        ):
            _run_module(params, client_mock=client)
        client.logout.assert_called_once_with()
