#!/usr/bin/python


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: warpgate_secret_backend

short_description: Manages Warpgate secret backends (Vault / OpenBao)

description:
    - Create, update and delete secret backends in Warpgate (>= 0.30).
    - A secret backend (HashiCorp Vault or OpenBao) lets Warpgate resolve
      target passwords and SSH private keys at connection time instead of
      storing them in its database.
    - Create backends before the targets that reference them via
      C(secret://<backend>/...). Deleting a backend still referenced by a
      target returns HTTP 409; remove the referencing targets first.

version_added: "2.3.0"

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
            - Secret backend ID (for update/delete operations).
        type: str
        required: false
    name:
        description:
            - Secret backend name (must be unique).
        type: str
        required: true
    backend_type:
        description:
            - Backend implementation. Required when O(state=present).
        type: str
        choices: ["vault", "openbao"]
        required: false
    address:
        description:
            - Base URL of the Vault/OpenBao server. Required when O(state=present).
        type: str
        required: false
    namespace:
        description:
            - Optional Vault/OpenBao namespace.
        type: str
        required: false
        default: ""
    auth:
        description:
            - Authentication configuration for the backend, a mapping with a
              C(method) discriminator. Required when O(state=present).
            - C(method=Token) takes a C(token); C(method=AppRole) takes
              C(role_id), C(secret_id) and an optional C(mount);
              C(method=Kubernetes) takes a C(role) and an optional C(mount).
            - The server blanks the stored secret (token / secret id) in API
              responses, so the module cannot detect a change limited to the
              secret value; change another field or recreate the backend to
              rotate it.
        type: dict
        required: false
    tls_skip_verify:
        description:
            - Skip TLS certificate verification when connecting to the backend.
        type: bool
        required: false
        default: false
    allowed_paths:
        description:
            - Path prefixes the backend may be used for (matched on whole
              segments), e.g. C(mount/path) for a KV read or C(mount/sign/role)
              for SSH certificate signing. Empty allows any path.
        type: list
        elements: str
        required: false
        default: []
    state:
        description:
            - Desired state of the secret backend.
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
- name: Create a Vault secret backend (token auth)
  warpgate_secret_backend:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "vault-prod"
    backend_type: "vault"
    address: "https://vault.example.com:8200"
    auth:
      method: "Token"
      token: "{{ vault_token }}"
    allowed_paths:
      - "secret/data/warpgate"
    state: present

- name: Create an OpenBao backend with AppRole auth
  warpgate_secret_backend:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "openbao-ssh-ca"
    backend_type: "openbao"
    address: "https://openbao.example.com:8200"
    auth:
      method: "AppRole"
      role_id: "{{ bao_role_id }}"
      secret_id: "{{ bao_secret_id }}"
      mount: "approle"
    allowed_paths:
      - "ssh/sign/warpgate"

- name: Delete a secret backend
  warpgate_secret_backend:
    host: "https://warpgate.example.com/@warpgate/admin/api/"
    token: "{{ warpgate_api_token }}"
    name: "vault-prod"
    state: absent
"""

RETURN = r"""
id:
    description: Secret backend ID
    type: str
    returned: always
name:
    description: Secret backend name
    type: str
    returned: always
backend_type:
    description: Backend implementation (vault or openbao)
    type: str
    returned: when available
address:
    description: Backend server address
    type: str
    returned: when available
allowed_paths:
    description: Allowed path prefixes
    type: list
    returned: when available
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    find_by_exact_name,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.secret_backend import (
    create_secret_backend,
    delete_secret_backend,
    get_secret_backend,
    get_secret_backends,
    update_secret_backend,
)

# Secret sub-keys of ``auth`` that the server blanks in GET responses and that
# therefore cannot be compared for idempotence.
_AUTH_SECRET_KEYS = ("token", "secret_id")


def _auth_comparable(auth):
    """Normalize an auth mapping for idempotent comparison: drop the secret
    sub-keys the server blanks, and drop ``None`` values (the server echoes an
    unset ``mount`` back as ``null`` while the user simply omits the key)."""
    return {
        k: v
        for k, v in (auth or {}).items()
        if k not in _AUTH_SECRET_KEYS and v is not None
    }


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        id=dict(type="str", required=False),
        name=dict(type="str", required=True),
        backend_type=dict(type="str", required=False, choices=["vault", "openbao"]),
        address=dict(type="str", required=False),
        namespace=dict(type="str", required=False, default=""),
        auth=dict(type="dict", required=False, no_log=True),
        tls_skip_verify=dict(type="bool", required=False, default=False),
        allowed_paths=dict(type="list", elements="str", required=False, default=[]),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[["state", "present", ["backend_type", "address", "auth"]]],
    )

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )

    backend_id = module.params["id"]
    name = module.params["name"]
    backend_type = module.params["backend_type"]
    address = module.params["address"]
    namespace = module.params["namespace"]
    auth = module.params["auth"]
    tls_skip_verify = module.params["tls_skip_verify"]
    allowed_paths = module.params["allowed_paths"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {
        "changed": False,
        "id": None,
        "name": name,
        "backend_type": backend_type,
        "address": address,
        "allowed_paths": allowed_paths,
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
        if backend_id:
            existing = get_secret_backend(client, backend_id)
        else:
            existing = find_by_exact_name(get_secret_backends, client, name)
            if existing is not None:
                backend_id = existing.id

        if state == "absent":
            if not existing:
                module.exit_json(**result)
            if not module.check_mode:
                delete_secret_backend(client, existing.id)
            result["changed"] = True
            result["id"] = existing.id
            result["diff"] = {"before": {"name": existing.name}, "after": {}}
            module.exit_json(**result)

        # present
        if existing:
            needs_update = (
                existing.name != name
                or existing.backend_type != backend_type
                or (existing.address or "") != (address or "")
                or (existing.namespace or "") != (namespace or "")
                or bool(existing.tls_skip_verify) != bool(tls_skip_verify)
                or sorted(existing.allowed_paths or []) != sorted(allowed_paths or [])
                or _auth_comparable(existing.auth) != _auth_comparable(auth)
            )

            if needs_update:
                result["diff"] = {
                    "before": {
                        "backend_type": existing.backend_type,
                        "address": existing.address,
                        "namespace": existing.namespace,
                        "tls_skip_verify": existing.tls_skip_verify,
                        "allowed_paths": existing.allowed_paths,
                        "auth": _auth_comparable(existing.auth),
                    },
                    "after": {
                        "backend_type": backend_type,
                        "address": address,
                        "namespace": namespace,
                        "tls_skip_verify": tls_skip_verify,
                        "allowed_paths": allowed_paths,
                        "auth": _auth_comparable(auth),
                    },
                }
                if not module.check_mode:
                    updated = update_secret_backend(
                        client,
                        existing.id,
                        name,
                        backend_type,
                        address,
                        auth,
                        namespace,
                        tls_skip_verify,
                        allowed_paths,
                    )
                    result["id"] = updated.id
                    result["address"] = updated.address
                    result["allowed_paths"] = updated.allowed_paths
                else:
                    result["id"] = existing.id
                result["changed"] = True
            else:
                result["id"] = existing.id
                result["address"] = existing.address
                result["allowed_paths"] = existing.allowed_paths
            module.exit_json(**result)

        # create
        if not module.check_mode:
            created = create_secret_backend(
                client,
                name,
                backend_type,
                address,
                auth,
                namespace,
                tls_skip_verify,
                allowed_paths,
            )
            result["id"] = created.id
            result["address"] = created.address
            result["allowed_paths"] = created.allowed_paths
        else:
            result["id"] = "new-secret-backend-id"
        result["changed"] = True
        result["diff"] = {
            "before": {},
            "after": {
                "name": name,
                "backend_type": backend_type,
                "address": address,
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
