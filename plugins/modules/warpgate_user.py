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
module: warpgate_user

short_description: Manages Warpgate users

description:
    - This module allows to create, modify and delete users in Warpgate.
    - It also manages credential policies for users.

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
            - User ID (for update/delete operations)
        type: str
        required: false
    username:
        description:
            - Username
        type: str
        required: true
    description:
        description:
            - User description
        type: str
        required: false
        default: ""
    credential_policy:
        description:
            - Credential policy for the user
        type: dict
        required: false
        suboptions:
            http:
                description:
                    - Accepted credential types for HTTP
                type: list
                elements: str
                choices: ["Password", "Totp", "Sso", "WebUserApproval"]
            ssh:
                description:
                    - Accepted credential types for SSH
                type: list
                elements: str
                choices: ["Password", "PublicKey", "Totp", "Sso", "WebUserApproval"]
            mysql:
                description:
                    - Accepted credential types for MySQL
                type: list
                elements: str
                choices: ["Password", "Totp", "Sso", "WebUserApproval"]
            postgres:
                description:
                    - Accepted credential types for PostgreSQL
                type: list
                elements: str
                choices: ["Password", "Totp", "Sso", "WebUserApproval"]
            kubernetes:
                description:
                    - Accepted credential types for Kubernetes
                type: list
                elements: str
                choices: ["Password", "PublicKey", "Certificate", "Totp", "Sso", "WebUserApproval"]
    password_credentials:
        description:
            - List of password credentials to manage for the user.
            - Each item should be a password string.
            - "Since the Warpgate API does not return password values,
              idempotence behavior depends on C(update_password)."
        type: list
        elements: str
        required: false
        no_log: true
    update_password:
        description:
            - C(on_create) will only set passwords when the user has no existing password credentials.
            - C(always) will replace all password credentials on every run (not idempotent).
        type: str
        choices: ['on_create', 'always']
        default: on_create
    public_key_credentials:
        description:
            - List of public key credentials to manage for the user
            - Each item should be a dict with 'label' and 'public_key' keys
            - The module will ensure the user has exactly these keys
            - Adds missing ones, updates changed ones, removes keys not in this list
            - If an empty list is provided, all public key credentials will be removed
            - If not provided, existing credentials are left unchanged
        type: list
        elements: dict
        required: false
        suboptions:
            label:
                description:
                    - Label for the public key
                type: str
                required: true
            public_key:
                description:
                    - OpenSSH public key
                type: str
                required: true
    roles:
        description:
            - List of role IDs or role names to assign to the user
            - Roles can be specified by ID (UUID) or by name
            - The module will ensure the user has exactly these roles (adds missing ones, removes extra ones)
            - If an empty list is provided, all roles will be removed
            - If not provided, existing roles are left unchanged
        type: list
        elements: str
        required: false
    state:
        description:
            - Desired state of the user
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
- name: Create a Warpgate user
  plopoyop.warpgate.warpgate_user:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    username: "eugene"
    description: "Eugene - WarpGate Developer"
    credential_policy:
      http: ["Password", "Totp"]
      ssh: ["PublicKey"]
      mysql: ["Password"]
      postgres: ["Password"]
    password_credentials:
      - "{{ user_password }}"
    public_key_credentials:
      - label: "Work Laptop"
        public_key: "ssh-rsa AAAAB3NzaC1yc2E... email@example.com"
      - label: "Home Desktop"
        public_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5... email@example.com"
    roles:
      - "developers"
      - "admin"
    state: present

- name: Update a user
  plopoyop.warpgate.warpgate_user:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    id: "user-uuid"
    username: "eugene"
    description: "Updated description"
    state: present

- name: Delete a user
  plopoyop.warpgate.warpgate_user:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    id: "user-uuid"
    username: "eugene"
    state: absent
"""

RETURN = """
id:
    description: User ID
    type: str
    returned: always
username:
    description: Username
    type: str
    returned: always
description:
    description: User description
    type: str
    returned: when available
credential_policy:
    description: Credential policy
    type: dict
    returned: when available
password_credentials:
    description: List of password credentials managed
    type: list
    returned: when password_credentials parameter is provided
public_key_credentials:
    description: List of public key credentials managed
    type: list
    returned: when public_key_credentials parameter is provided
roles:
    description: List of role IDs assigned to the user
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
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.user import (
    get_users,
    get_user,
    create_user,
    update_user,
    delete_user,
    UserRequireCredentialsPolicy,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.credential import (
    add_password_credential,
    get_password_credentials,
    delete_password_credential,
    get_public_key_credentials,
    add_public_key_credential,
    update_public_key_credential,
    delete_public_key_credential,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.role import (
    get_user_roles,
    add_user_role,
    delete_user_role,
)


def normalize_credential_policy(policy):
    """Normalizes the credential policy. Returns None when policy is empty or has only empty fields."""
    if not policy:
        return None

    cp = UserRequireCredentialsPolicy(
        http=policy.get("http") or None,
        ssh=policy.get("ssh") or None,
        mysql=policy.get("mysql") or None,
        postgres=policy.get("postgres") or None,
        kubernetes=policy.get("kubernetes") or None,
    )
    if not cp.to_dict():
        return None
    return cp


def manage_password_credentials(
    client, user_id, passwords, module, update_password="on_create"
):
    """
    Manages password credentials for a user.

    Since the Warpgate API does not return password values, true idempotence
    is impossible.  The ``update_password`` parameter controls behaviour:

    * ``on_create`` (default): only set passwords when the user has **no**
      existing password credentials.  If at least one credential already
      exists, this is a no-op (``changed=False``).
    * ``always``: delete all existing password credentials and recreate them
      with the provided values on every run (``changed=True``).
    """
    if not passwords:
        return False

    # Try to get existing password credentials
    existing_password_creds = []
    try:
        existing_password_creds = get_password_credentials(client, user_id)
        module.debug(
            f"Found {len(existing_password_creds)} existing password credentials"
        )
    except WarpgateAPIError as e:
        module.debug(f"Could not get existing password credentials: {e.message}")
        existing_password_creds = None

    # on_create: skip if user already has credentials
    if update_password == "on_create":
        if existing_password_creds:
            module.debug("update_password=on_create and credentials exist, skipping")
            return False

    # always: replace all credentials unconditionally
    if not module.check_mode:
        # Delete all existing password credentials first
        if existing_password_creds:
            for cred in existing_password_creds:
                if cred.id:
                    try:
                        delete_password_credential(client, user_id, cred.id)
                        module.debug(f"Deleted existing password credential {cred.id}")
                    except WarpgateAPIError as e:
                        module.debug(
                            f"Could not delete password credential {cred.id}: {e.message}"
                        )

        # Add the desired passwords
        for password in passwords:
            try:
                add_password_credential(client, user_id, password)
                module.debug("Added password credential")
            except WarpgateAPIError as e:
                module.fail_json(
                    msg=f"Failed to add password credential: {e.message}",
                    status_code=e.status_code,
                )

    return True


def manage_public_key_credentials(client, user_id, desired_keys, module):
    """
    Manages public key credentials for a user.
    Ensures the user has exactly the specified keys (adds missing, updates changed, removes extras).
    If an empty list is provided, all keys will be removed.
    Returns tuple (changed, list of managed credentials)
    """
    # desired_keys should never be None when this function is called
    # (caller should check before calling)
    if desired_keys is None:
        desired_keys = []

    changed = False
    managed_creds = []

    # Get existing public key credentials (both in normal and check mode for idempotence)
    existing_creds = {}
    try:
        existing_list = get_public_key_credentials(client, user_id)
        for cred in existing_list:
            existing_creds[cred.label] = cred
        module.debug(
            f"Found {len(existing_creds)} existing public key credentials: {list(existing_creds.keys())}"
        )
    except WarpgateAPIError as e:
        # If we can't read credentials, we'll just try to add/update
        module.debug(f"Could not get existing public key credentials: {e.message}")
        existing_creds = {}

    # Build set of desired labels
    desired_labels = set()
    if desired_keys:
        desired_labels = {key_spec["label"] for key_spec in desired_keys}

    # Remove keys that are not in the desired list
    keys_to_remove = set(existing_creds.keys()) - desired_labels
    if keys_to_remove:
        module.debug(f"Keys to remove: {keys_to_remove}")
        if not module.check_mode:
            for label in keys_to_remove:
                try:
                    delete_public_key_credential(
                        client, user_id, existing_creds[label].id
                    )
                except WarpgateAPIError as e:
                    module.fail_json(
                        msg=f"Failed to delete public key credential '{label}': {e.message}",
                        status_code=e.status_code,
                    )
        # Only mark as changed if we actually remove keys
        changed = True
    else:
        module.debug("No keys to remove")

    # Process desired keys (add or update)
    if desired_keys:
        for key_spec in desired_keys:
            label = key_spec["label"]
            public_key = key_spec["public_key"]

            if label in existing_creds:
                # Key exists, check if update is needed
                existing_cred = existing_creds[label]

                # Normalize both keys for comparison (strip whitespace and normalize line endings)
                def _normalize_key(k):
                    return (k or "").strip().replace("\r\n", "\n").replace("\r", "\n")

                existing_key_normalized = _normalize_key(
                    existing_cred.openssh_public_key
                )
                desired_key_normalized = _normalize_key(public_key)

                # Extract the key part (without comment) for comparison
                # SSH public keys format: "type keydata [comment]"
                # The API may not return the comment, so we compare only the key part
                def extract_key_part(key_str):
                    """Extract the key part without comment (first two space-separated parts)"""
                    parts = key_str.split()
                    if len(parts) >= 2:
                        return " ".join(parts[:2])  # type and keydata
                    return key_str

                existing_key_part = extract_key_part(existing_key_normalized)
                desired_key_part = extract_key_part(desired_key_normalized)

                module.debug(
                    f"Comparing key '{label}': existing len={len(existing_key_part)}, "
                    f"desired len={len(desired_key_part)}"
                )
                module.debug(
                    f"Existing key part: {existing_key_part[:80] if existing_key_part else 'EMPTY'}"
                )
                module.debug(
                    f"Desired key part: {desired_key_part[:80] if desired_key_part else 'EMPTY'}"
                )
                module.debug(f"Keys are equal: {existing_key_part == desired_key_part}")

                if existing_key_part != desired_key_part:
                    # Update needed
                    module.debug(f"Key '{label}' needs update: keys differ")
                    if not module.check_mode:
                        try:
                            updated_cred = update_public_key_credential(
                                client, user_id, existing_cred.id, label, public_key
                            )
                            managed_creds.append(
                                {
                                    "id": updated_cred.id,
                                    "label": updated_cred.label,
                                    "public_key": updated_cred.openssh_public_key,
                                }
                            )
                        except WarpgateAPIError as e:
                            module.fail_json(
                                msg=f"Failed to update public key credential '{label}': {e.message}",
                                status_code=e.status_code,
                            )
                    else:
                        managed_creds.append(
                            {
                                "id": existing_cred.id,
                                "label": label,
                                "public_key": public_key,
                            }
                        )
                    changed = True
                else:
                    # No change needed - key already exists with same value
                    module.debug(
                        f"Key '{label}' already exists with same value, no change needed"
                    )
                    managed_creds.append(
                        {
                            "id": existing_cred.id,
                            "label": existing_cred.label,
                            "public_key": existing_cred.openssh_public_key,
                        }
                    )
                    # Don't mark as changed
            else:
                # Key doesn't exist, add it
                if not module.check_mode:
                    try:
                        new_cred = add_public_key_credential(
                            client, user_id, label, public_key
                        )
                        managed_creds.append(
                            {
                                "id": new_cred.id,
                                "label": new_cred.label,
                                "public_key": new_cred.openssh_public_key,
                            }
                        )
                    except WarpgateAPIError as e:
                        module.fail_json(
                            msg=f"Failed to add public key credential '{label}': {e.message}",
                            status_code=e.status_code,
                        )
                else:
                    managed_creds.append(
                        {
                            "id": "new-credential-id",
                            "label": label,
                            "public_key": public_key,
                        }
                    )
                changed = True

    return changed, managed_creds


def manage_user_roles(client, user_id, desired_role_ids, module):
    """
    Manages user roles to match the desired list exactly.
    Adds missing roles and removes roles not in the desired list.
    If an empty list is provided, all roles will be removed.
    Returns tuple (changed, list of assigned role IDs)
    """
    # desired_role_ids should never be None when this function is called
    # (caller should check before calling)
    if desired_role_ids is None:
        desired_role_ids = []

    changed = False

    # Get current user roles
    current_roles = []
    if not module.check_mode:
        try:
            current_roles = get_user_roles(client, user_id)
        except WarpgateAPIError as e:
            module.fail_json(
                msg=f"Failed to get user roles: {e.message}", status_code=e.status_code
            )
    else:
        # In check mode, try to get current roles to simulate properly
        try:
            current_roles = get_user_roles(client, user_id)
        except WarpgateAPIError:
            # If we can't get roles in check mode, assume empty
            current_roles = []

    current_role_ids = set(role.id for role in current_roles)
    desired_role_ids_set = set(desired_role_ids)

    # Add missing roles
    roles_to_add = desired_role_ids_set - current_role_ids
    if roles_to_add:
        if not module.check_mode:
            for role_id in roles_to_add:
                try:
                    add_user_role(client, user_id, role_id)
                except WarpgateAPIError as e:
                    module.fail_json(
                        msg=f"Failed to add role {role_id} to user: {e.message}",
                        status_code=e.status_code,
                    )
        changed = True

    # Remove extra roles
    roles_to_remove = current_role_ids - desired_role_ids_set
    if roles_to_remove:
        if not module.check_mode:
            for role_id in roles_to_remove:
                try:
                    delete_user_role(client, user_id, role_id)
                except WarpgateAPIError as e:
                    module.fail_json(
                        msg=f"Failed to remove role {role_id} from user: {e.message}",
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
        username=dict(type="str", required=True),
        description=dict(type="str", required=False, default=""),
        credential_policy=dict(type="dict", required=False),
        password_credentials=dict(
            type="list", elements="str", required=False, no_log=True
        ),
        update_password=dict(
            type="str",
            default="on_create",
            choices=["on_create", "always"],
            no_log=False,
        ),
        public_key_credentials=dict(
            type="list",
            elements="dict",
            required=False,
            options=dict(
                label=dict(type="str", required=True),
                public_key=dict(type="str", required=True),
            ),
        ),
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
    user_id = module.params["id"]
    username = module.params["username"]
    description = module.params["description"]
    credential_policy = module.params["credential_policy"]
    password_credentials = module.params["password_credentials"]
    update_password = module.params["update_password"]
    public_key_credentials = module.params["public_key_credentials"]
    roles = module.params["roles"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": None,
        "username": username,
        "description": description,
        "credential_policy": credential_policy,
        "password_credentials": password_credentials if password_credentials else [],
        "public_key_credentials": [],
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

        # Search for user by username if ID is not provided
        if not user_id and state == "present":
            users = get_users(client, search=username)
            for user in users:
                if user.username == username:
                    user_id = user.id
                    break

        # If state=absent, delete the user
        if state == "absent":
            if not user_id:
                # Search for user by username
                users = get_users(client, search=username)
                for user in users:
                    if user.username == username:
                        user_id = user.id
                        break

            if user_id:
                if not module.check_mode:
                    delete_user(client, user_id)
                result["changed"] = True
                result["id"] = user_id
                result["diff"] = {
                    "before": {"username": username, "id": user_id},
                    "after": {},
                }
            else:
                result["changed"] = False
                module.exit_json(**result)

        # If state=present, create or update
        else:
            normalized_policy = normalize_credential_policy(credential_policy)

            if user_id:
                # Update an existing user
                existing_user = get_user(client, user_id)
                if not existing_user:
                    module.fail_json(msg=f"User with ID {user_id} not found")

                diff_before = {
                    "username": existing_user.username,
                    "description": existing_user.description or "",
                }
                diff_after = {
                    "username": username,
                    "description": description,
                }

                # Check if modifications are needed
                needs_update = False
                if existing_user.username != username:
                    needs_update = True
                if existing_user.description != description:
                    needs_update = True

                # Compare credential policies (only when a policy was explicitly provided)
                existing_policy = existing_user.credential_policy
                if normalized_policy:
                    policy_dict = normalized_policy.to_dict()
                    existing_policy_dict = (
                        existing_policy.to_dict() if existing_policy else {}
                    )
                    diff_before["credential_policy"] = existing_policy_dict
                    diff_after["credential_policy"] = policy_dict
                    if policy_dict != existing_policy_dict:
                        needs_update = True

                if needs_update:
                    if not module.check_mode:
                        updated_user = update_user(
                            client, user_id, username, description, normalized_policy
                        )
                        result["id"] = updated_user.id
                        result["description"] = updated_user.description
                        if updated_user.credential_policy:
                            policy_dict = updated_user.credential_policy.to_dict()
                            result["credential_policy"] = (
                                policy_dict if policy_dict else None
                            )
                        else:
                            result["credential_policy"] = None
                    result["changed"] = True
                else:
                    result["id"] = existing_user.id
                    result["description"] = existing_user.description
                    if existing_user.credential_policy:
                        policy_dict = existing_user.credential_policy.to_dict()
                        result["credential_policy"] = (
                            policy_dict if policy_dict else None
                        )
                    else:
                        result["credential_policy"] = None

                # Manage credentials
                if password_credentials is not None:
                    creds_changed = manage_password_credentials(
                        client, user_id, password_credentials, module, update_password
                    )
                    if creds_changed:
                        result["changed"] = True

                # Manage public_key_credentials (None is treated as empty list, meaning remove all)
                if public_key_credentials is not None:
                    creds_changed, managed_keys = manage_public_key_credentials(
                        client, user_id, public_key_credentials, module
                    )
                    if creds_changed:
                        result["changed"] = True
                    result["public_key_credentials"] = managed_keys
                else:
                    # If not provided, don't manage them (leave existing ones unchanged)
                    # Get current keys for return value
                    try:
                        existing_list = get_public_key_credentials(client, user_id)
                        result["public_key_credentials"] = [
                            {
                                "id": cred.id,
                                "label": cred.label,
                                "public_key": cred.openssh_public_key,
                            }
                            for cred in existing_list
                        ]
                    except WarpgateAPIError:
                        result["public_key_credentials"] = []

                # Manage roles (None is treated as empty list, meaning remove all)
                if roles is not None:
                    # Resolve role names/IDs to actual role IDs
                    resolved_role_ids = _resolve_role_ids(client, roles)
                    # Capture current roles for diff
                    try:
                        current_roles_before = get_user_roles(client, user_id)
                        diff_before["roles"] = [r.id for r in current_roles_before]
                    except WarpgateAPIError:
                        diff_before["roles"] = []
                    diff_after["roles"] = resolved_role_ids

                    roles_changed, final_role_ids = manage_user_roles(
                        client, user_id, resolved_role_ids, module
                    )
                    if roles_changed:
                        result["changed"] = True
                    result["roles"] = final_role_ids
                else:
                    # If not provided, don't manage them (leave existing ones unchanged)
                    # Get current roles for return value
                    try:
                        current_roles = get_user_roles(client, user_id)
                        result["roles"] = [role.id for role in current_roles]
                    except WarpgateAPIError:
                        result["roles"] = []

                if result["changed"]:
                    result["diff"] = {"before": diff_before, "after": diff_after}

            else:
                # Create a new user
                if not module.check_mode:
                    new_user = create_user(client, username, description)
                    user_id = new_user.id

                    # If a credential policy is specified, update it
                    if normalized_policy:
                        updated_user = update_user(
                            client, user_id, username, description, normalized_policy
                        )
                        if updated_user.credential_policy:
                            policy_dict = updated_user.credential_policy.to_dict()
                            result["credential_policy"] = (
                                policy_dict if policy_dict else None
                            )
                        else:
                            result["credential_policy"] = None
                    else:
                        result["credential_policy"] = None

                    result["id"] = user_id
                    result["description"] = new_user.description

                    # Manage credentials
                    if password_credentials is not None:
                        creds_changed = manage_password_credentials(
                            client,
                            user_id,
                            password_credentials,
                            module,
                            update_password,
                        )
                        if creds_changed:
                            result["changed"] = True

                    # Manage public_key_credentials (None is treated as empty list, meaning remove all)
                    if public_key_credentials is not None:
                        creds_changed, managed_keys = manage_public_key_credentials(
                            client, user_id, public_key_credentials, module
                        )
                        if creds_changed:
                            result["changed"] = True
                        result["public_key_credentials"] = managed_keys
                    else:
                        result["public_key_credentials"] = []

                    # Manage roles (None is treated as empty list, meaning remove all)
                    if roles is not None:
                        # Resolve role names/IDs to actual role IDs
                        resolved_role_ids = _resolve_role_ids(client, roles)
                        roles_changed, final_role_ids = manage_user_roles(
                            client, user_id, resolved_role_ids, module
                        )
                        if roles_changed:
                            result["changed"] = True
                        result["roles"] = final_role_ids
                    else:
                        result["roles"] = []
                else:
                    result["id"] = "new-user-id"  # Placeholder for check_mode
                    # In check mode, return the desired keys (or empty list if None)
                    if public_key_credentials:
                        result["public_key_credentials"] = [
                            {
                                "id": "new-credential-id",
                                "label": k["label"],
                                "public_key": k["public_key"],
                            }
                            for k in public_key_credentials
                        ]
                    else:
                        result["public_key_credentials"] = []
                    # In check mode, resolve roles but don't actually assign them
                    try:
                        result["roles"] = _resolve_role_ids(client, roles or [])
                    except (ValueError, WarpgateAPIError):
                        result["roles"] = roles or []

                result["changed"] = True
                result["diff"] = {
                    "before": {},
                    "after": {
                        "username": username,
                        "description": description,
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
