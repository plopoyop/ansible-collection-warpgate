"""
User management for the Warpgate API

This module provides functions to manage Warpgate users and their credential policies.
"""

import urllib.parse
from typing import Any

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
        http: list[str] | None = None,
        ssh: list[str] | None = None,
        mysql: list[str] | None = None,
        postgres: list[str] | None = None,
        kubernetes: list[str] | None = None,
    ):
        self.http = http
        self.ssh = ssh
        self.mysql = mysql
        self.postgres = postgres
        self.kubernetes = kubernetes

    def to_dict(self) -> dict[str, Any]:
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
        credential_policy: UserRequireCredentialsPolicy | None = None,
        rate_limit_bytes_per_second: int | None = None,
        ldap_server_id: str = "",
        allowed_ip_ranges: list[str] | None = None,
    ):
        self.id = id
        self.username = username
        self.description = description
        self.credential_policy = credential_policy
        self.rate_limit_bytes_per_second = rate_limit_bytes_per_second
        self.ldap_server_id = ldap_server_id
        self.allowed_ip_ranges = allowed_ip_ranges or []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Create a User from a dictionary"""
        policy = None
        if data.get("credential_policy"):
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
            rate_limit_bytes_per_second=data.get("rate_limit_bytes_per_second"),
            ldap_server_id=data.get("ldap_server_id", ""),
            allowed_ip_ranges=data.get("allowed_ip_ranges") or [],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the user for module output"""
        return {
            "id": self.id,
            "username": self.username,
            "description": self.description,
            "credential_policy": (
                self.credential_policy.to_dict() if self.credential_policy else {}
            ),
            "rate_limit_bytes_per_second": self.rate_limit_bytes_per_second,
            "ldap_server_id": self.ldap_server_id,
            "allowed_ip_ranges": list(self.allowed_ip_ranges),
        }


def get_users(client, search: str = "") -> list[User]:
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


def get_user(client, user_id: str) -> User | None:
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
    credential_policy: UserRequireCredentialsPolicy | None = None,
    rate_limit_bytes_per_second: int | None = None,
    allowed_ip_ranges: list[str] | None = None,
) -> User:
    """
    Updates an existing user's information including username, description,
    credential policy, bandwidth limit and IP allow-list.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        username: Updated username
        description: Updated description
        credential_policy: Optional credential policy
        rate_limit_bytes_per_second: Optional upstream bandwidth limit. Passing
            ``None`` leaves the field unset in the request body (no change).
        allowed_ip_ranges: Optional list of CIDR ranges allowed to authenticate
            as this user. Passing ``None`` leaves the field unset in the
            request body (no change); pass ``[]`` to explicitly clear it.

    Returns:
        Updated User object
    """
    body: dict[str, Any] = {"username": username, "description": description}
    if credential_policy:
        policy_dict = credential_policy.to_dict()
        if policy_dict:
            body["credential_policy"] = policy_dict
    if rate_limit_bytes_per_second is not None:
        body["rate_limit_bytes_per_second"] = rate_limit_bytes_per_second
    if allowed_ip_ranges is not None:
        body["allowed_ip_ranges"] = list(allowed_ip_ranges)

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
