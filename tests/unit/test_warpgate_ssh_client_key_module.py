"""Tests for the warpgate_ssh_client_key module."""

from unittest.mock import MagicMock, patch

import warpgate_ssh_client_key
from warpgate_client import WarpgateAPIError
from warpgate_client.ssh_client_key import SSHClientKey


def _base_params(**overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        id=None,
        label="default-client-key",
        private_key="dummy-openssh-private-key-material",
        reference=None,
        is_default=True,
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False, client_mock=None):
    with patch("warpgate_ssh_client_key.AnsibleModule") as mock_cls:
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

        with patch("warpgate_ssh_client_key.WarpgateClient") as mock_client_cls:
            if client_mock is not None:
                mock_client_cls.return_value = client_mock
            try:
                warpgate_ssh_client_key.main()
            except SystemExit:
                pass

        return result, mod


def _existing(**overrides):
    kwargs = dict(
        id="k1",
        label="default-client-key",
        kind="ed25519",
        public_key="ssh-ed25519 AAAA",
        is_default=True,
    )
    kwargs.update(overrides)
    return SSHClientKey(**kwargs)


class TestImport:
    def test_import_new_key(self):
        created = _existing()
        params = _base_params()
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=None,
            ),
            patch(
                "warpgate_ssh_client_key.import_ssh_client_key", return_value=created
            ) as mock_import,
        ):
            result, mod = _run_module(params)
        mock_import.assert_called_once()
        assert result["changed"] is True
        assert result["id"] == "k1"
        assert result["public_key"] == "ssh-ed25519 AAAA"
        # private key must never leak into the result
        assert "private_key" not in result
        assert "secret_key" not in result

    def test_import_via_reference(self):
        created = _existing(kind="rsa")
        params = _base_params(private_key=None, reference="secret://vault/ssh#key")
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=None,
            ),
            patch(
                "warpgate_ssh_client_key.import_ssh_client_key_reference",
                return_value=created,
            ) as mock_ref,
            patch("warpgate_ssh_client_key.import_ssh_client_key") as mock_import,
        ):
            result, mod = _run_module(params)
        mock_ref.assert_called_once()
        mock_import.assert_not_called()
        assert result["changed"] is True

    def test_import_check_mode(self):
        params = _base_params()
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=None,
            ),
            patch("warpgate_ssh_client_key.import_ssh_client_key") as mock_import,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_import.assert_not_called()
        assert result["changed"] is True
        assert result["id"] == "new-ssh-client-key-id"

    def test_missing_key_material_fails(self):
        params = _base_params(private_key=None, reference=None)
        with patch(
            "warpgate_ssh_client_key.find_ssh_client_key_by_label", return_value=None
        ):
            result, mod = _run_module(params)
        assert "does not exist" in result["msg"]

    def test_missing_auth_fails(self):
        params = _base_params(token=None, api_username=None, api_password=None)
        result, mod = _run_module(params)
        assert "Provide either token" in result["msg"]

    def test_import_conflict_is_friendly(self):
        params = _base_params()
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=None,
            ),
            patch(
                "warpgate_ssh_client_key.import_ssh_client_key",
                side_effect=WarpgateAPIError(409, "already imported"),
            ),
        ):
            result, mod = _run_module(params)
        assert "already imported" in result["msg"]
        assert result["status_code"] == 409

    def test_lookup_by_id_not_found_fails(self):
        params = _base_params(id="missing")
        with patch("warpgate_ssh_client_key.get_ssh_client_keys", return_value=[]):
            result, mod = _run_module(params)
        assert "No SSH client key found with id 'missing'" in result["msg"]


class TestIdempotence:
    def test_existing_same_metadata_no_change(self):
        # Key already present with the same label/is_default; the private key
        # can't be compared, so re-applying is a no-op.
        existing = _existing()
        params = _base_params()
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=existing,
            ),
            patch("warpgate_ssh_client_key.import_ssh_client_key") as mock_import,
            patch("warpgate_ssh_client_key.update_ssh_client_key") as mock_update,
        ):
            result, mod = _run_module(params)
        mock_import.assert_not_called()
        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_lookup_by_id(self):
        existing = _existing()
        params = _base_params(id="k1")
        with (
            patch(
                "warpgate_ssh_client_key.get_ssh_client_keys",
                return_value=[existing],
            ),
            patch("warpgate_ssh_client_key.import_ssh_client_key") as mock_import,
            patch("warpgate_ssh_client_key.update_ssh_client_key") as mock_update,
        ):
            result, mod = _run_module(params)
        mock_import.assert_not_called()
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "k1"

    def test_update_check_mode_skips_call(self):
        existing = _existing(is_default=False)
        params = _base_params(is_default=True)
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=existing,
            ),
            patch("warpgate_ssh_client_key.update_ssh_client_key") as mock_update,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert result["id"] == "k1"

    def test_metadata_update_without_reimport(self):
        existing = _existing(is_default=False)
        updated = _existing(is_default=True)
        params = _base_params(is_default=True)
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=existing,
            ),
            patch("warpgate_ssh_client_key.import_ssh_client_key") as mock_import,
            patch(
                "warpgate_ssh_client_key.update_ssh_client_key", return_value=updated
            ) as mock_update,
        ):
            result, mod = _run_module(params)
        mock_import.assert_not_called()
        mock_update.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["is_default"] is False
        assert result["diff"]["after"]["is_default"] is True


class TestDelete:
    def test_delete_existing(self):
        existing = _existing()
        params = _base_params(state="absent")
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=existing,
            ),
            patch("warpgate_ssh_client_key.delete_ssh_client_key") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["after"] == {}

    def test_delete_last_key_is_friendly(self):
        existing = _existing()
        params = _base_params(state="absent")
        with (
            patch(
                "warpgate_ssh_client_key.find_ssh_client_key_by_label",
                return_value=existing,
            ),
            patch(
                "warpgate_ssh_client_key.delete_ssh_client_key",
                side_effect=WarpgateAPIError(400, "At least one SSH client key"),
            ),
        ):
            result, mod = _run_module(params)
        assert "at least one client key to remain" in result["msg"]
        assert result["status_code"] == 400

    def test_delete_nonexistent_is_noop(self):
        params = _base_params(state="absent")
        with patch(
            "warpgate_ssh_client_key.find_ssh_client_key_by_label", return_value=None
        ):
            result, mod = _run_module(params)
        assert result["changed"] is False


class TestSession:
    def test_logout_called(self):
        client = MagicMock()
        params = _base_params()
        with patch(
            "warpgate_ssh_client_key.find_ssh_client_key_by_label",
            return_value=_existing(),
        ):
            _run_module(params, client_mock=client)
        client.logout.assert_called_once_with()
