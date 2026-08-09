#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: warpgate_admin_role

short_description: Manages Warpgate admin roles (v0.23+)

description:
    - Create, update and delete Warpgate admin roles.
    - Admin roles grant fine-grained permissions on the admin UI / API
      (target/user/access-role/session/recording/ticket/config management).
      They are distinct from access roles which control what backends a
      user may reach.

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
            - Admin role ID (for update/delete operations by ID).
        type: str
        required: false
    name:
        description:
            - Admin role name.
        type: str
        required: true
    description:
        description:
            - Admin role description.
        type: str
        required: false
        default: ""
    permissions:
        description:
            - Boolean flags for each admin permission. Omitted flags default to C(false).
        type: dict
        required: false
        default: {}
        suboptions:
            targets_create: {description: Create targets., type: bool, default: false}
            targets_edit: {description: Edit targets., type: bool, default: false}
            targets_delete: {description: Delete targets., type: bool, default: false}
            users_create: {description: Create users., type: bool, default: false}
            users_edit: {description: Edit users., type: bool, default: false}
            users_delete: {description: Delete users., type: bool, default: false}
            access_roles_create: {description: Create access roles., type: bool, default: false}
            access_roles_edit: {description: Edit access roles., type: bool, default: false}
            access_roles_delete: {description: Delete access roles., type: bool, default: false}
            access_roles_assign: {description: Assign access roles to users/targets., type: bool, default: false}
            sessions_view: {description: View live sessions., type: bool, default: false}
            sessions_terminate: {description: Terminate live sessions., type: bool, default: false}
            recordings_view: {description: View session recordings., type: bool, default: false}
            tickets_create: {description: Create tickets., type: bool, default: false}
            tickets_delete: {description: Delete tickets., type: bool, default: false}
            config_edit: {description: Edit server configuration., type: bool, default: false}
            admin_roles_manage: {description: Manage admin roles themselves., type: bool, default: false}
    state:
        description:
            - Desired state of the admin role.
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
- name: Create a read-only admin role
  plopoyop.warpgate.warpgate_admin_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "auditor"
    description: "Read-only admin (audit)."
    permissions:
      sessions_view: true
      recordings_view: true
    state: present

- name: Delete an admin role by name
  plopoyop.warpgate.warpgate_admin_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "auditor"
    state: absent
"""

RETURN = """
id:
    description: Admin role ID.
    type: str
    returned: always
name:
    description: Admin role name.
    type: str
    returned: always
description:
    description: Admin role description.
    type: str
    returned: when available
permissions:
    description: Map of permission flags applied to the role.
    type: dict
    returned: when available
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.admin_role import (
    PERMISSION_FIELDS,
    create_admin_role,
    delete_admin_role,
    get_admin_role,
    get_admin_roles,
    update_admin_role,
)


def _permissions_from_params(perm_params):
    """Normalize the ``permissions`` sub-dict into a full map of booleans."""
    perms = {f: False for f in PERMISSION_FIELDS}
    if perm_params:
        for f in PERMISSION_FIELDS:
            if perm_params.get(f) is not None:
                perms[f] = bool(perm_params[f])
    return perms


def _permissions_suboptions():
    return {f: dict(type="bool", default=False) for f in PERMISSION_FIELDS}


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        id=dict(type="str", required=False),
        name=dict(type="str", required=True),
        description=dict(type="str", required=False, default=""),
        permissions=dict(
            type="dict",
            required=False,
            default={},
            options=_permissions_suboptions(),
        ),
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

    role_id = module.params["id"]
    name = module.params["name"]
    description = module.params["description"]
    permissions = _permissions_from_params(module.params.get("permissions"))
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": None,
        "name": name,
        "description": description,
        "permissions": permissions,
    }

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

        existing = None
        if role_id:
            existing = get_admin_role(client, role_id)
        else:
            for r in get_admin_roles(client):
                if r.name == name:
                    existing = r
                    role_id = r.id
                    break

        if state == "absent":
            if existing is not None:
                if not module.check_mode:
                    delete_admin_role(client, existing.id)
                result["changed"] = True
                result["id"] = existing.id
                result["diff"] = {
                    "before": {
                        "name": existing.name,
                        "description": existing.description,
                        "permissions": existing.permissions,
                    },
                    "after": {},
                }
            module.exit_json(**result)

        # state == present
        if existing is None:
            if not module.check_mode:
                created = create_admin_role(client, name, description, permissions)
                result["id"] = created.id
                result["permissions"] = created.permissions
            else:
                result["id"] = "new-admin-role-id"
            result["changed"] = True
            result["diff"] = {
                "before": {},
                "after": {
                    "name": name,
                    "description": description,
                    "permissions": permissions,
                },
            }
        else:
            needs_update = (
                existing.name != name
                or (existing.description or "") != (description or "")
                or existing.permissions != permissions
            )
            if needs_update:
                if not module.check_mode:
                    updated = update_admin_role(
                        client, existing.id, name, description, permissions
                    )
                    result["id"] = updated.id
                    result["permissions"] = updated.permissions
                else:
                    result["id"] = existing.id
                result["changed"] = True
                result["diff"] = {
                    "before": {
                        "name": existing.name,
                        "description": existing.description,
                        "permissions": existing.permissions,
                    },
                    "after": {
                        "name": name,
                        "description": description,
                        "permissions": permissions,
                    },
                }
            else:
                result["id"] = existing.id
                result["permissions"] = existing.permissions

        module.exit_json(**result)

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
