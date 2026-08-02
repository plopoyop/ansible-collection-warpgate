"""Tests for warpgate_parameters module and the parameters client."""

from unittest.mock import MagicMock, patch

import warpgate_parameters
from warpgate_client.parameters import get_parameters, update_parameters

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CURRENT = {
    "allow_own_credential_management": True,
    "ssh_client_auth_publickey": True,
    "ssh_client_auth_password": True,
    "ssh_client_auth_keyboard_interactive": True,
    # Deprecated read-only field still returned by GET (Warpgate >= 0.26),
    # derived from password_login_mode.
    "minimize_password_login": False,
    "password_login_mode": "Enabled",
    "ticket_self_service_enabled": False,
    "ticket_auto_approve_existing_access": False,
    "ticket_require_description": False,
    "ticket_request_show_all_targets": False,
    "target_click_action": "Connect",
    "show_session_menu": True,
    "password_policy": {
        "min_length": 0,
        "require_uppercase": False,
        "require_lowercase": False,
        "require_digits": False,
        "require_special": False,
    },
    "record_scp": False,
    "ssh_host_key_verification": "Prompt",
    "login_protection_enabled": True,
    "lp_ip_max_attempts": 5,
    "lp_ip_block_duration_multiplier": 2.0,
    "lp_user_max_attempts": 10,
    "lp_user_exempt_admins": True,
    "banner": "",
    # Deprecated read-only alias still returned by GET (Warpgate >= 0.27),
    # mirrors web_clients_enabled.
    "web_ssh_enabled": True,
    "web_clients_enabled": True,
    "web_auth_max_age_seconds": None,
    "web_approval_grace_period_seconds": None,
    "analytics_consent": "Undecided",
    "analytics_normal": False,
    "recordings_enable": False,
    "recordings_storage": {"kind": "Disk", "path": "./data/recordings"},
}


def _base_params(**overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        allow_own_credential_management=None,
        rate_limit_bytes_per_second=None,
        ssh_client_auth_publickey=None,
        ssh_client_auth_password=None,
        ssh_client_auth_keyboard_interactive=None,
        ssh_host_key_verification=None,
        minimize_password_login=None,
        password_login_mode=None,
        ticket_self_service_enabled=None,
        ticket_auto_approve_existing_access=None,
        ticket_max_duration_seconds=None,
        ticket_max_uses=None,
        ticket_require_description=None,
        ticket_request_show_all_targets=None,
        target_click_action=None,
        show_session_menu=None,
        password_policy=None,
        max_api_token_duration_seconds=None,
        record_scp=None,
        login_protection_enabled=None,
        login_protection_retention_seconds=None,
        lp_ip_max_attempts=None,
        lp_ip_time_window_seconds=None,
        lp_ip_base_block_duration_seconds=None,
        lp_ip_block_duration_multiplier=None,
        lp_ip_max_block_duration_seconds=None,
        lp_ip_cooldown_reset_seconds=None,
        lp_user_max_attempts=None,
        lp_user_time_window_seconds=None,
        lp_user_auto_unlock=None,
        lp_user_lockout_duration_seconds=None,
        lp_user_exempt_admins=None,
        banner=None,
        web_clients_enabled=None,
        web_auth_max_age_seconds=None,
        web_approval_grace_period_seconds=None,
        analytics_consent=None,
        analytics_normal=None,
        recordings_enable=None,
        recordings_storage=None,
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    """Run the module main() and capture exit_json / fail_json."""
    with patch("warpgate_parameters.AnsibleModule") as mock_cls:
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

        with patch("warpgate_parameters.WarpgateClient"):
            try:
                warpgate_parameters.main()
            except SystemExit:
                pass

        return result, mod


# ---------------------------------------------------------------------------
# Client functions
# ---------------------------------------------------------------------------


class TestParametersClient:
    def test_get_parameters(self, mock_client):
        mock_client._request.return_value = dict(CURRENT)
        assert get_parameters(mock_client) == CURRENT
        mock_client._request.assert_called_once_with("GET", "/parameters")

    def test_update_parameters_filters_unknown_keys(self, mock_client):
        values = dict(CURRENT)
        values["id"] = "parameters"  # read-only key returned by GET
        update_parameters(mock_client, values)
        method, path, body = mock_client._request.call_args[0]
        assert (method, path) == ("PUT", "/parameters")
        assert "id" not in body
        # Deprecated, read-only: must not be sent back on PUT.
        assert "minimize_password_login" not in body  # 0.26
        assert "web_ssh_enabled" not in body  # 0.27 (renamed to web_clients_enabled)
        assert body["password_login_mode"] == "Enabled"
        assert body["web_clients_enabled"] is True
        assert body["allow_own_credential_management"] is True

    def test_update_parameters_drops_none_values(self, mock_client):
        values = dict(CURRENT)
        values["rate_limit_bytes_per_second"] = None
        update_parameters(mock_client, values)
        body = mock_client._request.call_args[0][2]
        assert "rate_limit_bytes_per_second" not in body


# ---------------------------------------------------------------------------
# Module behaviour
# ---------------------------------------------------------------------------


class TestParametersModule:
    def test_no_change_when_values_match(self):
        params = _base_params(show_session_menu=True)
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert "diff" not in result

    def test_change_triggers_update(self):
        params = _base_params(show_session_menu=False, record_scp=True)
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        mock_update.assert_called_once()
        sent = mock_update.call_args[0][1]
        assert sent["show_session_menu"] is False
        assert sent["record_scp"] is True
        # unspecified values are preserved from the server
        assert sent["allow_own_credential_management"] is True
        assert result["changed"] is True
        assert result["diff"]["before"]["show_session_menu"] is True
        assert result["diff"]["after"]["show_session_menu"] is False

    def test_check_mode_no_update_call(self):
        params = _base_params(record_scp=True)
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True

    def test_password_policy_partial_merge(self):
        params = _base_params(
            password_policy={
                "min_length": 12,
                "require_uppercase": None,
                "require_lowercase": None,
                "require_digits": None,
                "require_special": None,
            }
        )
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        sent = mock_update.call_args[0][1]
        assert sent["password_policy"]["min_length"] == 12
        # other policy rules preserved from the server
        assert sent["password_policy"]["require_uppercase"] is False
        assert result["changed"] is True

    def test_target_click_action_change(self):
        params = _base_params(target_click_action="ShowInstructions")
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        sent = mock_update.call_args[0][1]
        assert sent["target_click_action"] == "ShowInstructions"
        assert result["changed"] is True

    def test_password_login_mode_change(self):
        params = _base_params(password_login_mode="Disabled")
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        sent = mock_update.call_args[0][1]
        assert sent["password_login_mode"] == "Disabled"
        assert result["changed"] is True

    def test_minimize_password_login_maps_to_mode(self):
        params = _base_params(minimize_password_login=True)
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        mod.deprecate.assert_called_once()
        sent = mock_update.call_args[0][1]
        assert sent["password_login_mode"] == "Minimized"
        assert result["changed"] is True

    def test_login_protection_field_change(self):
        params = _base_params(lp_ip_max_attempts=3, web_clients_enabled=False)
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        sent = mock_update.call_args[0][1]
        assert sent["lp_ip_max_attempts"] == 3
        assert sent["web_clients_enabled"] is False
        assert result["changed"] is True

    def test_banner_set(self):
        params = _base_params(banner="Authorized access only.")
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        sent = mock_update.call_args[0][1]
        assert sent["banner"] == "Authorized access only."
        assert result["changed"] is True

    def test_ssh_host_key_verification_change(self):
        params = _base_params(ssh_host_key_verification="AutoReject")
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        sent = mock_update.call_args[0][1]
        assert sent["ssh_host_key_verification"] == "AutoReject"
        assert result["changed"] is True

    def test_recordings_storage_preserved_when_unset(self):
        params = _base_params(recordings_enable=True)
        with (
            patch("warpgate_parameters.get_parameters", return_value=dict(CURRENT)),
            patch("warpgate_parameters.update_parameters") as mock_update,
        ):
            result, mod = _run_module(params)
        sent = mock_update.call_args[0][1]
        assert sent["recordings_enable"] is True
        # unmanaged storage is round-tripped unchanged from the server
        assert sent["recordings_storage"] == CURRENT["recordings_storage"]
        assert result["changed"] is True
