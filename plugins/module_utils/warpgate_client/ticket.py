"""
Ticket management for the Warpgate API

This module provides functions to manage Warpgate access tickets.
"""

from typing import Any


class Ticket:
    """Represents a Warpgate ticket"""

    def __init__(
        self,
        id: str = "",
        user_id: str = "",
        username: str = "",
        description: str = "",
        target_id: str = "",
        target: str = "",
        uses_left: int | None = None,
        expiry: str = "",
        created: str = "",
    ):
        self.id = id
        self.user_id = user_id
        self.username = username
        self.description = description
        self.target_id = target_id
        self.target = target
        self.uses_left = uses_left
        self.expiry = expiry
        self.created = created

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ticket":
        """Create a Ticket from a dictionary"""
        return cls(
            id=data.get("id", ""),
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            description=data.get("description", ""),
            target_id=data.get("target_id", ""),
            target=data.get("target", ""),
            uses_left=data.get("uses_left"),
            expiry=data.get("expiry", ""),
            created=data.get("created", ""),
        )


class TicketAndSecret:
    """Represents a ticket along with its secret"""

    def __init__(self, ticket: Ticket, secret: str):
        self.ticket = ticket
        self.secret = secret

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TicketAndSecret":
        """Create a TicketAndSecret from a dictionary"""
        ticket = Ticket.from_dict(data.get("ticket", {}))
        return cls(ticket=ticket, secret=data.get("secret", ""))


def create_ticket(
    client,
    username: str = "",
    target_name: str = "",
    user_id: str = "",
    target_id: str = "",
    expiry: str = "",
    number_of_uses: int | None = None,
    description: str = "",
) -> TicketAndSecret:
    """
    Creates a new ticket in Warpgate.

    The user can be identified either by ``username`` or by ``user_id`` (UUID).
    Same for the target: ``target_name`` or ``target_id``. Since v0.23, the API
    accepts any combination; omitted fields are not sent.

    Args:
        client: WarpgateClient instance
        username: Username for the ticket (alternative to user_id)
        target_name: Target name for the ticket (alternative to target_id)
        user_id: User UUID (alternative to username)
        target_id: Target UUID (alternative to target_name)
        expiry: Expiry date (ISO 8601 format)
        number_of_uses: Maximum number of uses. ``None`` or a non-positive
            value means unlimited and the field is not sent.
        description: Optional description

    Returns:
        TicketAndSecret object containing the ticket and its secret
    """
    body: dict[str, Any] = {}
    if username:
        body["username"] = username
    if target_name:
        body["target_name"] = target_name
    if user_id:
        body["user_id"] = user_id
    if target_id:
        body["target_id"] = target_id
    if expiry:
        body["expiry"] = expiry
    if number_of_uses is not None and number_of_uses > 0:
        body["number_of_uses"] = number_of_uses
    if description:
        body["description"] = description

    response = client._request("POST", "/tickets", body)
    return TicketAndSecret.from_dict(response)


def delete_ticket(client, ticket_id: str) -> None:
    """
    Removes a ticket from Warpgate by its ID.

    Args:
        client: WarpgateClient instance
        ticket_id: Ticket ID to delete
    """
    client._request("DELETE", f"/tickets/{ticket_id}")
