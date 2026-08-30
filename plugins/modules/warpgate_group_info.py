#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_group_info

short_description: Lists Warpgate target groups

description:
    - Retrieves the target groups declared in Warpgate, optionally filtered by name.
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
            - Return only the target group whose name matches exactly.
            - Returns an empty list when no target group matches.
            - Mutually exclusive with C(search).
        type: str
        required: false
    search:
        description:
            - Server-side filter passed to the Warpgate API to narrow the listing.
            - Unlike C(name) this is a partial match and may return several target groups.
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
- name: List every Warpgate target group
  warpgate_group_info:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
  register: warpgate_existing_target_groups

- name: Remove target groups that are not declared in the playbook
  warpgate_group:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "{{ item }}"
    state: absent
  loop: >-
    {{ warpgate_existing_target_groups.target_groups | map(attribute='name') | difference(warpgate_wanted_groups) }}
"""

RETURN = r"""
target_groups:
    description: List of matching target groups, empty when none matches.
    type: list
    elements: dict
    returned: always
    contains:
        id:
            description: Target group ID
            type: str
        name:
            description: Target group name
            type: str
        description:
            description: Target group description
            type: str
        color:
            description: Target group color used by the Warpgate UI
            type: str
    sample:
        - id: "c4e5d6f7-8a9b-4c0d-9e1f-2a3b4c5d6e7f"
          name: "production"
          description: "Production environment servers"
          color: "Danger"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    find_by_exact_name,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.target_group import (
    get_target_groups,
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
            match = find_by_exact_name(get_target_groups, client, name)
            groups = [match] if match is not None else []
        else:
            groups = get_target_groups(client, search=search)

        module.exit_json(
            changed=False, target_groups=[group.to_dict() for group in groups]
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
