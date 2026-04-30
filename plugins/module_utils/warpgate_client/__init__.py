"""
Warpgate API Client Package

This package provides a Python client for interacting with the Warpgate API.
The client is organized by entity type, similar to the Terraform provider structure.
"""

from .client import WarpgateAPIError, WarpgateClient, WarpgateClientError
from .helpers import find_by_exact_name, find_id_by_exact_name, resolve_role_ids

__all__ = [
    "WarpgateClient",
    "WarpgateClientError",
    "WarpgateAPIError",
    "find_by_exact_name",
    "find_id_by_exact_name",
    "resolve_role_ids",
]
