"""Tests for warpgate_password_credential module."""

from unittest.mock import MagicMock, patch

import warpgate_password_credential
from warpgate_client.client import WarpgateAPIError
from warpgate_client.credential import PasswordCredential

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
        password="s3cret",
        update_password="on_create",
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    with patch("warpgate_password_credential.AnsibleModule") as mock_cls:
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

        with patch("warpgate_password_credential.WarpgateClient"):
            try:
                warpgate_password_credential.main()
            except SystemExit:
                pass

        return result, mod


# ---------------------------------------------------------------------------
# Create (on_create)
# ---------------------------------------------------------------------------


class TestPasswordCredentialCreate:
    def test_create_when_no_existing(self):
        new_cred = PasswordCredential(id="c1")
        params = _base_params()
        with (
            patch(
                "warpgate_password_credential.get_password_credentials", return_value=[]
            ),
            patch(
                "warpgate_password_credential.add_password_credential",
                return_value=new_cred,
            ),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["credential_id"] == "c1"
        assert result["diff"]["before"]["password_credentials_count"] == 0
        assert result["diff"]["after"]["password_credentials_count"] == 1

    def test_on_create_existing_is_noop(self):
        existing = [PasswordCredential(id="c1")]
        params = _base_params()
        with patch(
            "warpgate_password_credential.get_password_credentials",
            return_value=existing,
        ):
            result, mod = _run_module(params)
        assert result["changed"] is False
        assert "diff" not in result

    def test_always_replaces_credentials(self):
        existing = [PasswordCredential(id="c1")]
        new_cred = PasswordCredential(id="c2")
        params = _base_params(update_password="always")
        with (
            patch(
                "warpgate_password_credential.get_password_credentials",
                return_value=existing,
            ),
            patch(
                "warpgate_password_credential.delete_password_credential"
            ) as mock_del,
            patch(
                "warpgate_password_credential.add_password_credential",
                return_value=new_cred,
            ),
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["password_credentials_count"] == 1

    def test_always_keeps_old_password_when_new_one_is_rejected(self):
        params = _base_params(update_password="always")
        with (
            patch(
                "warpgate_password_credential.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch(
                "warpgate_password_credential.delete_password_credential"
            ) as mock_del,
            patch(
                "warpgate_password_credential.add_password_credential",
                side_effect=WarpgateAPIError(400, "rejected"),
            ),
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        assert "rejected" in result["msg"]

    def test_always_adds_before_deleting(self):
        calls = []
        params = _base_params(update_password="always")
        with (
            patch(
                "warpgate_password_credential.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch(
                "warpgate_password_credential.delete_password_credential",
                side_effect=lambda *a: calls.append("delete"),
            ),
            patch(
                "warpgate_password_credential.add_password_credential",
                side_effect=lambda *a: (
                    calls.append("add") or PasswordCredential(id="c2")
                ),
            ),
        ):
            result, mod = _run_module(params)
        assert calls == ["add", "delete"]

    def test_always_delete_error_fails(self):
        params = _base_params(update_password="always")
        with (
            patch(
                "warpgate_password_credential.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch(
                "warpgate_password_credential.delete_password_credential",
                side_effect=WarpgateAPIError(500, "boom"),
            ),
            patch(
                "warpgate_password_credential.add_password_credential",
                return_value=PasswordCredential(id="c2"),
            ),
        ):
            result, mod = _run_module(params)
        assert "boom" in result["msg"]
        assert result["changed"] is True

    def test_create_check_mode(self):
        params = _base_params()
        with (
            patch(
                "warpgate_password_credential.get_password_credentials", return_value=[]
            ),
            patch("warpgate_password_credential.add_password_credential") as mock_add,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_add.assert_not_called()
        assert result["changed"] is True


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestPasswordCredentialDelete:
    def _patch_existing(self, *ids):
        return patch(
            "warpgate_password_credential.get_password_credentials",
            return_value=[PasswordCredential(id=i) for i in ids],
        )

    def test_delete_credential(self):
        params = _base_params(state="absent", credential_id="c1", password=None)
        with (
            self._patch_existing("c1"),
            patch(
                "warpgate_password_credential.delete_password_credential"
            ) as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["credential_id"] == "c1"
        assert result["diff"]["after"] == {}

    def test_delete_check_mode(self):
        params = _base_params(state="absent", credential_id="c1", password=None)
        with (
            self._patch_existing("c1"),
            patch(
                "warpgate_password_credential.delete_password_credential"
            ) as mock_del,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert result["changed"] is True

    def test_delete_missing_is_noop(self):
        params = _base_params(state="absent", credential_id="c1", password=None)
        with (
            self._patch_existing("c2"),
            patch("warpgate_password_credential.get_user", return_value=object()),
            patch(
                "warpgate_password_credential.delete_password_credential"
            ) as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        assert result["changed"] is False


class TestPasswordCredentialDeleteUnknownUser:
    def test_unknown_user_fails(self):
        params = _base_params(state="absent", credential_id="c1", password=None)
        with (
            patch(
                "warpgate_password_credential.get_password_credentials",
                return_value=[],
            ),
            patch("warpgate_password_credential.get_user", return_value=None),
            patch(
                "warpgate_password_credential.delete_password_credential"
            ) as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        assert "not found" in result["msg"]


class TestPasswordCredentialTransportError:
    def test_client_error_after_add_reports_changed(self):
        from warpgate_client.client import WarpgateClientError

        params = _base_params(update_password="always")
        with (
            patch(
                "warpgate_password_credential.get_password_credentials",
                return_value=[PasswordCredential(id="c1")],
            ),
            patch(
                "warpgate_password_credential.add_password_credential",
                return_value=PasswordCredential(id="c2"),
            ),
            patch(
                "warpgate_password_credential.delete_password_credential",
                side_effect=WarpgateClientError("timeout"),
            ),
        ):
            result, mod = _run_module(params)
        assert "timeout" in result["msg"]
        assert result["changed"] is True
