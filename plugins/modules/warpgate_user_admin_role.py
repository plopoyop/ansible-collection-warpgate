#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: warpgate_user_admin_role

short_description: Grants or revokes admin roles on a Warpgate user (v0.23+)

description:
    - Manages the assignment of admin roles to a user. Admin roles are
      distinct from access roles and grant fine-grained permissions on
      the Warpgate admin API/UI.

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
            - User UUID.
        type: str
        required: true
    admin_role:
        description:
            - Admin role UUID or name to grant/revoke.
        type: str
        required: true
    state:
        description:
            - Desired state of the assignment.
        type: str
        choices: ["present", "absent"]
        default: "present"
    insecure:
        description:
            - Disables SSL certificate verification.
        type: bool
        default: false
    timeout:
        description:
            - Request timeout in seconds.
        type: int
        default: 30

author:
    - Clément Hubert (@plopoyop)
"""

EXAMPLES = """
- name: Grant the "auditor" admin role to a user
  plopoyop.warpgate.warpgate_user_admin_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    admin_role: "auditor"
    state: present

- name: Revoke an admin role
  plopoyop.warpgate.warpgate_user_admin_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    admin_role: "auditor"
    state: absent
"""

RETURN = """
id:
    description: Association ID (format user_id:admin_role_id).
    type: str
    returned: always
user_id:
    description: User ID.
    type: str
    returned: always
admin_role_id:
    description: Admin role ID.
    type: str
    returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.admin_role import (
    add_user_admin_role,
    delete_user_admin_role,
    get_user_admin_roles,
    resolve_admin_role_id,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        user_id=dict(type="str", required=True),
        admin_role=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )

    user_id = module.params["user_id"]
    admin_role_spec = module.params["admin_role"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    try:
        client = WarpgateClient(
            host,
            token=token,
            username=api_username,
            password=api_password,
            timeout=timeout,
            insecure=insecure,
        )

        try:
            admin_role_id = resolve_admin_role_id(client, admin_role_spec)
        except ValueError as e:
            module.fail_json(msg=str(e))

        current = [r.id for r in get_user_admin_roles(client, user_id)]
        assigned = admin_role_id in current

        result = {
            "changed": False,
            "id": f"{user_id}:{admin_role_id}",
            "user_id": user_id,
            "admin_role_id": admin_role_id,
        }

        if state == "present" and not assigned:
            if not module.check_mode:
                add_user_admin_role(client, user_id, admin_role_id)
            result["changed"] = True
            result["diff"] = {
                "before": {"admin_roles": current},
                "after": {"admin_roles": current + [admin_role_id]},
            }
        elif state == "absent" and assigned:
            if not module.check_mode:
                delete_user_admin_role(client, user_id, admin_role_id)
            result["changed"] = True
            result["diff"] = {
                "before": {"admin_roles": current},
                "after": {"admin_roles": [r for r in current if r != admin_role_id]},
            }

        module.exit_json(**result)

    except WarpgateAPIError as e:
        module.fail_json(
            msg=f"Warpgate API error: {e.message}", status_code=e.status_code
        )
    except WarpgateClientError as e:
        module.fail_json(msg=f"Warpgate client error: {e!s}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e!s}")


if __name__ == "__main__":
    main()
