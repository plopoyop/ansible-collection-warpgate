"""
Target group management for the Warpgate API

This module provides functions to manage Warpgate target groups.
"""

import urllib.parse
from typing import Any, Dict, List, Optional

from .client import WarpgateAPIError


class TargetGroup:
    """Represents a Warpgate target group"""

    def __init__(self, id: str, name: str, description: str = "", color: str = ""):
        self.id = id
        self.name = name
        self.description = description
        self.color = color

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetGroup":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", "") or "",
            color=data.get("color", "") or "",
        )


def get_target_groups(client, search: str = "") -> List[TargetGroup]:
    """
    Retrieves all target groups from the Warpgate API, optionally filtered by search term.

    Note: This relies on the `/target-groups` listing endpoint.
    """
    path = "/target-groups"
    if search:
        path += f"?search={urllib.parse.quote(search)}"

    response = client._request("GET", path)
    return [TargetGroup.from_dict(item) for item in response]


def get_target_group(client, group_id: str) -> Optional[TargetGroup]:
    """Retrieves a specific target group by ID. Returns None if not found."""
    try:
        response = client._request("GET", f"/target-groups/{group_id}")
        return TargetGroup.from_dict(response)
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return None
        raise


def create_target_group(
    client, name: str, description: str = "", color: str = ""
) -> TargetGroup:
    """Creates a new target group."""
    body: Dict[str, Any] = {
        "name": name,
        "description": description,
    }
    if color:
        body["color"] = color

    response = client._request("POST", "/target-groups", body)
    return TargetGroup.from_dict(response)


def update_target_group(
    client, group_id: str, name: str, description: str = "", color: str = ""
) -> TargetGroup:
    """Updates an existing target group."""
    body: Dict[str, Any] = {
        "name": name,
        "description": description,
    }
    if color:
        body["color"] = color

    response = client._request("PUT", f"/target-groups/{group_id}", body)
    return TargetGroup.from_dict(response)


def delete_target_group(client, group_id: str) -> None:
    """Deletes a target group by ID."""
    client._request("DELETE", f"/target-groups/{group_id}")
