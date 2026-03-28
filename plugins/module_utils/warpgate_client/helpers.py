"""
Shared helpers for Warpgate Ansible modules.

Provides common functionality used across multiple modules:
- Role resolution (name or UUID to role ID)
"""

from typing import List

from .client import WarpgateAPIError
from .role import get_role, get_roles


def resolve_role_ids(client, role_specs: List[str]) -> List[str]:
    """
    Resolves role specifications (IDs or names) to actual role IDs.

    Args:
        client: WarpgateClient instance
        role_specs: List of role identifiers (UUIDs or names)

    Returns:
        List of resolved role IDs

    Raises:
        ValueError: If a role spec cannot be resolved
    """
    if not role_specs:
        return []

    resolved_ids = []
    all_roles = None

    for role_spec in role_specs:
        # Try to use as ID first (UUID format: 36 chars with 4 dashes)
        if len(role_spec) == 36 and role_spec.count("-") == 4:
            try:
                role = get_role(client, role_spec)
                if role:
                    resolved_ids.append(role.id)
                    continue
            except WarpgateAPIError:
                pass

        # Try to find by name
        if all_roles is None:
            all_roles = get_roles(client)

        found = False
        for role in all_roles:
            if role.name == role_spec:
                resolved_ids.append(role.id)
                found = True
                break

        if not found:
            raise ValueError(
                f"Role '{role_spec}' not found (neither as ID nor as name)"
            )

    return resolved_ids
