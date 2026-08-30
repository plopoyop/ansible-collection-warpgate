#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_target_info

short_description: Lists Warpgate targets

description:
    - Retrieves the targets declared in Warpgate, optionally filtered by name.
    - Intended to compare the server state with the desired state of a playbook,
      for instance to delete targets whose backend no longer exists.
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
            - Return only the target whose name matches exactly.
            - Returns an empty list when no target matches.
            - Mutually exclusive with C(search).
        type: str
        required: false
    search:
        description:
            - Server-side filter passed to the Warpgate API to narrow the listing.
            - Unlike C(name) this is a partial match and may return several targets.
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
- name: List every Warpgate target
  warpgate_target_info:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
  register: warpgate_existing_targets

- name: Remove targets that are not declared in the playbook
  warpgate_target:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "{{ item }}"
    state: absent
  loop: >-
    {{ warpgate_existing_targets.targets | map(attribute='name') | difference(warpgate_wanted_targets) }}

- name: Look up a single target
  warpgate_target_info:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "db-prod"
  register: db_prod
"""

RETURN = r"""
targets:
    description: List of matching targets, empty when none matches.
    type: list
    elements: dict
    returned: always
    contains:
        id:
            description: Target ID
            type: str
        name:
            description: Target name
            type: str
        description:
            description: Target description
            type: str
        group_id:
            description: ID of the target group, empty when the target has no group
            type: str
        allow_roles:
            description: IDs of the roles allowed to access the target
            type: list
            elements: str
        options:
            description: Protocol-specific options (ssh, http, mysql, postgres, kubernetes)
            type: dict
        rate_limit_bytes_per_second:
            description: Per-target bandwidth limit in bytes/second (v0.23+), null when unset
            type: int
    sample:
        - id: "9c2a5f31-4d6e-4b7a-9c1d-2e3f4a5b6c7d"
          name: "db-prod"
          description: "Production database"
          group_id: ""
          allow_roles: []
          options: {}
          rate_limit_bytes_per_second: null
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    find_by_exact_name,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.target import (
    get_targets,
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
            match = find_by_exact_name(get_targets, client, name)
            targets = [match] if match is not None else []
        else:
            targets = get_targets(client, search=search)

        module.exit_json(changed=False, targets=[t.to_dict() for t in targets])

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
