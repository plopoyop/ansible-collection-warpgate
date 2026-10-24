"""
Secret backend management for the Warpgate API (Warpgate >= 0.30).

Secret backends (HashiCorp Vault / OpenBao) let Warpgate resolve target
passwords and private keys at connection time instead of storing them in the
database. The ``auth`` object carries a secret (Vault token or AppRole
secret id) that the API never returns (it is blanked in ``GET`` responses),
so a managed backend with an ``auth`` secret cannot be fully compared.
"""

from typing import Any

from .client import WarpgateAPIError

BACKEND_TYPES = ("vault", "openbao")


class SecretBackend:
    """Represents a Warpgate secret backend."""

    def __init__(
        self,
        id: str,
        name: str,
        backend_type: str = "vault",
        address: str = "",
        namespace: str = "",
        auth: dict[str, Any] | None = None,
        tls_skip_verify: bool = False,
        allowed_paths: list[str] | None = None,
    ):
        self.id = id
        self.name = name
        self.backend_type = backend_type
        self.address = address
        self.namespace = namespace
        self.auth = auth or {}
        self.tls_skip_verify = tls_skip_verify
        self.allowed_paths = allowed_paths or []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SecretBackend":
        return cls(
            id=data["id"],
            name=data["name"],
            backend_type=data.get("backend_type", "vault"),
            address=data.get("address", "") or "",
            namespace=data.get("namespace", "") or "",
            auth=data.get("auth") or {},
            tls_skip_verify=bool(data.get("tls_skip_verify", False)),
            allowed_paths=data.get("allowed_paths") or [],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the secret backend for module output (the auth secret is
        already redacted by the server)."""
        return {
            "id": self.id,
            "name": self.name,
            "backend_type": self.backend_type,
            "address": self.address,
            "namespace": self.namespace,
            "auth": dict(self.auth),
            "tls_skip_verify": self.tls_skip_verify,
            "allowed_paths": list(self.allowed_paths),
        }


def _body(
    name: str,
    backend_type: str,
    address: str,
    auth: dict[str, Any],
    namespace: str = "",
    tls_skip_verify: bool = False,
    allowed_paths: list[str] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": name,
        "backend_type": backend_type,
        "address": address,
        "auth": auth or {},
        "tls_skip_verify": bool(tls_skip_verify),
        "allowed_paths": list(allowed_paths or []),
    }
    if namespace and namespace.strip():
        body["namespace"] = namespace
    return body


def get_secret_backends(client, search: str = "") -> list[SecretBackend]:
    """List all secret backends.

    The listing endpoint has no server-side search; ``search`` is accepted for
    compatibility with :func:`find_by_exact_name` and ignored.
    """
    response = client._request("GET", "/secret-backends")
    return [SecretBackend.from_dict(item) for item in response]


def get_secret_backend(client, backend_id: str) -> SecretBackend | None:
    """Retrieve a secret backend by ID. Returns None if not found."""
    try:
        response = client._request("GET", f"/secret-backends/{backend_id}")
        return SecretBackend.from_dict(response)
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return None
        raise


def create_secret_backend(
    client,
    name: str,
    backend_type: str,
    address: str,
    auth: dict[str, Any],
    namespace: str = "",
    tls_skip_verify: bool = False,
    allowed_paths: list[str] | None = None,
) -> SecretBackend:
    """Create a secret backend."""
    body = _body(
        name, backend_type, address, auth, namespace, tls_skip_verify, allowed_paths
    )
    response = client._request("POST", "/secret-backends", body)
    return SecretBackend.from_dict(response)


def update_secret_backend(
    client,
    backend_id: str,
    name: str,
    backend_type: str,
    address: str,
    auth: dict[str, Any],
    namespace: str = "",
    tls_skip_verify: bool = False,
    allowed_paths: list[str] | None = None,
) -> SecretBackend:
    """Update an existing secret backend."""
    body = _body(
        name, backend_type, address, auth, namespace, tls_skip_verify, allowed_paths
    )
    response = client._request("PUT", f"/secret-backends/{backend_id}", body)
    return SecretBackend.from_dict(response)


def delete_secret_backend(client, backend_id: str) -> None:
    """Delete a secret backend by ID."""
    client._request("DELETE", f"/secret-backends/{backend_id}")
