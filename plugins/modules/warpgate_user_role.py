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
module: warpgate_user_role

short_description: Manages associations between users and roles in Warpgate

description:
    - This module allows to assign and remove roles from users.

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
    user_id:
        description:
            - User ID
        type: str
        required: true
    role_id:
        description:
            - Role ID
        type: str
        required: true
    state:
        description:
            - Desired state of the association
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

EXAMPLES = """
- name: Assign a role to a user
  plopoyop.warpgate.warpgate_user_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    role_id: "role-uuid"
    state: present

- name: Remove a role from a user
  plopoyop.warpgate.warpgate_user_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    role_id: "role-uuid"
    state: absent
"""

RETURN = """
id:
    description: Association ID (format user_id:role_id)
    type: str
    returned: always
user_id:
    description: User ID
    type: str
    returned: always
role_id:
    description: Role ID
    type: str
    returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateClient,
    WarpgateClientError,
    WarpgateAPIError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.role import (
    get_user_roles,
    add_user_role,
    delete_user_role,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        user_id=dict(type="str", required=True),
        role_id=dict(type="str", required=True),
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
    user_id = module.params["user_id"]
    role_id = module.params["role_id"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": f"{user_id}:{role_id}",
        "user_id": user_id,
        "role_id": role_id,
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

        # Check if the role is already assigned
        user_roles = get_user_roles(client, user_id)
        role_assigned = any(role.id == role_id for role in user_roles)

        current_role_ids = [role.id for role in user_roles]

        if state == "present":
            if not role_assigned:
                if not module.check_mode:
                    add_user_role(client, user_id, role_id)
                result["changed"] = True
                result["diff"] = {
                    "before": {"roles": current_role_ids},
                    "after": {"roles": current_role_ids + [role_id]},
                }
        else:  # state == 'absent'
            if role_assigned:
                if not module.check_mode:
                    delete_user_role(client, user_id, role_id)
                result["changed"] = True
                result["diff"] = {
                    "before": {"roles": current_role_ids},
                    "after": {"roles": [r for r in current_role_ids if r != role_id]},
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
