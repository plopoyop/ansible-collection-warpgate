"""
Target management for the Warpgate API

This module provides functions to manage Warpgate targets (SSH, HTTP, MySQL, PostgreSQL).
"""

import urllib.parse
from typing import Any, Dict, List, Optional

from .client import WarpgateAPIError

# TLS mode constants
TLS_MODE_DISABLED = "Disabled"
TLS_MODE_PREFERRED = "Preferred"
TLS_MODE_REQUIRED = "Required"


class TLS:
    """Represents TLS configuration for a target"""

    def __init__(self, mode: str, verify: bool):
        self.mode = mode
        self.verify = verify

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {"mode": self.mode, "verify": self.verify}


class Target:
    """Represents a Warpgate target"""

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        group_id: str = "",
        allow_roles: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.group_id = group_id
        self.allow_roles = allow_roles or []
        self.options = options or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Target":
        """Create a Target from a dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            group_id=data.get("group_id", ""),
            allow_roles=data.get("allow_roles", []),
            options=data.get("options", {}),
        )


def get_targets(client, search: str = "") -> List[Target]:
    """
    Retrieves all targets from the Warpgate API, optionally filtered by search term.

    Args:
        client: WarpgateClient instance
        search: Optional search term to filter targets

    Returns:
        List of Target objects
    """
    path = "/targets"
    if search:
        path += f"?search={urllib.parse.quote(search)}"

    response = client._request("GET", path)
    return [Target.from_dict(target) for target in response]


def get_target(client, target_id: str) -> Optional[Target]:
    """
    Retrieves a specific target by ID from the Warpgate API.

    Args:
        client: WarpgateClient instance
        target_id: Target ID

    Returns:
        Target object if found, None otherwise
    """
    try:
        response = client._request("GET", f"/targets/{target_id}")
        return Target.from_dict(response)
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return None
        raise


def create_target(
    client,
    name: str,
    description: str = "",
    group_id: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> Target:
    """
    Creates a new target in Warpgate with the provided name, description, and configuration options.

    Args:
        client: WarpgateClient instance
        name: Target name
        description: Optional description
        group_id: Optional target group ID
        options: Target options (SSH, HTTP, MySQL, or PostgreSQL configuration)

    Returns:
        Created Target object
    """
    body = {"name": name, "description": description, "options": options or {}}
    if group_id and group_id.strip():
        body["group_id"] = group_id
    response = client._request("POST", "/targets", body)
    return Target.from_dict(response)


def update_target(
    client,
    target_id: str,
    name: str,
    description: str = "",
    group_id: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> Target:
    """
    Updates an existing target's information including name, description, and configuration options.

    Args:
        client: WarpgateClient instance
        target_id: Target ID
        name: Updated target name
        description: Updated description
        group_id: Updated target group ID
        options: Updated target options

    Returns:
        Updated Target object
    """
    body = {"name": name, "description": description, "options": options or {}}
    if group_id and group_id.strip():
        body["group_id"] = group_id
    response = client._request("PUT", f"/targets/{target_id}", body)
    return Target.from_dict(response)


def delete_target(client, target_id: str) -> None:
    """
    Removes a target from Warpgate by its ID.

    Args:
        client: WarpgateClient instance
        target_id: Target ID to delete
    """
    client._request("DELETE", f"/targets/{target_id}")
