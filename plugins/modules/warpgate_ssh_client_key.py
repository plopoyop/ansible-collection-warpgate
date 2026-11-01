#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_ssh_client_key

short_description: Manages Warpgate outbound SSH client keys

description:
    - Import, update and delete the SSH client keys Warpgate uses to
      authenticate to its SSH targets (Warpgate >= 0.27, stored in the
      database since that release).
    - These are distinct from the per-user login public keys managed by
      M(plopoyop.warpgate.warpgate_public_key_credential).
    - Keys are identified by their O(label); the private key is never returned
      by the API, so re-importing an existing label is skipped (idempotent) and
      rotating the key material requires removing and re-adding it.

version_added: "2.4.0"

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
            - SSH client key ID (alternative to O(label) for update/delete).
        type: str
        required: false
    label:
        description:
            - Human-readable label identifying the key. Used as the idempotency
              key when O(id) is not given.
        type: str
        required: true
    private_key:
        description:
            - Private key material to import, in OpenSSH or PKCS#8 PEM format,
              without a passphrase. Mutually exclusive with O(reference).
            - Only used when the key does not already exist (the API never
              returns the private key, so it cannot be compared).
        type: str
        required: false
    reference:
        description:
            - A C(secret://backend/mount/path#field) reference resolving to a
              private key, instead of inline O(private_key) (Warpgate >= 0.30).
              Mutually exclusive with O(private_key).
        type: str
        required: false
    is_default:
        description:
            - Whether this key is the default client key used for targets that
              do not specify their own.
        type: bool
        required: false
        default: false
    state:
        description:
            - Desired state of the SSH client key.
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

EXAMPLES = r"""
- name: Import the outbound SSH client key from a vault variable
  warpgate_ssh_client_key:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    label: "default-client-key"
    private_key: "{{ vault_warpgate_client_key }}"
    is_default: true
    state: present

- name: Import an outbound key from a secret backend reference
  warpgate_ssh_client_key:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    label: "vault-signed-key"
    reference: "secret://vault-prod/ssh/keys/warpgate#private_key"

- name: Remove an outbound SSH client key
  warpgate_ssh_client_key:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    label: "default-client-key"
    state: absent
"""

RETURN = r"""
id:
    description: SSH client key ID
    type: str
    returned: always
label:
    description: SSH client key label
    type: str
    returned: always
kind:
    description: Key algorithm (e.g. ed25519, rsa)
    type: str
    returned: when available
public_key:
    description: OpenSSH public key
    type: str
    returned: when available
is_default:
    description: Whether this key is the default client key
    type: bool
    returned: when available
secret_backend:
    description: Name of the secret backend storing the key, if any
    type: str
    returned: when available
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.ssh_client_key import (
    delete_ssh_client_key,
    find_ssh_client_key_by_label,
    get_ssh_client_keys,
    import_ssh_client_key,
    import_ssh_client_key_reference,
    update_ssh_client_key,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        id=dict(type="str", required=False),
        label=dict(type="str", required=True),
        private_key=dict(type="str", required=False, no_log=True),
        reference=dict(type="str", required=False),
        is_default=dict(type="bool", required=False, default=False),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[["private_key", "reference"]],
    )

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )

    key_id = module.params["id"]
    label = module.params["label"]
    private_key = module.params["private_key"]
    reference = module.params["reference"]
    is_default = module.params["is_default"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": None,
        "label": label,
        "is_default": is_default,
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
        if key_id:
            existing = next(
                (k for k in get_ssh_client_keys(client) if k.id == key_id), None
            )
        else:
            existing = find_ssh_client_key_by_label(client, label)

        if key_id and not existing and state == "present":
            module.fail_json(msg=f"No SSH client key found with id '{key_id}'")

        if state == "absent":
            if not existing:
                module.exit_json(**result)
            if not module.check_mode:
                try:
                    delete_ssh_client_key(client, existing.id)
                except WarpgateAPIError as e:
                    if e.status_code == 400:
                        module.fail_json(
                            msg=(
                                "Cannot delete SSH client key '%s': Warpgate "
                                "requires at least one client key to remain (%s)"
                                % (existing.label, e.message)
                            ),
                            status_code=e.status_code,
                        )
                    raise
            result["changed"] = True
            result["id"] = existing.id
            result["diff"] = {
                "before": {"label": existing.label, "is_default": existing.is_default},
                "after": {},
            }
            module.exit_json(**result)

        # present
        if existing:
            # The private key cannot be compared (never returned); only
            # reconcile metadata. Re-importing an existing label is skipped.
            needs_update = existing.label != label or bool(existing.is_default) != bool(
                is_default
            )
            if needs_update:
                result["diff"] = {
                    "before": {
                        "label": existing.label,
                        "is_default": existing.is_default,
                    },
                    "after": {"label": label, "is_default": is_default},
                }
                if not module.check_mode:
                    updated = update_ssh_client_key(
                        client, existing.id, label, is_default
                    )
                    result["id"] = updated.id
                    result["kind"] = updated.kind
                    result["public_key"] = updated.public_key
                    result["is_default"] = updated.is_default
                    result["secret_backend"] = updated.secret_backend
                else:
                    result["id"] = existing.id
                result["changed"] = True
            else:
                result["id"] = existing.id
                result["kind"] = existing.kind
                result["public_key"] = existing.public_key
                result["is_default"] = existing.is_default
                result["secret_backend"] = existing.secret_backend
            module.exit_json(**result)

        # create (import)
        if not private_key and not reference:
            module.fail_json(
                msg=(
                    "SSH client key '%s' does not exist; provide 'private_key' or "
                    "'reference' to import it" % label
                )
            )

        if not module.check_mode:
            try:
                if private_key:
                    created = import_ssh_client_key(
                        client, label, private_key, is_default
                    )
                else:
                    created = import_ssh_client_key_reference(
                        client, label, reference, is_default
                    )
            except WarpgateAPIError as e:
                if e.status_code == 409:
                    module.fail_json(
                        msg=(
                            "Cannot import SSH client key '%s': this key material is "
                            "already imported (possibly under another label) (%s)"
                            % (label, e.message)
                        ),
                        status_code=e.status_code,
                    )
                raise
            result["id"] = created.id
            result["kind"] = created.kind
            result["public_key"] = created.public_key
            result["is_default"] = created.is_default
            result["secret_backend"] = created.secret_backend
        else:
            result["id"] = "new-ssh-client-key-id"
        result["changed"] = True
        result["diff"] = {
            "before": {},
            "after": {"label": label, "is_default": is_default},
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
