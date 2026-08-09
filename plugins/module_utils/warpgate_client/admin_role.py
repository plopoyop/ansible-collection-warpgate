"""
Admin role management for the Warpgate API (v0.23+).

Admin roles are distinct from access roles: they grant fine-grained
permissions on the admin UI / API itself (create targets, terminate
sessions, view recordings, etc.) rather than access to backends.
"""

from typing import Any

from .client import WarpgateAPIError

PERMISSION_FIELDS = (
    "targets_create",
    "targets_edit",
    "targets_delete",
    "users_create",
    "users_edit",
    "users_delete",
    "access_roles_create",
    "access_roles_edit",
    "access_roles_delete",
    "access_roles_assign",
    "sessions_view",
    "sessions_terminate",
    "recordings_view",
    "tickets_create",
    "tickets_delete",
    "config_edit",
    "admin_roles_manage",
    "ticket_requests_manage",
)


class AdminRole:
    """Represents a Warpgate admin role with its full permission set."""

    def __init__(
        self,
        id: str = "",
        name: str = "",
        description: str = "",
        permissions: dict[str, bool] | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.permissions = {f: False for f in PERMISSION_FIELDS}
        if permissions:
            self.permissions.update(
                {k: bool(v) for k, v in permissions.items() if k in PERMISSION_FIELDS}
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdminRole":
        perms = {f: bool(data.get(f, False)) for f in PERMISSION_FIELDS}
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            permissions=perms,
        )

    def to_request_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {"name": self.name}
        if self.description:
            body["description"] = self.description
        for f in PERMISSION_FIELDS:
            body[f] = bool(self.permissions.get(f, False))
        return body


def get_admin_roles(client) -> list[AdminRole]:
    """List all admin roles."""
    response = client._request("GET", "/admin-roles")
    return [AdminRole.from_dict(r) for r in response]


def get_admin_role(client, role_id: str) -> AdminRole | None:
    """Retrieve a single admin role by ID. Returns None if not found."""
    try:
        response = client._request("GET", f"/admin-roles/{role_id}")
        return AdminRole.from_dict(response)
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return None
        raise


def create_admin_role(
    client,
    name: str,
    description: str = "",
    permissions: dict[str, bool] | None = None,
) -> AdminRole:
    role = AdminRole(name=name, description=description, permissions=permissions)
    response = client._request("POST", "/admin-roles", role.to_request_body())
    return AdminRole.from_dict(response)


def update_admin_role(
    client,
    role_id: str,
    name: str,
    description: str = "",
    permissions: dict[str, bool] | None = None,
) -> AdminRole:
    role = AdminRole(name=name, description=description, permissions=permissions)
    response = client._request("PUT", f"/admin-roles/{role_id}", role.to_request_body())
    return AdminRole.from_dict(response)


def delete_admin_role(client, role_id: str) -> None:
    client._request("DELETE", f"/admin-roles/{role_id}")


def get_admin_role_users(client, role_id: str) -> list[dict[str, Any]]:
    """List users that hold a given admin role (raw dicts from the API)."""
    try:
        return client._request("GET", f"/admin-roles/{role_id}/users") or []
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return []
        raise


def get_user_admin_roles(client, user_id: str) -> list[AdminRole]:
    """List the admin roles held by a given user."""
    try:
        response = client._request("GET", f"/users/{user_id}/admin-roles") or []
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return []
        raise
    return [AdminRole.from_dict(r) for r in response]


def add_user_admin_role(client, user_id: str, role_id: str) -> None:
    """Grant an admin role to a user."""
    client._request("POST", f"/users/{user_id}/admin-roles/{role_id}")


def delete_user_admin_role(client, user_id: str, role_id: str) -> None:
    """Revoke an admin role from a user."""
    client._request("DELETE", f"/users/{user_id}/admin-roles/{role_id}")


def resolve_admin_role_id(client, spec: str) -> str:
    """Resolve an admin-role UUID or name to an admin-role UUID.

    Raises ``ValueError`` if the role cannot be found.
    """
    if not spec:
        raise ValueError("admin role spec is empty")
    if len(spec) == 36 and spec.count("-") == 4:
        role = get_admin_role(client, spec)
        if role:
            return role.id
    for role in get_admin_roles(client):
        if role.name == spec:
            return role.id
    raise ValueError(f"Admin role '{spec}' not found (neither as ID nor as name)")


def resolve_admin_role_ids(client, specs: list[str]) -> list[str]:
    """Resolve a list of admin-role UUIDs or names to UUIDs.

    The admin-role list is fetched at most once and cached locally for
    name-based lookups.
    """
    if not specs:
        return []

    resolved: list[str] = []
    all_roles: list[AdminRole] | None = None
    for spec in specs:
        if len(spec) == 36 and spec.count("-") == 4:
            role = get_admin_role(client, spec)
            if role:
                resolved.append(role.id)
                continue
        if all_roles is None:
            all_roles = get_admin_roles(client)
        match = next((r for r in all_roles if r.name == spec), None)
        if match is None:
            raise ValueError(
                f"Admin role '{spec}' not found (neither as ID nor as name)"
            )
        resolved.append(match.id)
    return resolved
