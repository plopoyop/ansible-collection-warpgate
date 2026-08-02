"""
Role management for the Warpgate API

This module provides functions to manage Warpgate access roles and their
assignments to users and targets. Since v0.23, user-role assignments can
carry an ``expires_at`` timestamp; this is exposed through the new
:class:`UserRoleAssignment` type and the ``update_user_role`` /
``get_user_role`` helpers.
"""

import urllib.parse
from typing import Any

from .client import WarpgateAPIError


class Role:
    """Represents a Warpgate access role"""

    def __init__(
        self, id: str, name: str, description: str = "", is_default: bool = False
    ):
        self.id = id
        self.name = name
        self.description = description
        # Warpgate >= 0.24: default roles are auto-assigned to new users.
        self.is_default = is_default

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Role":
        """Create a Role from a dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            is_default=bool(data.get("is_default", False)),
        )


class UserRoleAssignment:
    """Represents a single user-to-role assignment (with optional expiry).

    Returned by ``GET /users/{id}/roles`` (list) and ``GET /users/{id}/roles/{role_id}``
    since Warpgate v0.23. Has the same ``id`` / ``name`` / ``description`` as
    :class:`Role` so it can be used interchangeably where only those fields
    are needed.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        granted_at: str = "",
        expires_at: str = "",
        is_expired: bool = False,
        is_active: bool = True,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.granted_at = granted_at
        self.expires_at = expires_at
        self.is_expired = is_expired
        self.is_active = is_active

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserRoleAssignment":
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            granted_at=data.get("granted_at", "") or "",
            expires_at=data.get("expires_at", "") or "",
            is_expired=bool(data.get("is_expired", False)),
            is_active=bool(data.get("is_active", True)),
        )


def get_roles(client, search: str = "") -> list[Role]:
    """
    Retrieves all roles from the Warpgate API, optionally filtered by search term.

    Args:
        client: WarpgateClient instance
        search: Optional search term to filter roles

    Returns:
        List of Role objects
    """
    path = "/roles"
    if search:
        path += f"?search={urllib.parse.quote(search)}"

    response = client._request("GET", path)
    return [Role.from_dict(role) for role in response]


def get_role(client, role_id: str) -> Role | None:
    """
    Retrieves a specific role by ID from the Warpgate API.

    Args:
        client: WarpgateClient instance
        role_id: Role ID

    Returns:
        Role object if found, None otherwise
    """
    try:
        response = client._request("GET", f"/role/{role_id}")
        return Role.from_dict(response)
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return None
        raise


def create_role(
    client, name: str, description: str = "", is_default: bool | None = None
) -> Role:
    """
    Creates a new role in Warpgate with the provided name and description.

    Args:
        client: WarpgateClient instance
        name: Role name
        description: Optional description
        is_default: Auto-assign this role to new users (Warpgate >= 0.24).
            ``None`` omits the field for compatibility with older servers.

    Returns:
        Created Role object
    """
    body: dict[str, Any] = {"name": name, "description": description}
    if is_default is not None:
        body["is_default"] = is_default
    response = client._request("POST", "/roles", body)
    return Role.from_dict(response)


def update_role(
    client,
    role_id: str,
    name: str,
    description: str = "",
    is_default: bool | None = None,
) -> Role:
    """
    Updates an existing role's information including name and description.

    Args:
        client: WarpgateClient instance
        role_id: Role ID
        name: Updated role name
        description: Updated description
        is_default: Auto-assign this role to new users (Warpgate >= 0.24).
            ``None`` omits the field for compatibility with older servers.

    Returns:
        Updated Role object
    """
    body: dict[str, Any] = {"name": name, "description": description}
    if is_default is not None:
        body["is_default"] = is_default
    response = client._request("PUT", f"/role/{role_id}", body)
    return Role.from_dict(response)


def delete_role(client, role_id: str) -> None:
    """
    Removes a role from Warpgate by its ID.

    Args:
        client: WarpgateClient instance
        role_id: Role ID to delete
    """
    client._request("DELETE", f"/role/{role_id}")


def get_user_roles(client, user_id: str) -> list[UserRoleAssignment]:
    """
    Retrieves all roles assigned to a specific user, including assignment
    metadata (granted_at, expires_at, is_expired, is_active).

    Since Warpgate v0.23 this endpoint returns ``UserRoleAssignmentResponse``
    objects instead of bare roles. Callers that only need ``.id`` can use the
    returned :class:`UserRoleAssignment` unchanged.
    """
    response = client._request("GET", f"/users/{user_id}/roles")
    return [UserRoleAssignment.from_dict(r) for r in response]


def get_user_role(client, user_id: str, role_id: str) -> UserRoleAssignment | None:
    """Retrieves a single user-role assignment (v0.23+)."""
    try:
        response = client._request("GET", f"/users/{user_id}/roles/{role_id}")
        return UserRoleAssignment.from_dict(response)
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return None
        raise


def add_user_role(
    client, user_id: str, role_id: str, expires_at: str | None = None
) -> UserRoleAssignment | None:
    """
    Assigns a role to a user, optionally with an expiry timestamp (v0.23+).

    Args:
        client: WarpgateClient instance
        user_id: User ID
        role_id: Role ID to assign
        expires_at: Optional ISO-8601 expiry timestamp. ``None`` = permanent.

    Returns:
        The created :class:`UserRoleAssignment` when the server returns one,
        otherwise ``None`` (older server builds return an empty 201).
    """
    body: dict[str, Any] = {}
    if expires_at:
        body["expires_at"] = expires_at
    response = client._request(
        "POST", f"/users/{user_id}/roles/{role_id}", body if body else None
    )
    if isinstance(response, dict) and response.get("id"):
        return UserRoleAssignment.from_dict(response)
    return None


def update_user_role(
    client, user_id: str, role_id: str, expires_at: str | None = None
) -> UserRoleAssignment:
    """Updates the expiry of an existing user-role assignment (v0.23+).

    Pass ``expires_at=None`` to clear the expiry and make the assignment
    permanent; pass an ISO-8601 string to set a new expiry.
    """
    body: dict[str, Any] = {"expires_at": expires_at}
    response = client._request("PUT", f"/users/{user_id}/roles/{role_id}", body)
    return UserRoleAssignment.from_dict(response)


def delete_user_role(client, user_id: str, role_id: str) -> None:
    """
    Removes a role assignment from a user in Warpgate.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        role_id: Role ID to remove
    """
    client._request("DELETE", f"/users/{user_id}/roles/{role_id}")


def get_target_roles(client, target_id: str) -> list[Role]:
    """
    Retrieves all roles assigned to a specific target.

    Args:
        client: WarpgateClient instance
        target_id: Target ID

    Returns:
        List of Role objects assigned to the target
    """
    response = client._request("GET", f"/targets/{target_id}/roles")
    return [Role.from_dict(role) for role in response]


def add_target_role(client, target_id: str, role_id: str) -> None:
    """
    Assigns a role to a target in Warpgate.

    Args:
        client: WarpgateClient instance
        target_id: Target ID
        role_id: Role ID to assign
    """
    client._request("POST", f"/targets/{target_id}/roles/{role_id}")


def delete_target_role(client, target_id: str, role_id: str) -> None:
    """
    Removes a role assignment from a target in Warpgate.

    Args:
        client: WarpgateClient instance
        target_id: Target ID
        role_id: Role ID to remove
    """
    client._request("DELETE", f"/targets/{target_id}/roles/{role_id}")
