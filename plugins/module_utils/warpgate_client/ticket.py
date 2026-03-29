"""
Ticket management for the Warpgate API

This module provides functions to manage Warpgate access tickets.
"""

from typing import Any, Dict


class Ticket:
    """Represents a Warpgate ticket"""

    def __init__(
        self,
        id: str = "",
        username: str = "",
        description: str = "",
        target: str = "",
        uses_left: str = "",
        expiry: str = "",
        created: str = "",
    ):
        self.id = id
        self.username = username
        self.description = description
        self.target = target
        self.uses_left = uses_left
        self.expiry = expiry
        self.created = created

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ticket":
        """Create a Ticket from a dictionary"""
        return cls(
            id=data.get("id", ""),
            username=data.get("username", ""),
            description=data.get("description", ""),
            target=data.get("target", ""),
            uses_left=data.get("uses_left", ""),
            expiry=data.get("expiry", ""),
            created=data.get("created", ""),
        )


class TicketAndSecret:
    """Represents a ticket along with its secret"""

    def __init__(self, ticket: Ticket, secret: str):
        self.ticket = ticket
        self.secret = secret

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TicketAndSecret":
        """Create a TicketAndSecret from a dictionary"""
        ticket = Ticket.from_dict(data.get("ticket", {}))
        return cls(ticket=ticket, secret=data.get("secret", ""))


def create_ticket(
    client,
    username: str = "",
    target_name: str = "",
    expiry: str = "",
    number_of_uses: int = 0,
    description: str = "",
) -> TicketAndSecret:
    """
    Creates a new ticket in Warpgate with the provided parameters.

    Args:
        client: WarpgateClient instance
        username: Username for the ticket
        target_name: Target name for the ticket
        expiry: Expiry date (ISO 8601 format)
        number_of_uses: Number of allowed uses
        description: Optional description

    Returns:
        TicketAndSecret object containing the ticket and its secret
    """
    body = {
        "username": username or "",
        "target_name": target_name or "",
    }
    if expiry:
        body["expiry"] = expiry
    if number_of_uses is not None:
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
