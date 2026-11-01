"""
Outbound SSH client key management for the Warpgate API (Warpgate >= 0.27).

These are the keys Warpgate uses to authenticate *to* SSH targets (the former
``client-ed25519`` / ``client-rsa`` files, moved into the database in 0.27).
They are distinct from the per-user login public keys handled by
``warpgate_public_key_credential``.

The private key material is never returned by ``GET``; only the public key,
label, kind and ``is_default`` flag are listed. Callers therefore identify a
managed key by its ``label``.
"""

from typing import Any


class SSHClientKey:
    """Represents an outbound SSH client key."""

    def __init__(
        self,
        id: str,
        label: str = "",
        kind: str = "",
        public_key: str = "",
        is_default: bool = False,
        secret_backend: str | None = None,
    ):
        self.id = id
        self.label = label
        self.kind = kind
        self.public_key = public_key
        self.is_default = is_default
        self.secret_backend = secret_backend

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SSHClientKey":
        return cls(
            id=data["id"],
            label=data.get("label", "") or "",
            kind=data.get("kind", "") or "",
            public_key=data.get("public_key", "") or "",
            is_default=bool(data.get("is_default", False)),
            secret_backend=data.get("secret_backend"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for module output (never includes private key material)."""
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "public_key": self.public_key,
            "is_default": self.is_default,
            "secret_backend": self.secret_backend,
        }


def get_ssh_client_keys(client) -> list[SSHClientKey]:
    """List all outbound SSH client keys."""
    response = client._request("GET", "/ssh/own-keys")
    return [SSHClientKey.from_dict(item) for item in response]


def find_ssh_client_key_by_label(client, label: str) -> SSHClientKey | None:
    """Return the first SSH client key with the given label, or None."""
    for key in get_ssh_client_keys(client):
        if key.label == label:
            return key
    return None


def import_ssh_client_key(
    client, label: str, secret_key: str, is_default: bool = False
) -> SSHClientKey:
    """Import an existing private key (OpenSSH or PKCS#8 PEM, no passphrase)."""
    body = {"label": label, "secret_key": secret_key, "is_default": bool(is_default)}
    response = client._request("POST", "/ssh/own-keys", body)
    return SSHClientKey.from_dict(response)


def import_ssh_client_key_reference(
    client, label: str, reference: str, is_default: bool = False
) -> SSHClientKey:
    """Import a key via a ``secret://backend/mount/path#field`` reference."""
    body = {"label": label, "reference": reference, "is_default": bool(is_default)}
    response = client._request("POST", "/ssh/own-keys/reference", body)
    return SSHClientKey.from_dict(response)


def update_ssh_client_key(
    client, key_id: str, label: str, is_default: bool = False
) -> SSHClientKey:
    """Update an SSH client key's metadata (label / default flag)."""
    body = {"label": label, "is_default": bool(is_default)}
    response = client._request("PUT", f"/ssh/own-keys/{key_id}", body)
    return SSHClientKey.from_dict(response)


def delete_ssh_client_key(client, key_id: str) -> None:
    """Delete an SSH client key by ID."""
    client._request("DELETE", f"/ssh/own-keys/{key_id}")
