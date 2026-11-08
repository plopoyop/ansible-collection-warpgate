#!/usr/bin/python


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
            - With O(state=absent), the deletion fails if the object found by ID is not named O(username).
        type: str
        required: false
    username:
        description:
            - Username
            - An existing user is matched exactly, else ignoring ASCII case like Warpgate on
              SQLite (on PostgreSQL, Warpgate also ignores the case of non-ASCII letters).
        type: str
        required: true
    description:
        description:
            - User description
        type: str
        required: false
        default: ""
    rate_limit_bytes_per_second:
        description:
            - Optional per-user upstream bandwidth limit in bytes/second (v0.23+).
            - When not provided, no bandwidth cap is applied.
        type: int
        required: false
    allowed_ip_ranges:
        description:
            - Optional list of CIDR ranges authorized to authenticate as this user (v0.23+).
            - Pass C([]) to explicitly clear the allow-list.
            - When not provided, the current list on the server is left unchanged.
        type: list
        elements: str
        required: false
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
    update_password:
        description:
            - C(on_create) will only set passwords when the user has no existing password credentials.
            - C(always) will replace all password credentials on every run (not idempotent).
            - With C(always), an empty O(password_credentials) list removes every password credential.
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
            - Labels must be unique. Keys are added or updated before others are removed,
              so a rejected new key leaves the previous ones in place (and the task fails).
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
    sso_credentials:
        description:
            - List of SSO credentials to manage for the user.
            - Each item is a dict with C(email) (required) and optional C(provider).
            - The module enforces the exact list (adds missing, updates changed, removes extras).
            - An empty list removes all SSO credentials. If not provided, existing ones are left unchanged.
            - Identity is matched on C(email) + C(provider). Two credentials with the same email but
              different providers are treated as distinct.
        type: list
        elements: dict
        required: false
        suboptions:
            email:
                description:
                    - Email used by the SSO identity (must match the C(email) claim returned by the IdP).
                type: str
                required: true
            provider:
                description:
                    - Name of the configured SSO provider (as declared in Warpgate's C(sso_providers)).
                    - Leave empty to accept any provider.
                type: str
                required: false
                default: ""
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
    admin_roles:
        description:
            - List of admin role IDs or names to grant to the user (v0.23+).
            - The module ensures the user holds exactly these admin roles
              (adds missing, removes extras). Empty list = revoke all.
            - When not provided, existing admin-role assignments are left unchanged.
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
    sso_credentials:
      - provider: "microsoft"
        email: "eugene@example.com"
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
rate_limit_bytes_per_second:
    description: Per-user bandwidth limit in bytes/second (v0.23+)
    type: int
    returned: when available
allowed_ip_ranges:
    description: Authorized CIDR ranges for this user (v0.23+)
    type: list
    returned: when available
password_credentials:
    description: List of password credentials managed
    type: list
    returned: when password_credentials parameter is provided
public_key_credentials:
    description: List of public key credentials managed
    type: list
    returned: when public_key_credentials parameter is provided
sso_credentials:
    description: List of SSO credentials managed
    type: list
    returned: when sso_credentials parameter is provided
roles:
    description: List of role IDs assigned to the user
    type: list
    returned: when roles parameter is provided
admin_roles:
    description: List of admin-role IDs granted to the user (v0.23+)
    type: list
    returned: when admin_roles parameter is provided
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    find_id_by_exact_name,
    fold_username,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    resolve_role_ids as _resolve_role_ids,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.admin_role import (
    add_user_admin_role,
    delete_user_admin_role,
    get_user_admin_roles,
    resolve_admin_role_ids,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.credential import (
    add_password_credential,
    add_public_key_credential,
    add_sso_credential,
    delete_password_credential,
    delete_public_key_credential,
    delete_sso_credential,
    format_password_policy_error,
    get_password_credentials,
    get_public_key_credentials,
    get_sso_credentials,
    update_public_key_credential,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.role import (
    add_user_role,
    delete_user_role,
    get_user_roles,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.user import (
    UserRequireCredentialsPolicy,
    create_user,
    delete_user,
    get_user,
    get_users,
    update_user,
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


def _mark_changed(result):
    """Record a change in the module result as soon as it happens."""
    if result is not None:
        result["changed"] = True


def manage_password_credentials(
    client,
    user_id,
    passwords,
    module,
    update_password="on_create",
    changed_before=False,
    result=None,
):
    """
    Manages password credentials for a user.

    Since the Warpgate API does not return password values, true idempotence
    is impossible.  The ``update_password`` parameter controls behaviour:

    * ``on_create`` (default): only set passwords when the user has **no**
      existing password credentials.  If at least one credential already
      exists, this is a no-op (``changed=False``).
    * ``always``: add the provided values, then delete the existing password
      credentials, on every run (``changed=True``). An empty list removes them.
    """
    if passwords is None or (not passwords and update_password != "always"):
        return False

    try:
        existing_password_creds = get_password_credentials(client, user_id)
    except WarpgateAPIError as e:
        module.fail_json(
            changed=changed_before,
            msg=f"Failed to get existing password credentials: {e.message}",
            status_code=e.status_code,
        )

    if not passwords and not existing_password_creds:
        return False

    if update_password == "on_create" and existing_password_creds:
        module.debug("update_password=on_create and credentials exist, skipping")
        return False

    changed = False
    if not module.check_mode:
        # Add before deleting so that a rejected password never leaves the
        # user without any.
        for password in passwords:
            try:
                add_password_credential(client, user_id, password)
                changed = True
                _mark_changed(result)
            except WarpgateAPIError as e:
                policy_msg = format_password_policy_error(e)
                module.fail_json(
                    changed=changed_before or changed,
                    msg=policy_msg or f"Failed to add password credential: {e.message}",
                    status_code=e.status_code,
                )

        for cred in existing_password_creds:
            if not cred.id:
                continue
            try:
                delete_password_credential(client, user_id, cred.id)
                changed = True
                _mark_changed(result)
            except WarpgateAPIError as e:
                module.fail_json(
                    msg=f"Failed to delete password credential {cred.id}: {e.message}",
                    status_code=e.status_code,
                    changed=changed_before or changed,
                )

    return True


def _public_key_part(key):
    """Key type and data of an OpenSSH public key, without the comment."""
    return " ".join((key or "").split()[:2])


def manage_public_key_credentials(
    client, user_id, desired_keys, module, changed_before=False, result=None
):
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
    try:
        existing_list = get_public_key_credentials(client, user_id)
    except WarpgateAPIError as e:
        module.fail_json(
            changed=changed_before or changed,
            msg=f"Failed to get existing public key credentials: {e.message}",
            status_code=e.status_code,
        )
    labels = [k["label"] for k in desired_keys]
    if len(labels) != len(set(labels)):
        module.fail_json(
            changed=changed_before,
            msg="public_key_credentials contains the same label several times",
        )

    # Warpgate does not enforce unique labels: keep one credential per desired
    # label (the matching one if any) and remove every other one.
    desired_by_label = {k["label"]: k["public_key"] for k in desired_keys or []}
    by_label = {}
    for cred in existing_list:
        by_label.setdefault(cred.label, []).append(cred)
    existing_creds = {}
    creds_to_remove = []
    for label, creds in by_label.items():
        if label not in desired_by_label:
            creds_to_remove.extend(creds)
            continue
        wanted = _public_key_part(desired_by_label[label])
        keep = next(
            (c for c in creds if _public_key_part(c.openssh_public_key) == wanted),
            creds[0],
        )
        existing_creds[label] = keep
        creds_to_remove.extend(c for c in creds if c is not keep)

    # Process desired keys (add or update)
    if desired_keys:
        for key_spec in desired_keys:
            label = key_spec["label"]
            public_key = key_spec["public_key"]

            if label in existing_creds:
                # Key exists, check if update is needed
                existing_cred = existing_creds[label]

                existing_key_part = _public_key_part(existing_cred.openssh_public_key)
                desired_key_part = _public_key_part(public_key)

                if existing_key_part != desired_key_part:
                    # Update needed
                    module.debug(f"Key '{label}' needs update: keys differ")
                    if not module.check_mode:
                        try:
                            updated_cred = update_public_key_credential(
                                client, user_id, existing_cred.id, label, public_key
                            )
                            changed = True
                            _mark_changed(result)
                            managed_creds.append(
                                {
                                    "id": updated_cred.id,
                                    "label": updated_cred.label,
                                    "public_key": updated_cred.openssh_public_key,
                                }
                            )
                        except WarpgateAPIError as e:
                            module.fail_json(
                                changed=changed_before or changed,
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
                        changed = True
                        _mark_changed(result)
                        managed_creds.append(
                            {
                                "id": new_cred.id,
                                "label": new_cred.label,
                                "public_key": new_cred.openssh_public_key,
                            }
                        )
                    except WarpgateAPIError as e:
                        module.fail_json(
                            changed=changed_before or changed,
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

    # Removed last so that a rejected new key never leaves the user without any.
    if creds_to_remove:
        if not module.check_mode:
            for cred in creds_to_remove:
                try:
                    delete_public_key_credential(client, user_id, cred.id)
                    changed = True
                    _mark_changed(result)
                except WarpgateAPIError as e:
                    module.fail_json(
                        changed=changed_before or changed,
                        msg=f"Failed to delete public key credential '{cred.label}': {e.message}",
                        status_code=e.status_code,
                    )
        changed = True

    return changed, managed_creds


def manage_sso_credentials(
    client, user_id, desired_creds, module, changed_before=False, result=None
):
    """
    Manages SSO credentials for a user.
    Ensures the user has exactly the specified (provider, email) pairs
    (adds missing, updates changed, removes extras).
    Passing an empty list removes every SSO credential.
    Returns tuple (changed, list of managed credentials).
    """
    if desired_creds is None:
        desired_creds = []

    changed = False
    managed_creds = []

    try:
        existing_creds = get_sso_credentials(client, user_id)
    except WarpgateAPIError as e:
        module.fail_json(
            changed=changed_before or changed,
            msg=f"Failed to get existing SSO credentials: {e.message}",
            status_code=e.status_code,
        )

    # Index existing credentials by (provider, email) for deterministic matching.
    # Warpgate treats a null provider as a wildcard, so normalize "" → "" and keep it as a key.
    def _key(provider, email):
        return ((provider or "").strip(), (email or "").strip())

    desired_by_key = {
        _key(spec.get("provider"), spec["email"]): spec for spec in desired_creds
    }
    existing_by_key = {}
    creds_to_remove = []
    for cred in existing_creds:
        key = _key(cred.provider, cred.email)
        if key in desired_by_key and key not in existing_by_key:
            existing_by_key[key] = cred
        else:
            creds_to_remove.append(cred)

    for key, spec in desired_by_key.items():
        email = spec["email"]
        provider = (spec.get("provider") or "").strip()
        if key in existing_by_key:
            # (provider, email) already matches — nothing to update.
            cred = existing_by_key[key]
            managed_creds.append(
                {"id": cred.id, "provider": cred.provider, "email": cred.email}
            )
            continue

        if not module.check_mode:
            try:
                new_cred = add_sso_credential(client, user_id, email, provider)
                changed = True
                _mark_changed(result)
                managed_creds.append(
                    {
                        "id": new_cred.id,
                        "provider": new_cred.provider,
                        "email": new_cred.email,
                    }
                )
            except WarpgateAPIError as e:
                module.fail_json(
                    changed=changed_before or changed,
                    msg=f"Failed to add SSO credential (provider={provider}, email={email}): {e.message}",
                    status_code=e.status_code,
                )
        else:
            managed_creds.append(
                {"id": "new-sso-credential-id", "provider": provider, "email": email}
            )
        changed = True

    if creds_to_remove:
        if not module.check_mode:
            for cred in creds_to_remove:
                try:
                    delete_sso_credential(client, user_id, cred.id)
                    changed = True
                    _mark_changed(result)
                except WarpgateAPIError as e:
                    module.fail_json(
                        changed=changed_before or changed,
                        msg=f"Failed to delete SSO credential (provider={cred.provider}, email={cred.email}): {e.message}",
                        status_code=e.status_code,
                    )
        changed = True

    return changed, managed_creds


def manage_user_roles(
    client, user_id, desired_role_ids, module, changed_before=False, result=None
):
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

    try:
        current_roles = get_user_roles(client, user_id)
    except WarpgateAPIError as e:
        module.fail_json(
            changed=changed_before or changed,
            msg=f"Failed to get user roles: {e.message}",
            status_code=e.status_code,
        )

    current_role_ids = set(role.id for role in current_roles)
    desired_role_ids_set = set(desired_role_ids)

    # Add missing roles
    roles_to_add = desired_role_ids_set - current_role_ids
    if roles_to_add:
        if not module.check_mode:
            for role_id in roles_to_add:
                try:
                    add_user_role(client, user_id, role_id)
                    changed = True
                    _mark_changed(result)
                except WarpgateAPIError as e:
                    module.fail_json(
                        changed=changed_before or changed,
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
                    changed = True
                    _mark_changed(result)
                except WarpgateAPIError as e:
                    module.fail_json(
                        changed=changed_before or changed,
                        msg=f"Failed to remove role {role_id} from user: {e.message}",
                        status_code=e.status_code,
                    )
        changed = True

    # Return the final list of role IDs
    final_role_ids = list(desired_role_ids_set)
    return changed, final_role_ids


def manage_user_admin_roles(
    client, user_id, desired_admin_role_ids, module, changed_before=False, result=None
):
    """Ensure the user holds exactly the given admin-role IDs.

    ``desired_admin_role_ids`` is a list of already-resolved admin-role
    UUIDs. An empty list revokes all admin roles from the user.
    """
    if desired_admin_role_ids is None:
        desired_admin_role_ids = []

    changed = False
    try:
        current_roles = get_user_admin_roles(client, user_id)
    except WarpgateAPIError as e:
        module.fail_json(
            changed=changed_before or changed,
            msg=f"Failed to get user admin roles: {e.message}",
            status_code=e.status_code,
        )

    current_ids = {r.id for r in current_roles}
    desired_ids = set(desired_admin_role_ids)

    to_add = desired_ids - current_ids
    to_remove = current_ids - desired_ids

    if to_add:
        if not module.check_mode:
            for role_id in to_add:
                try:
                    add_user_admin_role(client, user_id, role_id)
                    changed = True
                    _mark_changed(result)
                except WarpgateAPIError as e:
                    if e.status_code == 409:
                        continue  # already assigned
                    module.fail_json(
                        changed=changed_before or changed,
                        msg=f"Failed to grant admin role {role_id}: {e.message}",
                        status_code=e.status_code,
                    )
        changed = True
    if to_remove:
        if not module.check_mode:
            for role_id in to_remove:
                try:
                    delete_user_admin_role(client, user_id, role_id)
                    changed = True
                    _mark_changed(result)
                except WarpgateAPIError as e:
                    module.fail_json(
                        changed=changed_before or changed,
                        msg=f"Failed to revoke admin role {role_id}: {e.message}",
                        status_code=e.status_code,
                    )
        changed = True

    return changed, list(desired_ids)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        id=dict(type="str", required=False),
        username=dict(type="str", required=True),
        description=dict(type="str", required=False, default=""),
        rate_limit_bytes_per_second=dict(type="int", required=False),
        allowed_ip_ranges=dict(type="list", elements="str", required=False),
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
        sso_credentials=dict(
            type="list",
            elements="dict",
            required=False,
            options=dict(
                email=dict(type="str", required=True),
                provider=dict(type="str", required=False, default=""),
            ),
        ),
        roles=dict(type="list", elements="str", required=False),
        admin_roles=dict(type="list", elements="str", required=False),
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
    rate_limit_bytes_per_second = module.params.get("rate_limit_bytes_per_second")
    allowed_ip_ranges = module.params.get("allowed_ip_ranges")
    credential_policy = module.params["credential_policy"]
    password_credentials = module.params["password_credentials"]
    update_password = module.params["update_password"]
    public_key_credentials = module.params["public_key_credentials"]
    sso_credentials = module.params["sso_credentials"]
    roles = module.params["roles"]
    admin_roles = module.params.get("admin_roles")
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": None,
        "username": username,
        "description": description,
        "rate_limit_bytes_per_second": rate_limit_bytes_per_second,
        "allowed_ip_ranges": allowed_ip_ranges if allowed_ip_ranges is not None else [],
        "credential_policy": credential_policy,
        "password_credentials": password_credentials if password_credentials else [],
        "public_key_credentials": [],
        "sso_credentials": [],
        "roles": [],
        "admin_roles": [],
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

        # Search for user by username if ID is not provided
        if not user_id and state == "present":
            user_id = find_id_by_exact_name(get_users, client, username)

        # If state=absent, delete the user
        if state == "absent":
            if user_id:
                existing = get_user(client, user_id)
                if existing is None:
                    other_id = find_id_by_exact_name(get_users, client, username)
                    if other_id:
                        module.fail_json(
                            msg=f"User {user_id} not found, but '{username}' exists with ID {other_id}"
                        )
                    user_id = None
                elif fold_username(existing.username) != fold_username(username):
                    module.fail_json(
                        msg=f"User {user_id} is named '{existing.username}', not '{username}'"
                    )
            else:
                # Search for user by username
                user_id = find_id_by_exact_name(get_users, client, username)

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
                    "rate_limit_bytes_per_second": existing_user.rate_limit_bytes_per_second,
                    "allowed_ip_ranges": list(existing_user.allowed_ip_ranges or []),
                }
                diff_after = {
                    "username": username,
                    "description": description,
                    "rate_limit_bytes_per_second": rate_limit_bytes_per_second,
                    "allowed_ip_ranges": (
                        list(allowed_ip_ranges)
                        if allowed_ip_ranges is not None
                        else list(existing_user.allowed_ip_ranges or [])
                    ),
                }

                # Check if modifications are needed
                needs_update = False
                if existing_user.username != username:
                    needs_update = True
                if existing_user.description != description:
                    needs_update = True
                if (
                    rate_limit_bytes_per_second is not None
                    and existing_user.rate_limit_bytes_per_second
                    != rate_limit_bytes_per_second
                ):
                    needs_update = True
                if allowed_ip_ranges is not None and list(
                    existing_user.allowed_ip_ranges or []
                ) != list(allowed_ip_ranges):
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
                            client,
                            user_id,
                            username,
                            description,
                            normalized_policy,
                            rate_limit_bytes_per_second=rate_limit_bytes_per_second,
                            allowed_ip_ranges=allowed_ip_ranges,
                        )
                        result["changed"] = True
                        result["id"] = updated_user.id
                        result["description"] = updated_user.description
                        result["rate_limit_bytes_per_second"] = (
                            updated_user.rate_limit_bytes_per_second
                        )
                        result["allowed_ip_ranges"] = list(
                            updated_user.allowed_ip_ranges or []
                        )
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
                    result["rate_limit_bytes_per_second"] = (
                        existing_user.rate_limit_bytes_per_second
                    )
                    result["allowed_ip_ranges"] = list(
                        existing_user.allowed_ip_ranges or []
                    )
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
                        client,
                        user_id,
                        password_credentials,
                        module,
                        update_password,
                        changed_before=result["changed"],
                        result=result,
                    )
                    if creds_changed:
                        result["changed"] = True

                # Manage public_key_credentials (None is treated as empty list, meaning remove all)
                if public_key_credentials is not None:
                    creds_changed, managed_keys = manage_public_key_credentials(
                        client,
                        user_id,
                        public_key_credentials,
                        module,
                        changed_before=result["changed"],
                        result=result,
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

                # Manage sso_credentials (None = leave untouched, [] = remove all)
                if sso_credentials is not None:
                    sso_changed, managed_sso = manage_sso_credentials(
                        client,
                        user_id,
                        sso_credentials,
                        module,
                        changed_before=result["changed"],
                        result=result,
                    )
                    if sso_changed:
                        result["changed"] = True
                    result["sso_credentials"] = managed_sso
                else:
                    try:
                        existing_sso = get_sso_credentials(client, user_id)
                        result["sso_credentials"] = [
                            {
                                "id": cred.id,
                                "provider": cred.provider,
                                "email": cred.email,
                            }
                            for cred in existing_sso
                        ]
                    except WarpgateAPIError:
                        result["sso_credentials"] = []

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
                        client,
                        user_id,
                        resolved_role_ids,
                        module,
                        changed_before=result["changed"],
                        result=result,
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

                # Manage admin role assignments
                if admin_roles is not None:
                    try:
                        resolved_admin_role_ids = resolve_admin_role_ids(
                            client, admin_roles
                        )
                    except ValueError as e:
                        module.fail_json(msg=str(e), changed=result["changed"])

                    try:
                        current_admin_before = get_user_admin_roles(client, user_id)
                        diff_before["admin_roles"] = [
                            r.id for r in current_admin_before
                        ]
                    except WarpgateAPIError:
                        diff_before["admin_roles"] = []
                    diff_after["admin_roles"] = resolved_admin_role_ids

                    admin_changed, final_admin_ids = manage_user_admin_roles(
                        client,
                        user_id,
                        resolved_admin_role_ids,
                        module,
                        changed_before=result["changed"],
                        result=result,
                    )
                    if admin_changed:
                        result["changed"] = True
                    result["admin_roles"] = final_admin_ids
                else:
                    try:
                        result["admin_roles"] = [
                            r.id for r in get_user_admin_roles(client, user_id)
                        ]
                    except WarpgateAPIError:
                        result["admin_roles"] = []

                if result["changed"]:
                    result["diff"] = {"before": diff_before, "after": diff_after}

            else:
                # Create a new user
                if not module.check_mode:
                    new_user = create_user(client, username, description)
                    result["changed"] = True
                    user_id = new_user.id

                    # POST /users only accepts username + description. Apply
                    # the remaining fields (credential_policy, rate limit,
                    # allowed_ip_ranges) through a follow-up PUT /users/{id}
                    # whenever at least one of them was provided.
                    if (
                        normalized_policy
                        or rate_limit_bytes_per_second is not None
                        or allowed_ip_ranges is not None
                    ):
                        updated_user = update_user(
                            client,
                            user_id,
                            username,
                            description,
                            normalized_policy,
                            rate_limit_bytes_per_second=rate_limit_bytes_per_second,
                            allowed_ip_ranges=allowed_ip_ranges,
                        )
                        if updated_user.credential_policy:
                            policy_dict = updated_user.credential_policy.to_dict()
                            result["credential_policy"] = (
                                policy_dict if policy_dict else None
                            )
                        else:
                            result["credential_policy"] = None
                        result["rate_limit_bytes_per_second"] = (
                            updated_user.rate_limit_bytes_per_second
                        )
                        result["allowed_ip_ranges"] = list(
                            updated_user.allowed_ip_ranges or []
                        )
                    else:
                        result["credential_policy"] = None
                        result["rate_limit_bytes_per_second"] = (
                            new_user.rate_limit_bytes_per_second
                        )
                        result["allowed_ip_ranges"] = list(
                            new_user.allowed_ip_ranges or []
                        )

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
                            changed_before=result["changed"],
                            result=result,
                        )
                        if creds_changed:
                            result["changed"] = True

                    # Manage public_key_credentials (None is treated as empty list, meaning remove all)
                    if public_key_credentials is not None:
                        creds_changed, managed_keys = manage_public_key_credentials(
                            client,
                            user_id,
                            public_key_credentials,
                            module,
                            changed_before=result["changed"],
                            result=result,
                        )
                        if creds_changed:
                            result["changed"] = True
                        result["public_key_credentials"] = managed_keys
                    else:
                        result["public_key_credentials"] = []

                    # Manage sso_credentials
                    if sso_credentials is not None:
                        sso_changed, managed_sso = manage_sso_credentials(
                            client,
                            user_id,
                            sso_credentials,
                            module,
                            changed_before=result["changed"],
                            result=result,
                        )
                        if sso_changed:
                            result["changed"] = True
                        result["sso_credentials"] = managed_sso
                    else:
                        result["sso_credentials"] = []

                    # Manage roles (None is treated as empty list, meaning remove all)
                    if roles is not None:
                        # Resolve role names/IDs to actual role IDs
                        resolved_role_ids = _resolve_role_ids(client, roles)
                        roles_changed, final_role_ids = manage_user_roles(
                            client,
                            user_id,
                            resolved_role_ids,
                            module,
                            changed_before=result["changed"],
                            result=result,
                        )
                        if roles_changed:
                            result["changed"] = True
                        result["roles"] = final_role_ids
                    else:
                        result["roles"] = []

                    # Manage admin-role assignments
                    if admin_roles is not None:
                        try:
                            resolved_admin_role_ids = resolve_admin_role_ids(
                                client, admin_roles
                            )
                        except ValueError as e:
                            module.fail_json(msg=str(e), changed=result["changed"])
                        admin_changed, final_admin_ids = manage_user_admin_roles(
                            client,
                            user_id,
                            resolved_admin_role_ids,
                            module,
                            changed_before=result["changed"],
                            result=result,
                        )
                        if admin_changed:
                            result["changed"] = True
                        result["admin_roles"] = final_admin_ids
                    else:
                        result["admin_roles"] = []
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
                    if sso_credentials:
                        result["sso_credentials"] = [
                            {
                                "id": "new-sso-credential-id",
                                "provider": c.get("provider") or "",
                                "email": c["email"],
                            }
                            for c in sso_credentials
                        ]
                    else:
                        result["sso_credentials"] = []
                    # In check mode, resolve roles but don't actually assign them
                    try:
                        result["roles"] = _resolve_role_ids(client, roles or [])
                    except (ValueError, WarpgateAPIError):
                        result["roles"] = roles or []
                    try:
                        result["admin_roles"] = resolve_admin_role_ids(
                            client, admin_roles or []
                        )
                    except (ValueError, WarpgateAPIError):
                        result["admin_roles"] = admin_roles or []

                result["changed"] = True
                result["diff"] = {
                    "before": {},
                    "after": {
                        "username": username,
                        "description": description,
                        "rate_limit_bytes_per_second": rate_limit_bytes_per_second,
                        "allowed_ip_ranges": allowed_ip_ranges or [],
                        "roles": roles or [],
                        "admin_roles": admin_roles or [],
                    },
                }

        module.exit_json(**result)

    except WarpgateAPIError as e:
        module.fail_json(
            msg=f"Warpgate API error: {e.message}",
            status_code=e.status_code,
            changed=result["changed"],
        )
    except WarpgateClientError as e:
        module.fail_json(msg=f"Warpgate client error: {e!s}", changed=result["changed"])
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e!s}", changed=result["changed"])
    finally:
        if client is not None:
            client.logout()


if __name__ == "__main__":
    main()
