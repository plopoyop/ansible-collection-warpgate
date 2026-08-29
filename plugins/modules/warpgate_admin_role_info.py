#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_admin_role_info

short_description: Lists Warpgate admin roles

description:
    - Retrieves the admin roles declared in Warpgate (v0.23+), optionally filtered by name.
    - Admin roles grant permissions on the admin UI/API itself. For access roles see
      M(plopoyop.warpgate.warpgate_role_info).
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
    name:
        description:
            - Return only the admin role whose name matches exactly.
            - Returns an empty list when no admin role matches.
            - Mutually exclusive with C(search).
        type: str
        required: false
    search:
        description:
            - Case-insensitive substring filter on the admin role name.
            - The admin roles endpoint has no server-side search parameter, so the
              full listing is fetched and filtered locally.
            - Mutually exclusive with C(name).
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
- name: List every Warpgate admin role
  warpgate_admin_role_info:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
  register: warpgate_existing_admin_roles

- name: Report admin roles allowed to delete users
  ansible.builtin.debug:
    msg: >-
      {{ warpgate_existing_admin_roles.admin_roles
         | selectattr('permissions.users_delete')
         | map(attribute='name') | list }}
"""

RETURN = r"""
admin_roles:
    description: List of matching admin roles, empty when none matches.
    type: list
    elements: dict
    returned: always
    contains:
        id:
            description: Admin role ID
            type: str
        name:
            description: Admin role name
            type: str
        description:
            description: Admin role description
            type: str
        permissions:
            description:
                - Full permission set of the admin role.
                - Every permission is always present, defaulting to C(false).
            type: dict
    sample:
        - id: "7f6e5d4c-3b2a-4190-8f7e-6d5c4b3a2910"
          name: "auditor"
          description: "Read-only admin used by auditors"
          permissions:
            sessions_view: true
            recordings_view: true
            users_delete: false
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.admin_role import (
    get_admin_roles,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        name=dict(type="str", required=False),
        search=dict(type="str", required=False),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[["name", "search"]],
    )

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )

    name = module.params.get("name")
    search = module.params.get("search")
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

        admin_roles = get_admin_roles(client)
        if name:
            admin_roles = [role for role in admin_roles if role.name == name]
        elif search:
            needle = search.lower()
            admin_roles = [
                role for role in admin_roles if needle in (role.name or "").lower()
            ]

        module.exit_json(
            changed=False, admin_roles=[role.to_dict() for role in admin_roles]
        )

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
