"""
User management for the Warpgate API

This module provides functions to manage Warpgate users and their credential policies.
"""

import urllib.parse
from typing import Any, Dict, List, Optional

from .client import WarpgateAPIError

# Credential kind constants
CREDENTIAL_KIND_PASSWORD = "Password"
CREDENTIAL_KIND_PUBLIC_KEY = "PublicKey"
CREDENTIAL_KIND_TOTP = "Totp"
CREDENTIAL_KIND_SSO = "Sso"
CREDENTIAL_KIND_WEB_USER_APPROVAL = "WebUserApproval"
CREDENTIAL_KIND_CERTIFICATE = "Certificate"


class UserRequireCredentialsPolicy:
    """Defines the credential policy for a user"""

    def __init__(
        self,
        http: Optional[List[str]] = None,
        ssh: Optional[List[str]] = None,
        mysql: Optional[List[str]] = None,
        postgres: Optional[List[str]] = None,
        kubernetes: Optional[List[str]] = None,
    ):
        self.http = http
        self.ssh = ssh
        self.mysql = mysql
        self.postgres = postgres
        self.kubernetes = kubernetes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization. Returns empty dict if no policies set."""
        result = {}
        if self.http:
            result["http"] = self.http
        if self.ssh:
            result["ssh"] = self.ssh
        if self.mysql:
            result["mysql"] = self.mysql
        if self.postgres:
            result["postgres"] = self.postgres
        if self.kubernetes:
            result["kubernetes"] = self.kubernetes
        return result


class User:
    """Represents a Warpgate user"""

    def __init__(
        self,
        id: str,
        username: str,
        description: str = "",
        credential_policy: Optional[UserRequireCredentialsPolicy] = None,
    ):
        self.id = id
        self.username = username
        self.description = description
        self.credential_policy = credential_policy

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create a User from a dictionary"""
        policy = None
        if "credential_policy" in data and data["credential_policy"]:
            cp = data["credential_policy"]
            policy = UserRequireCredentialsPolicy(
                http=cp.get("http"),
                ssh=cp.get("ssh"),
                mysql=cp.get("mysql"),
                postgres=cp.get("postgres"),
                kubernetes=cp.get("kubernetes"),
            )
        return cls(
            id=data["id"],
            username=data["username"],
            description=data.get("description", ""),
            credential_policy=policy,
        )


def get_users(client, search: str = "") -> List[User]:
    """
    Retrieves all users from the Warpgate API, optionally filtered by search term.

    Args:
        client: WarpgateClient instance
        search: Optional search term to filter users

    Returns:
        List of User objects
    """
    path = "/users"
    if search:
        path += f"?search={urllib.parse.quote(search)}"

    response = client._request("GET", path)
    return [User.from_dict(user) for user in response]


def get_user(client, user_id: str) -> Optional[User]:
    """
    Retrieves a specific user by ID from the Warpgate API.

    Args:
        client: WarpgateClient instance
        user_id: User ID

    Returns:
        User object if found, None otherwise
    """
    try:
        response = client._request("GET", f"/users/{user_id}")
        return User.from_dict(response)
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return None
        raise


def create_user(client, username: str, description: str = "") -> User:
    """
    Creates a new user in Warpgate with the provided username and description.

    Args:
        client: WarpgateClient instance
        username: Username for the new user
        description: Optional description

    Returns:
        Created User object
    """
    body = {"username": username, "description": description}
    response = client._request("POST", "/users", body)
    return User.from_dict(response)


def update_user(
    client,
    user_id: str,
    username: str,
    description: str = "",
    credential_policy: Optional[UserRequireCredentialsPolicy] = None,
) -> User:
    """
    Updates an existing user's information including username, description, and credential policy.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        username: Updated username
        description: Updated description
        credential_policy: Optional credential policy

    Returns:
        Updated User object
    """
    body = {"username": username, "description": description}
    if credential_policy:
        policy_dict = credential_policy.to_dict()
        if policy_dict:
            body["credential_policy"] = policy_dict

    response = client._request("PUT", f"/users/{user_id}", body)
    return User.from_dict(response)


def delete_user(client, user_id: str) -> None:
    """
    Removes a user from Warpgate by their ID.

    Args:
        client: WarpgateClient instance
        user_id: User ID to delete
    """
    client._request("DELETE", f"/users/{user_id}")
