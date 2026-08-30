#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_role_info

short_description: Lists Warpgate access roles

description:
    - Retrieves the access roles declared in Warpgate, optionally filtered by name.
    - Access roles grant access to targets. For admin UI/API permissions see M(plopoyop.warpgate.warpgate_admin_role_info).
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
            - Return only the role whose name matches exactly.
            - Returns an empty list when no role matches.
            - Mutually exclusive with C(search).
        type: str
        required: false
    search:
        description:
            - Server-side filter passed to the Warpgate API to narrow the listing.
            - Unlike C(name) this is a partial match and may return several roles.
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
- name: List every Warpgate access role
  warpgate_role_info:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
  register: warpgate_existing_roles

- name: Remove roles that are not declared in the playbook
  warpgate_role:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "{{ item }}"
    state: absent
  loop: >-
    {{ warpgate_existing_roles.roles | map(attribute='name') | difference(warpgate_wanted_roles + ['warpgate:admin']) }}
"""

RETURN = r"""
roles:
    description: List of matching access roles, empty when none matches.
    type: list
    elements: dict
    returned: always
    contains:
        id:
            description: Role ID
            type: str
        name:
            description: Role name
            type: str
        description:
            description: Role description
            type: str
        is_default:
            description: Whether the role is auto-assigned to newly created users (v0.24+)
            type: bool
    sample:
        - id: "3b8e1c22-7a4d-4f0b-8e91-5d6c7b8a9f01"
          name: "developers"
          description: "Role for development team"
          is_default: false
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    find_by_exact_name,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.role import (
    get_roles,
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

        if name:
            match = find_by_exact_name(get_roles, client, name)
            roles = [match] if match is not None else []
        else:
            roles = get_roles(client, search=search)

        module.exit_json(changed=False, roles=[role.to_dict() for role in roles])

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
