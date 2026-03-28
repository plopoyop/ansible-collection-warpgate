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
module: warpgate_target

short_description: Manages Warpgate targets (SSH, HTTP, MySQL, PostgreSQL, Kubernetes)

description:
    - This module allows to create, modify and delete targets in Warpgate.
    - Supports SSH, HTTP, MySQL, PostgreSQL and Kubernetes target types.

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
            - Target ID (for update/delete operations)
        type: str
        required: false
    name:
        description:
            - Target name
        type: str
        required: true
    description:
        description:
            - Target description
        type: str
        required: false
        default: ""
    group:
        description:
            - Target group name.
            - The module will resolve this name to a target group ID using the Warpgate API.
            - If not provided or empty, the target is not assigned to any group.
        type: str
        required: false
        default: ""
    ssh_options:
        description:
            - Options for an SSH target
        type: dict
        required: false
        suboptions:
            host:
                description: SSH host (hostname or IP)
                type: str
                required: true
            port:
                description: SSH port
                type: int
                required: true
            username:
                description: SSH username
                type: str
                required: true
            allow_insecure_algos:
                description: Allow insecure SSH algorithms
                type: bool
                default: false
            password_auth:
                description: Password authentication
                type: dict
                suboptions:
                    password:
                        description: Password
                        type: str
                        required: true
            public_key_auth:
                description: Public key authentication
                type: dict
    http_options:
        description:
            - Options for an HTTP target
        type: dict
        required: false
        suboptions:
            url:
                description: HTTP server URL
                type: str
                required: true
            tls:
                description: TLS configuration
                type: dict
                required: true
                suboptions:
                    mode:
                        description: TLS mode (Disabled, Preferred, Required)
                        type: str
                        choices: ["Disabled", "Preferred", "Required"]
                        required: true
                    verify:
                        description: Verify TLS certificates
                        type: bool
                        required: true
            headers:
                description: Custom HTTP headers
                type: dict
            external_host:
                description: External host for HTTP requests
                type: str
    mysql_options:
        description:
            - Options for a MySQL target
        type: dict
        required: false
        suboptions:
            host:
                description: MySQL host (hostname or IP)
                type: str
                required: true
            port:
                description: MySQL port
                type: int
                required: true
            username:
                description: MySQL username
                type: str
                required: true
            password:
                description: MySQL password
                type: str
            tls:
                description: TLS configuration
                type: dict
                required: true
                suboptions:
                    mode:
                        description: TLS mode (Disabled, Preferred, Required)
                        type: str
                        choices: ["Disabled", "Preferred", "Required"]
                        required: true
                    verify:
                        description: Verify TLS certificates
                        type: bool
                        required: true
    postgres_options:
        description:
            - Options for a PostgreSQL target
        type: dict
        required: false
        suboptions:
            host:
                description: PostgreSQL host (hostname or IP)
                type: str
                required: true
            port:
                description: PostgreSQL port
                type: int
                required: true
            username:
                description: PostgreSQL username
                type: str
                required: true
            password:
                description: PostgreSQL password
                type: str
            tls:
                description: TLS configuration
                type: dict
                required: true
                suboptions:
                    mode:
                        description: TLS mode (Disabled, Preferred, Required)
                        type: str
                        choices: ["Disabled", "Preferred", "Required"]
                        required: true
                    verify:
                        description: Verify TLS certificates
                        type: bool
                        required: true
    kubernetes_options:
        description:
            - Options for a Kubernetes target (experimental, requires Warpgate >= 0.21.0)
        type: dict
        required: false
        suboptions:
            cluster_url:
                description: URL of the upstream Kubernetes API server
                type: str
                required: true
            tls:
                description: TLS configuration for the upstream connection
                type: dict
                required: true
                suboptions:
                    mode:
                        description: TLS mode (Disabled, Preferred, Required)
                        type: str
                        choices: ["Disabled", "Preferred", "Required"]
                        required: true
                    verify:
                        description: Verify upstream TLS certificates
                        type: bool
                        required: true
            token_auth:
                description: >-
                    Token-based authentication to the upstream K8s cluster
                    (mutually exclusive with certificate_auth)
                type: dict
                suboptions:
                    token:
                        description: Bearer token for K8s API authentication
                        type: str
                        required: true
            certificate_auth:
                description: >-
                    Certificate-based authentication to the upstream K8s cluster
                    (mutually exclusive with token_auth)
                type: dict
                suboptions:
                    certificate:
                        description: Client certificate PEM for mTLS to upstream
                        type: str
                        required: true
                    private_key:
                        description: Private key PEM for mTLS to upstream
                        type: str
                        required: true
    roles:
        description:
            - List of role IDs or role names to assign to the target.
            - Each item is a string (role ID or role name).
            - Roles can be specified by ID (UUID) or by name.
            - The module will ensure the target has exactly these roles (adds missing ones, removes extra ones).
            - If an empty list is provided, all roles will be removed.
            - If not provided, existing roles are left unchanged.
        type: list
        elements: str
        required: false
    state:
        description:
            - Desired state of the target
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
- name: Create an SSH target
  plopoyop.warpgate.warpgate_target:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "app-server"
    description: "Application Server"
    ssh_options:
      host: "10.0.0.10"
      port: 22
      username: "admin"
      password_auth:
        password: "{{ ssh_password }}"
    state: present

- name: Create an HTTP target
  plopoyop.warpgate.warpgate_target:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "internal-web-app"
    description: "Internal Web Application"
    http_options:
      url: "https://internal.example.com"
      tls:
        mode: "Required"
        verify: true
      headers:
        X-Custom-Header: "value"
    state: present

- name: Create a MySQL target
  plopoyop.warpgate.warpgate_target:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "mysql-db"
    description: "Production MySQL Database"
    mysql_options:
      host: "db.example.com"
      port: 3306
      username: "admin"
      password: "{{ db_password }}"
      tls:
        mode: "Required"
        verify: true
    roles:
      - "developers"
      - "database-admins"
    state: present

- name: Create a Kubernetes target with token auth
  plopoyop.warpgate.warpgate_target:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "prod-cluster"
    description: "Production Kubernetes cluster"
    kubernetes_options:
      cluster_url: "https://10.0.0.1:6443"
      tls:
        mode: "Required"
        verify: true
      token_auth:
        token: "{{ k8s_service_account_token }}"
    roles:
      - "k8s-admins"
    state: present

- name: Create a Kubernetes target with certificate auth
  plopoyop.warpgate.warpgate_target:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    name: "staging-cluster"
    description: "Staging Kubernetes cluster"
    kubernetes_options:
      cluster_url: "https://10.0.1.1:6443"
      tls:
        mode: "Required"
        verify: false
      certificate_auth:
        certificate: "{{ k8s_client_cert }}"
        private_key: "{{ k8s_client_key }}"
    state: present
"""

RETURN = """
id:
    description: Target ID
    type: str
    returned: always
name:
    description: Target name
    type: str
    returned: always
description:
    description: Target description
    type: str
    returned: when available
group:
    description: Target group name
    type: str
    returned: when available
allow_roles:
    description: List of allowed roles
    type: list
    returned: when available
roles:
    description: List of role IDs assigned to the target
    type: list
    returned: when roles parameter is provided
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateClient,
    WarpgateClientError,
    WarpgateAPIError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    resolve_role_ids as _resolve_role_ids,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.target import (
    get_targets,
    get_target,
    create_target,
    update_target,
    delete_target,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.role import (
    get_target_roles,
    add_target_role,
    delete_target_role,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.target_group import (
    get_target_groups,
)


def build_target_options(module):
    """Builds target options from module parameters"""
    ssh_options = module.params.get("ssh_options")
    http_options = module.params.get("http_options")
    mysql_options = module.params.get("mysql_options")
    postgres_options = module.params.get("postgres_options")
    kubernetes_options = module.params.get("kubernetes_options")

    option_count = sum(
        [
            1 if ssh_options else 0,
            1 if http_options else 0,
            1 if mysql_options else 0,
            1 if postgres_options else 0,
            1 if kubernetes_options else 0,
        ]
    )

    if option_count == 0:
        module.fail_json(
            msg="One of ssh_options, http_options, mysql_options, "
            "postgres_options, or kubernetes_options must be specified"
        )
    if option_count > 1:
        module.fail_json(
            msg="Only one of ssh_options, http_options, mysql_options, "
            "postgres_options, or kubernetes_options can be specified"
        )

    if ssh_options:
        options = {
            "kind": "Ssh",
            "host": ssh_options["host"],
            "port": ssh_options["port"],
            "username": ssh_options["username"],
            "allow_insecure_algos": ssh_options.get("allow_insecure_algos", False),
        }

        if "password_auth" in ssh_options and ssh_options["password_auth"]:
            options["auth"] = {
                "kind": "Password",
                "password": ssh_options["password_auth"]["password"],
            }
        elif "public_key_auth" in ssh_options:
            # public_key_auth can be {} (empty dict) meaning "use public key auth"
            options["auth"] = {"kind": "PublicKey"}
        else:
            module.fail_json(
                msg="SSH target requires either password_auth or public_key_auth"
            )

        return options

    elif http_options:
        options = {
            "kind": "Http",
            "url": http_options["url"],
            "tls": {
                "mode": http_options["tls"]["mode"],
                "verify": http_options["tls"]["verify"],
            },
        }

        if "headers" in http_options:
            options["headers"] = http_options["headers"]
        if "external_host" in http_options:
            options["external_host"] = http_options["external_host"]

        return options

    elif mysql_options:
        options = {
            "kind": "MySql",
            "host": mysql_options["host"],
            "port": mysql_options["port"],
            "username": mysql_options["username"],
            "tls": {
                "mode": mysql_options["tls"]["mode"],
                "verify": mysql_options["tls"]["verify"],
            },
        }

        if "password" in mysql_options:
            options["password"] = mysql_options["password"]

        return options

    elif postgres_options:
        options = {
            "kind": "Postgres",
            "host": postgres_options["host"],
            "port": postgres_options["port"],
            "username": postgres_options["username"],
            "tls": {
                "mode": postgres_options["tls"]["mode"],
                "verify": postgres_options["tls"]["verify"],
            },
        }

        if "password" in postgres_options:
            options["password"] = postgres_options["password"]

        return options

    elif kubernetes_options:
        options = {
            "kind": "Kubernetes",
            "cluster_url": kubernetes_options["cluster_url"],
            "tls": {
                "mode": kubernetes_options["tls"]["mode"],
                "verify": kubernetes_options["tls"]["verify"],
            },
        }

        if "token_auth" in kubernetes_options and kubernetes_options["token_auth"]:
            options["auth"] = {
                "kind": "Token",
                "token": kubernetes_options["token_auth"]["token"],
            }
        elif (
            "certificate_auth" in kubernetes_options
            and kubernetes_options["certificate_auth"]
        ):
            options["auth"] = {
                "kind": "Certificate",
                "certificate": kubernetes_options["certificate_auth"]["certificate"],
                "private_key": kubernetes_options["certificate_auth"]["private_key"],
            }
        else:
            module.fail_json(
                msg="Kubernetes target requires either token_auth or certificate_auth"
            )

        return options

    return None


def options_equal(opts1, opts2):
    """Compares two option dictionaries ignoring certain fields"""

    # Normalize dictionaries for comparison
    def normalize(d):
        if not d:
            return {}
        normalized = d.copy()
        # Ignore fields that may vary
        normalized.pop("id", None)
        normalized.pop("allow_roles", None)
        return normalized

    return normalize(opts1) == normalize(opts2)


def resolve_group_id(client, group_name: str, module) -> str:
    """
    Resolves a target group name to its ID.
    Returns empty string when group_name is empty.
    """
    if not group_name or not str(group_name).strip():
        return ""

    groups = get_target_groups(client, search=group_name)
    for g in groups:
        if g.name == group_name:
            return g.id

    module.fail_json(msg=f"Target group '{group_name}' not found")


def manage_target_roles(
    client, target_id, desired_role_ids, module, current_role_ids_from_target=None
):
    """
    Manages target roles to match the desired list exactly.
    Adds missing roles and removes roles not in the desired list.
    If an empty list is provided, all roles will be removed.
    Uses current_role_ids_from_target (target.allow_roles) when provided, so the
    source of truth is the target resource itself; otherwise falls back to GET
    /targets/{id}/roles (which may return a different format on some APIs).
    Returns tuple (changed, list of assigned role IDs)
    """
    # desired_role_ids should never be None when this function is called
    # (caller should check before calling)
    if desired_role_ids is None:
        desired_role_ids = []

    changed = False

    # Normalize to a set of role ID strings (API may return list of IDs or list of objects)
    def _to_role_id_set(role_list):
        out = set()
        for r in role_list or []:
            if isinstance(r, str) and r:
                out.add(r)
            elif hasattr(r, "id"):
                out.add(r.id)
            elif isinstance(r, dict):
                rid = r.get("id") or r.get("role_id")
                if rid:
                    out.add(rid)
        return out

    # Current roles: prefer target.allow_roles; if empty, GET /targets/{id}/roles
    # (some Warpgate versions do not populate allow_roles on GET /targets/{id})
    current_role_ids = (
        _to_role_id_set(current_role_ids_from_target)
        if current_role_ids_from_target
        else set()
    )
    if not current_role_ids:
        try:
            current_roles = get_target_roles(client, target_id)
            current_role_ids = _to_role_id_set(current_roles)
        except WarpgateAPIError as e:
            if e.status_code != 404:
                module.fail_json(
                    msg=f"Failed to get target roles: {e.message}",
                    status_code=e.status_code,
                )
    desired_role_ids_set = set(desired_role_ids)

    # Idempotence: do nothing if current already matches desired
    if current_role_ids == desired_role_ids_set:
        return False, list(desired_role_ids_set)

    # Add missing roles (409 = already assigned, skip for idempotence)
    roles_to_add = desired_role_ids_set - current_role_ids
    if roles_to_add:
        actually_added = False
        if not module.check_mode:
            for role_id in roles_to_add:
                try:
                    add_target_role(client, target_id, role_id)
                    actually_added = True
                except WarpgateAPIError as e:
                    if e.status_code == 409:
                        continue  # Already assigned
                    module.fail_json(
                        msg=f"Failed to add role {role_id} to target: {e.message}",
                        status_code=e.status_code,
                    )
        if actually_added or module.check_mode:
            changed = True

    # Remove extra roles
    roles_to_remove = current_role_ids - desired_role_ids_set
    if roles_to_remove:
        if not module.check_mode:
            for role_id in roles_to_remove:
                try:
                    delete_target_role(client, target_id, role_id)
                except WarpgateAPIError as e:
                    module.fail_json(
                        msg=f"Failed to remove role {role_id} from target: {e.message}",
                        status_code=e.status_code,
                    )
        changed = True

    # Return the final list of role IDs
    final_role_ids = list(desired_role_ids_set)
    return changed, final_role_ids


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        id=dict(type="str", required=False),
        name=dict(type="str", required=True),
        description=dict(type="str", required=False, default=""),
        group=dict(type="str", required=False, default=""),
        ssh_options=dict(type="dict", required=False),
        http_options=dict(type="dict", required=False),
        mysql_options=dict(type="dict", required=False),
        postgres_options=dict(type="dict", required=False),
        kubernetes_options=dict(type="dict", required=False),
        roles=dict(type="list", elements="str", required=False),
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
    target_id = module.params["id"]
    name = module.params["name"]
    description = module.params["description"]
    group = module.params["group"]
    roles = module.params["roles"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": None,
        "name": name,
        "description": description,
        "group": group,
        "roles": [],
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

        # Search for target by name if ID is not provided
        if not target_id and state == "present":
            targets = get_targets(client, search=name)
            for target in targets:
                if target.name == name:
                    target_id = target.id
                    break

        # If state=absent, delete the target
        if state == "absent":
            if not target_id:
                # Search for target by name
                targets = get_targets(client, search=name)
                for target in targets:
                    if target.name == name:
                        target_id = target.id
                        break

            if target_id:
                if not module.check_mode:
                    delete_target(client, target_id)
                result["changed"] = True
                result["id"] = target_id
                result["diff"] = {
                    "before": {"name": name, "id": target_id},
                    "after": {},
                }
            else:
                result["changed"] = False
                module.exit_json(**result)

        # If state=present, create or update
        else:
            target_options = build_target_options(module)
            group_id = resolve_group_id(client, group, module)

            if target_id:
                # Update an existing target
                existing_target = get_target(client, target_id)
                if not existing_target:
                    module.fail_json(msg=f"Target with ID {target_id} not found")

                diff_before = {
                    "name": existing_target.name,
                    "description": existing_target.description or "",
                    "group_id": existing_target.group_id or "",
                    "options": existing_target.options or {},
                }
                diff_after = {
                    "name": name,
                    "description": description,
                    "group_id": group_id or "",
                    "options": target_options or {},
                }

                # Check if modifications are needed
                needs_update = False
                if existing_target.name != name:
                    needs_update = True
                if existing_target.description != description:
                    needs_update = True
                if (existing_target.group_id or "") != (group_id or ""):
                    needs_update = True

                # Compare options (simplified - basic comparison)
                existing_options = existing_target.options
                if not options_equal(existing_options, target_options):
                    needs_update = True

                if needs_update:
                    if not module.check_mode:
                        updated_target = update_target(
                            client,
                            target_id,
                            name,
                            description,
                            group_id,
                            target_options,
                        )
                        result["id"] = updated_target.id
                        result["description"] = updated_target.description
                        result["group"] = group
                        result["allow_roles"] = updated_target.allow_roles
                    result["changed"] = True
                else:
                    result["id"] = existing_target.id
                    result["description"] = existing_target.description
                    result["group"] = group
                    result["allow_roles"] = existing_target.allow_roles

                # Manage roles (use target.allow_roles as source of truth for current state)
                if roles is not None:
                    # Resolve role names/IDs to actual role IDs
                    resolved_role_ids = _resolve_role_ids(client, roles)
                    current_from_target = (
                        (existing_target.allow_roles or []) if existing_target else None
                    )
                    diff_before["roles"] = list(current_from_target or [])
                    diff_after["roles"] = resolved_role_ids

                    roles_changed, final_role_ids = manage_target_roles(
                        client,
                        target_id,
                        resolved_role_ids,
                        module,
                        current_role_ids_from_target=current_from_target,
                    )
                    if roles_changed:
                        result["changed"] = True
                    result["roles"] = final_role_ids
                else:
                    # If not provided, leave existing ones unchanged; return from target.allow_roles
                    result["roles"] = list(existing_target.allow_roles or [])

                if result["changed"]:
                    result["diff"] = {"before": diff_before, "after": diff_after}

            else:
                # Create a new target
                if not module.check_mode:
                    new_target = create_target(
                        client, name, description, group_id, target_options
                    )
                    target_id = new_target.id
                    result["id"] = target_id
                    result["description"] = new_target.description
                    result["group"] = group
                    result["allow_roles"] = new_target.allow_roles

                    # Manage roles (new target has allow_roles from create response)
                    if roles is not None:
                        # Resolve role names/IDs to actual role IDs
                        resolved_role_ids = _resolve_role_ids(client, roles)
                        current_from_target = (
                            getattr(new_target, "allow_roles", None) or []
                        )
                        roles_changed, final_role_ids = manage_target_roles(
                            client,
                            target_id,
                            resolved_role_ids,
                            module,
                            current_role_ids_from_target=current_from_target,
                        )
                        if roles_changed:
                            result["changed"] = True
                        result["roles"] = final_role_ids
                    else:
                        result["roles"] = list(
                            getattr(new_target, "allow_roles", None) or []
                        )
                else:
                    result["id"] = "new-target-id"  # Placeholder for check_mode
                    if roles is not None:
                        # In check mode, resolve roles but don't actually assign them
                        try:
                            result["roles"] = _resolve_role_ids(client, roles)
                        except (ValueError, WarpgateAPIError):
                            result["roles"] = roles or []
                    else:
                        result["roles"] = []

                result["changed"] = True
                result["diff"] = {
                    "before": {},
                    "after": {
                        "name": name,
                        "description": description,
                        "group": group,
                        "options": target_options or {},
                        "roles": roles or [],
                    },
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
