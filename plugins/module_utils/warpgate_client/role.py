"""
Role management for the Warpgate API

This module provides functions to manage Warpgate roles and role assignments.
"""

import urllib.parse
from typing import Any, Dict, List, Optional

from .client import WarpgateAPIError


class Role:
    """Represents a Warpgate role"""

    def __init__(self, id: str, name: str, description: str = ""):
        self.id = id
        self.name = name
        self.description = description

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        """Create a Role from a dictionary"""
        return cls(
            id=data["id"], name=data["name"], description=data.get("description", "")
        )


def get_roles(client, search: str = "") -> List[Role]:
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


def get_role(client, role_id: str) -> Optional[Role]:
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


def create_role(client, name: str, description: str = "") -> Role:
    """
    Creates a new role in Warpgate with the provided name and description.

    Args:
        client: WarpgateClient instance
        name: Role name
        description: Optional description

    Returns:
        Created Role object
    """
    body = {"name": name, "description": description}
    response = client._request("POST", "/roles", body)
    return Role.from_dict(response)


def update_role(client, role_id: str, name: str, description: str = "") -> Role:
    """
    Updates an existing role's information including name and description.

    Args:
        client: WarpgateClient instance
        role_id: Role ID
        name: Updated role name
        description: Updated description

    Returns:
        Updated Role object
    """
    body = {"name": name, "description": description}
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


def get_user_roles(client, user_id: str) -> List[Role]:
    """
    Retrieves all roles assigned to a specific user.

    Args:
        client: WarpgateClient instance
        user_id: User ID

    Returns:
        List of Role objects assigned to the user
    """
    response = client._request("GET", f"/users/{user_id}/roles")
    return [Role.from_dict(role) for role in response]


def add_user_role(client, user_id: str, role_id: str) -> None:
    """
    Assigns a role to a user in Warpgate.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        role_id: Role ID to assign
    """
    client._request("POST", f"/users/{user_id}/roles/{role_id}")


def delete_user_role(client, user_id: str, role_id: str) -> None:
    """
    Removes a role assignment from a user in Warpgate.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        role_id: Role ID to remove
    """
    client._request("DELETE", f"/users/{user_id}/roles/{role_id}")


def get_target_roles(client, target_id: str) -> List[Role]:
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
