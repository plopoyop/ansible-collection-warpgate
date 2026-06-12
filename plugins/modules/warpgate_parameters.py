#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: warpgate_parameters

short_description: Manages Warpgate global parameters

description:
    - This module configures the global parameters of a Warpgate instance
      (singleton resource, Warpgate >= 0.24).
    - Only the options you set are changed; every other parameter keeps its
      current server-side value.

version_added: "1.2.0"

options:
    host:
        description:
            - Base URL of the Warpgate instance (e.g., https://warpgate.example.com)
        type: str
        required: true
    token:
        description:
            - Warpgate API authentication token. If provided, takes priority over api_username/api_password.
        type: str
        required: false
    api_username:
        description:
            - Warpgate admin username. Use with api_password to obtain a token automatically.
        type: str
        required: false
    api_password:
        description:
            - Warpgate admin password. Use with api_username instead of token.
        type: str
        required: false
    allow_own_credential_management:
        description:
            - Allow users to manage their own credentials.
        type: bool
    rate_limit_bytes_per_second:
        description:
            - Global bandwidth limit in bytes per second.
        type: int
    ssh_client_auth_publickey:
        description:
            - Enable SSH public key authentication for clients.
        type: bool
    ssh_client_auth_password:
        description:
            - Enable SSH password authentication for clients.
        type: bool
    ssh_client_auth_keyboard_interactive:
        description:
            - Enable SSH keyboard-interactive authentication for clients.
        type: bool
    minimize_password_login:
        description:
            - Hide username/password fields behind a link, emphasizing SSO buttons.
        type: bool
    ticket_self_service_enabled:
        description:
            - Enable the ticket self-service request system.
        type: bool
    ticket_auto_approve_existing_access:
        description:
            - Automatically approve ticket requests when the requester already has access.
        type: bool
    ticket_max_duration_seconds:
        description:
            - Maximum ticket duration in seconds.
        type: int
    ticket_max_uses:
        description:
            - Maximum number of uses for tickets.
        type: int
    ticket_require_description:
        description:
            - Require a description for ticket requests.
        type: bool
    ticket_request_show_all_targets:
        description:
            - Display all targets when requesting tickets.
        type: bool
    target_click_action:
        description:
            - Action performed when clicking a target in the UI.
        type: str
        choices: ["Connect", "ShowInstructions"]
    show_session_menu:
        description:
            - Inject a session menu into HTTP sessions, allowing users to log
              out or return to the home page.
        type: bool
    password_policy:
        description:
            - Rules that user passwords must satisfy (Warpgate >= 0.25).
        type: dict
        suboptions:
            min_length:
                description: Minimum number of characters (0 = no requirement).
                type: int
            require_uppercase:
                description: Require at least one uppercase character.
                type: bool
            require_lowercase:
                description: Require at least one lowercase character.
                type: bool
            require_digits:
                description: Require at least one digit.
                type: bool
            require_special:
                description: Require at least one special character.
                type: bool
    max_api_token_duration_seconds:
        description:
            - Maximum API token duration in seconds.
        type: int
    record_scp:
        description:
            - Record SCP sessions.
        type: bool
    insecure:
        description:
            - Disables SSL certificate verification
        type: bool
        default: false
    timeout:
        description:
            - Request timeout in seconds
        type: int
        default: 30

author:
    - Clément Hubert (@plopoyop)
"""

EXAMPLES = """
- name: Configure Warpgate global parameters
  plopoyop.warpgate.warpgate_parameters:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    allow_own_credential_management: true
    show_session_menu: true
    target_click_action: "Connect"

- name: Enforce a password policy and ticket limits
  plopoyop.warpgate.warpgate_parameters:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    ticket_self_service_enabled: true
    ticket_max_duration_seconds: 86400
    ticket_max_uses: 5
    password_policy:
      min_length: 12
      require_uppercase: true
      require_lowercase: true
      require_digits: true
      require_special: false
"""

RETURN = """
parameters:
    description: The resulting global parameters
    type: dict
    returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateClient,
    WarpgateClientError,
    WarpgateAPIError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.parameters import (
    PARAMETER_FIELDS,
    PASSWORD_POLICY_FIELDS,
    get_parameters,
    update_parameters,
)


def build_desired_parameters(module, current):
    """Merges module parameters over the current server values.

    Returns the merged dict. Options left to ``None`` keep the current
    server-side value; ``password_policy`` is merged key by key so a partial
    policy does not reset the other rules.
    """
    desired = dict(current)
    for field in PARAMETER_FIELDS:
        value = module.params.get(field)
        if value is None:
            continue
        if field == "password_policy":
            merged_policy = dict(current.get("password_policy") or {})
            for policy_field in PASSWORD_POLICY_FIELDS:
                policy_value = value.get(policy_field)
                if policy_value is not None:
                    merged_policy[policy_field] = policy_value
            desired[field] = merged_policy
        else:
            desired[field] = value
    return desired


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        allow_own_credential_management=dict(type="bool", required=False),
        rate_limit_bytes_per_second=dict(type="int", required=False),
        ssh_client_auth_publickey=dict(type="bool", required=False),
        ssh_client_auth_password=dict(type="bool", required=False, no_log=False),
        ssh_client_auth_keyboard_interactive=dict(type="bool", required=False),
        minimize_password_login=dict(type="bool", required=False, no_log=False),
        ticket_self_service_enabled=dict(type="bool", required=False),
        ticket_auto_approve_existing_access=dict(type="bool", required=False),
        ticket_max_duration_seconds=dict(type="int", required=False),
        ticket_max_uses=dict(type="int", required=False),
        ticket_require_description=dict(type="bool", required=False),
        ticket_request_show_all_targets=dict(type="bool", required=False),
        target_click_action=dict(
            type="str", required=False, choices=["Connect", "ShowInstructions"]
        ),
        show_session_menu=dict(type="bool", required=False),
        password_policy=dict(
            type="dict",
            required=False,
            no_log=False,
            options=dict(
                min_length=dict(type="int", required=False),
                require_uppercase=dict(type="bool", required=False),
                require_lowercase=dict(type="bool", required=False),
                require_digits=dict(type="bool", required=False),
                require_special=dict(type="bool", required=False),
            ),
        ),
        max_api_token_duration_seconds=dict(type="int", required=False),
        record_scp=dict(type="bool", required=False),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {"changed": False, "parameters": {}}

    try:
        client = WarpgateClient(
            host,
            token=token,
            username=api_username,
            password=api_password,
            timeout=timeout,
            insecure=insecure,
        )

        current = get_parameters(client)
        desired = build_desired_parameters(module, current)

        if desired != current:
            result["changed"] = True
            result["diff"] = {"before": current, "after": desired}
            if not module.check_mode:
                update_parameters(client, desired)
        result["parameters"] = desired

        module.exit_json(**result)

    except WarpgateAPIError as e:
        module.fail_json(
            msg=f"Warpgate API error: {e.message}", status_code=e.status_code
        )
    except WarpgateClientError as e:
        module.fail_json(msg=f"Warpgate client error: {str(e)}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
