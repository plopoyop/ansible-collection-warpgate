#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_user_info

short_description: Lists Warpgate users

description:
    - Retrieves the users declared in Warpgate, optionally filtered by username.
    - Intended to compare the server state with the desired state of a playbook,
      for instance to detect users that are no longer wanted and delete them.
    - This module is read-only, it always reports C(changed=false) and runs unchanged in check mode.

version_added: "2.2.0"

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
    username:
        description:
            - Return only the user whose username matches exactly.
            - Returns an empty list when no user matches.
            - Mutually exclusive with C(search).
        type: str
        required: false
    search:
        description:
            - Server-side filter passed to the Warpgate API to narrow the listing.
            - Unlike C(username) this is a partial match and may return several users.
            - Mutually exclusive with C(username).
        type: str
        required: false
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

EXAMPLES = r"""
- name: List every Warpgate user
  warpgate_user_info:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
  register: warpgate_existing_users

- name: Remove users that are not declared in the playbook
  warpgate_user:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    username: "{{ item }}"
    state: absent
  loop: >-
    {{ warpgate_existing_users.users | map(attribute='username') | difference(warpgate_wanted_users + ['admin']) }}

- name: Look up a single user
  warpgate_user_info:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    username: "eugene"
  register: eugene
"""

RETURN = r"""
users:
    description: List of matching users, empty when none matches.
    type: list
    elements: dict
    returned: always
    contains:
        id:
            description: User ID
            type: str
        username:
            description: Username
            type: str
        description:
            description: User description
            type: str
        credential_policy:
            description: Credential policy, empty dict when unset
            type: dict
        rate_limit_bytes_per_second:
            description: Per-user bandwidth limit in bytes/second (v0.23+), null when unset
            type: int
        ldap_server_id:
            description: ID of the LDAP server this user comes from, empty for local users
            type: str
        allowed_ip_ranges:
            description: Authorized CIDR ranges for this user (v0.23+)
            type: list
            elements: str
    sample:
        - id: "0f1b0b7a-1f4e-4a5a-8a1b-2c3d4e5f6a7b"
          username: "eugene"
          description: "Eugene - WarpGate Developer"
          credential_policy: {}
          rate_limit_bytes_per_second: null
          ldap_server_id: ""
          allowed_ip_ranges: []
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    find_by_exact_name,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.user import (
    get_users,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        username=dict(type="str", required=False),
        search=dict(type="str", required=False),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[["username", "search"]],
    )

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )

    username = module.params.get("username")
    search = module.params.get("search") or ""
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    client = None

    try:
        client = WarpgateClient(
            host,
            token=token,
            username=api_username,
            password=api_password,
            timeout=timeout,
            insecure=insecure,
        )

        if username:
            match = find_by_exact_name(get_users, client, username)
            users = [match] if match is not None else []
        else:
            users = get_users(client, search=search)

        module.exit_json(changed=False, users=[user.to_dict() for user in users])

    except WarpgateAPIError as e:
        module.fail_json(
            msg=f"Warpgate API error: {e.message}", status_code=e.status_code
        )
    except WarpgateClientError as e:
        module.fail_json(msg=f"Warpgate client error: {e!s}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e!s}")
    finally:
        if client is not None:
            client.logout()


if __name__ == "__main__":
    main()
