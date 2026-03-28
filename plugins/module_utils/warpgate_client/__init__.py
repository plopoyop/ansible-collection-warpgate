"""
Warpgate API Client Package

This package provides a Python client for interacting with the Warpgate API.
The client is organized by entity type, similar to the Terraform provider structure.
"""

from .client import WarpgateAPIError, WarpgateClient, WarpgateClientError
from .helpers import resolve_role_ids

__all__ = [
    "WarpgateClient",
    "WarpgateClientError",
    "WarpgateAPIError",
    "resolve_role_ids",
]
