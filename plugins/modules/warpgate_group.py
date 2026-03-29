#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_group

short_description: Manages Warpgate target groups

description:
    - Create, update and delete target groups in Warpgate.

version_added: "1.0.0"

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
    id:
        description:
            - Target group ID (for update/delete operations)
        type: str
        required: false
    name:
        description:
            - Target group name (must be unique)
        type: str
        required: true
    description:
        description:
            - Target group description
        type: str
        required: false
        default: ""
    color:
        description:
            - Target group color for UI identification
            - Valid values are Warpgate UI colors (e.g. Primary, Secondary, Success, Danger, Warning, Info, Light, Dark)
        type: str
        required: false
        default: ""
    state:
        description:
            - Desired state of the target group
        type: str
        choices: ["present", "absent"]
        default: "present"
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
- name: Create a target group
  warpgate_group:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "production"
    description: "Production environment servers"
    color: "Danger"
    state: present

- name: Delete a target group
  warpgate_group:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "production"
    state: absent
"""

RETURN = r"""
id:
    description: Target group ID
    type: str
    returned: always
name:
    description: Target group name
    type: str
    returned: always
description:
    description: Target group description
    type: str
    returned: when available
color:
    description: Target group color
    type: str
    returned: when available
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateClient,
    WarpgateClientError,
    WarpgateAPIError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.target_group import (
    get_target_groups,
    get_target_group,
    create_target_group,
    update_target_group,
    delete_target_group,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        id=dict(type="str", required=False),
        name=dict(type="str", required=True),
        description=dict(type="str", required=False, default=""),
        color=dict(type="str", required=False, default=""),
        state=dict(type="str", choices=["present", "absent"], default="present"),
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
    group_id = module.params["id"]
    name = module.params["name"]
    description = module.params["description"]
    color = module.params["color"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": None,
        "name": name,
        "description": description,
        "color": color,
    }

    try:
        client = WarpgateClient(
            host,
            token=token,
            username=api_username,
            password=api_password,
            timeout=timeout,
            insecure=insecure,
        )

        # Resolve by name if no id provided
        existing = None
        if group_id:
            existing = get_target_group(client, group_id)
        else:
            groups = get_target_groups(client, search=name)
            for g in groups:
                if g.name == name:
                    existing = g
                    group_id = g.id
                    break

        if state == "absent":
            if not existing:
                module.exit_json(**result)

            if not module.check_mode:
                delete_target_group(client, existing.id)
            result["changed"] = True
            result["id"] = existing.id
            result["diff"] = {
                "before": {
                    "name": existing.name,
                    "description": existing.description or "",
                    "color": existing.color or "",
                },
                "after": {},
            }
            module.exit_json(**result)

        # present
        if existing:
            needs_update = (
                existing.name != name
                or (existing.description or "") != (description or "")
                or (existing.color or "") != (color or "")
            )

            if needs_update:
                result["diff"] = {
                    "before": {
                        "name": existing.name,
                        "description": existing.description or "",
                        "color": existing.color or "",
                    },
                    "after": {"name": name, "description": description, "color": color},
                }
                if not module.check_mode:
                    updated = update_target_group(
                        client, existing.id, name, description, color
                    )
                    result["id"] = updated.id
                    result["description"] = updated.description
                    result["color"] = updated.color
                else:
                    result["id"] = existing.id
                result["changed"] = True
            else:
                result["id"] = existing.id
                result["description"] = existing.description
                result["color"] = existing.color

            module.exit_json(**result)

        # create
        if not module.check_mode:
            created = create_target_group(client, name, description, color)
            result["id"] = created.id
            result["description"] = created.description
            result["color"] = created.color
        else:
            result["id"] = "new-target-group-id"
        result["changed"] = True
        result["diff"] = {
            "before": {},
            "after": {"name": name, "description": description, "color": color},
        }
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
