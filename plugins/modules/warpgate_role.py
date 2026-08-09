#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: warpgate_role

short_description: Manages Warpgate roles

description:
    - This module allows to create, modify and delete roles in Warpgate.

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
            - Role ID (for update/delete operations)
        type: str
        required: false
    name:
        description:
            - Role name
        type: str
        required: true
    description:
        description:
            - Role description
        type: str
        required: false
        default: ""
    is_default:
        description:
            - Automatically assign this role to newly created users (Warpgate >= 0.24).
            - When unset, the existing server-side value is preserved.
        type: bool
        required: false
    state:
        description:
            - Desired state of the role
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
- name: Create a Warpgate role
  plopoyop.warpgate.warpgate_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "developers"
    description: "Role for development team"
    state: present

- name: Create a default role (auto-assigned to new users)
  plopoyop.warpgate.warpgate_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "everyone"
    description: "Baseline access"
    is_default: true
    state: present

- name: Update a role
  plopoyop.warpgate.warpgate_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    id: "role-uuid"
    name: "developers"
    description: "Updated description"
    state: present

- name: Delete a role
  plopoyop.warpgate.warpgate_role:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    id: "role-uuid"
    name: "developers"
    state: absent
"""

RETURN = """
id:
    description: Role ID
    type: str
    returned: always
name:
    description: Role name
    type: str
    returned: always
description:
    description: Role description
    type: str
    returned: when available
is_default:
    description: Whether the role is auto-assigned to new users
    type: bool
    returned: when available
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    find_id_by_exact_name,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.role import (
    create_role,
    delete_role,
    get_role,
    get_roles,
    update_role,
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
        is_default=dict(type="bool", required=False),
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
    role_id = module.params["id"]
    name = module.params["name"]
    description = module.params["description"]
    is_default = module.params.get("is_default")
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {"changed": False, "id": None, "name": name, "description": description}

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

        # Search for role by name if ID is not provided
        if not role_id and state == "present":
            role_id = find_id_by_exact_name(get_roles, client, name)

        # If state=absent, delete the role
        if state == "absent":
            if not role_id:
                # Search for role by name
                role_id = find_id_by_exact_name(get_roles, client, name)

            if role_id:
                if not module.check_mode:
                    delete_role(client, role_id)
                result["changed"] = True
                result["id"] = role_id
                result["diff"] = {
                    "before": {"name": name, "id": role_id},
                    "after": {},
                }
            else:
                result["changed"] = False
                module.exit_json(**result)

        # If state=present, create or update
        else:
            if role_id:
                # Update an existing role
                existing_role = get_role(client, role_id)
                if not existing_role:
                    module.fail_json(msg=f"Role with ID {role_id} not found")

                # Check if modifications are needed. When is_default is not
                # provided, preserve the existing server-side value.
                effective_is_default = (
                    is_default if is_default is not None else existing_role.is_default
                )
                needs_update = False
                if existing_role.name != name:
                    needs_update = True
                if existing_role.description != description:
                    needs_update = True
                if existing_role.is_default != effective_is_default:
                    needs_update = True

                if needs_update:
                    result["diff"] = {
                        "before": {
                            "name": existing_role.name,
                            "description": existing_role.description,
                            "is_default": existing_role.is_default,
                        },
                        "after": {
                            "name": name,
                            "description": description,
                            "is_default": effective_is_default,
                        },
                    }
                    if not module.check_mode:
                        updated_role = update_role(
                            client,
                            role_id,
                            name,
                            description,
                            is_default=effective_is_default,
                        )
                        result["id"] = updated_role.id
                        result["description"] = updated_role.description
                        result["is_default"] = updated_role.is_default
                    result["changed"] = True
                else:
                    result["id"] = existing_role.id
                    result["description"] = existing_role.description
                    result["is_default"] = existing_role.is_default

            else:
                # Create a new role
                if not module.check_mode:
                    new_role = create_role(client, name, description, is_default)
                    role_id = new_role.id
                    result["id"] = role_id
                    result["description"] = new_role.description
                    result["is_default"] = new_role.is_default
                else:
                    result["id"] = "new-role-id"  # Placeholder for check_mode

                result["changed"] = True
                result["diff"] = {
                    "before": {},
                    "after": {
                        "name": name,
                        "description": description,
                        "is_default": bool(is_default),
                    },
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
    finally:
        if client is not None:
            client.logout()


if __name__ == "__main__":
    main()
