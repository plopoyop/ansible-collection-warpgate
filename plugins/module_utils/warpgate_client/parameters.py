"""
Global parameters management for the Warpgate API

This module provides functions to read and update the Warpgate global
parameters (singleton resource, Warpgate >= 0.24). The ``GET /parameters``
endpoint returns a ``ParameterValues`` object; ``PUT /parameters`` accepts a
``ParameterUpdate`` object with the same fields.
"""

from typing import Any, Dict

# Fields accepted by the /parameters endpoint (ParameterUpdate schema).
PARAMETER_FIELDS = (
    "allow_own_credential_management",
    "rate_limit_bytes_per_second",
    "ssh_client_auth_publickey",
    "ssh_client_auth_password",
    "ssh_client_auth_keyboard_interactive",
    "minimize_password_login",
    "ticket_self_service_enabled",
    "ticket_auto_approve_existing_access",
    "ticket_max_duration_seconds",
    "ticket_max_uses",
    "ticket_require_description",
    "ticket_request_show_all_targets",
    "target_click_action",
    "show_session_menu",
    "password_policy",
    "max_api_token_duration_seconds",
    "record_scp",
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


def get_parameters(client) -> Dict[str, Any]:
    """
    Retrieves the global parameters from the Warpgate API.

    Args:
        client: WarpgateClient instance

    Returns:
        Dict with the current ParameterValues
    """
    return client._request("GET", "/parameters")


def update_parameters(client, values: Dict[str, Any]) -> None:
    """
    Updates the global parameters in Warpgate.

    The ``ParameterUpdate`` schema requires ``allow_own_credential_management``;
    callers should pass a full object (current values merged with the desired
    changes) so unspecified fields are preserved.

    Args:
        client: WarpgateClient instance
        values: Full parameters object to send (unknown keys are dropped)
    """
    body = {k: v for k, v in values.items() if k in PARAMETER_FIELDS and v is not None}
    client._request("PUT", "/parameters", body)
