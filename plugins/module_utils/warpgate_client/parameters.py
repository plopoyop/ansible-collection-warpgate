"""
Global parameters management for the Warpgate API

This module provides functions to read and update the Warpgate global
parameters (singleton resource, Warpgate >= 0.24). The ``GET /parameters``
endpoint returns a ``ParameterValues`` object; ``PUT /parameters`` accepts a
``ParameterUpdate`` object with the same fields.

Warpgate 0.26 replaces the writable ``minimize_password_login`` boolean with
the ``password_login_mode`` enum and adds the login-protection (brute-force),
SSH banner, WebSSH and analytics parameters. ``minimize_password_login`` is
still returned by ``GET`` (deprecated, derived from ``password_login_mode``)
but is no longer accepted by ``PUT``.

Warpgate 0.27 renames ``ssh_banner`` to ``banner`` and ``web_ssh_enabled`` to
``web_clients_enabled`` (``web_ssh_enabled`` stays as a deprecated read-only
alias in ``GET``), and adds the ``ssh_host_key_verification`` mode, the web
reauthentication settings (``web_auth_max_age_seconds``,
``web_approval_grace_period_seconds``) and the session-recording parameters
(``recordings_enable`` and the ``recordings_storage`` disk/S3 config).

Warpgate 0.28 adds the ``open_targets_in_new_tab`` mode.
"""

from typing import Any

# Fields accepted by the /parameters endpoint (ParameterUpdate schema).
PARAMETER_FIELDS = (
    "allow_own_credential_management",
    "rate_limit_bytes_per_second",
    "ssh_client_auth_publickey",
    "ssh_client_auth_password",
    "ssh_client_auth_keyboard_interactive",
    "ssh_host_key_verification",
    "password_login_mode",
    "ticket_self_service_enabled",
    "ticket_auto_approve_existing_access",
    "ticket_max_duration_seconds",
    "ticket_max_uses",
    "ticket_require_description",
    "ticket_request_show_all_targets",
    "target_click_action",
    "open_targets_in_new_tab",
    "show_session_menu",
    "password_policy",
    "max_api_token_duration_seconds",
    "record_scp",
    "login_protection_enabled",
    "login_protection_retention_seconds",
    "lp_ip_max_attempts",
    "lp_ip_time_window_seconds",
    "lp_ip_base_block_duration_seconds",
    "lp_ip_block_duration_multiplier",
    "lp_ip_max_block_duration_seconds",
    "lp_ip_cooldown_reset_seconds",
    "lp_user_max_attempts",
    "lp_user_time_window_seconds",
    "lp_user_auto_unlock",
    "lp_user_lockout_duration_seconds",
    "lp_user_exempt_admins",
    "banner",
    "web_clients_enabled",
    "web_auth_max_age_seconds",
    "web_approval_grace_period_seconds",
    "analytics_consent",
    "analytics_normal",
    "recordings_enable",
    "recordings_storage",
)

# Sub-fields of the password_policy object (PasswordPolicy schema).
PASSWORD_POLICY_FIELDS = (
    "min_length",
    "require_uppercase",
    "require_lowercase",
    "require_digits",
    "require_special",
)

TARGET_CLICK_ACTIONS = ("Connect", "ShowInstructions")

# open_targets_in_new_tab enum (Warpgate >= 0.28).
OPEN_TARGETS_IN_NEW_TAB_MODES = ("DefaultOn", "DefaultOff", "ForcedOn", "ForcedOff")

# password_login_mode enum (Warpgate >= 0.26).
PASSWORD_LOGIN_MODES = ("Enabled", "Minimized", "Disabled")

# analytics_consent enum (Warpgate >= 0.26).
ANALYTICS_CONSENT_VALUES = ("Undecided", "Off", "On")

# ssh_host_key_verification enum (Warpgate >= 0.27).
SSH_HOST_KEY_VERIFICATION_MODES = ("Prompt", "AutoAccept", "AutoReject", "Ignore")


def get_parameters(client) -> dict[str, Any]:
    """
    Retrieves the global parameters from the Warpgate API.

    Args:
        client: WarpgateClient instance

    Returns:
        Dict with the current ParameterValues
    """
    return client._request("GET", "/parameters")


def update_parameters(client, values: dict[str, Any]) -> None:
    """
    Updates the global parameters in Warpgate.

    Every field of the ``ParameterUpdate`` schema is optional (Warpgate >= 0.26);
    callers should still pass a full object (current values merged with the
    desired changes) so unspecified fields are preserved. Keys not in
    :data:`PARAMETER_FIELDS` (e.g. the deprecated ``minimize_password_login``)
    and ``None`` values are dropped from the request body.

    Args:
        client: WarpgateClient instance
        values: Full parameters object to send (unknown keys are dropped)
    """
    body = {k: v for k, v in values.items() if k in PARAMETER_FIELDS and v is not None}
    client._request("PUT", "/parameters", body)
