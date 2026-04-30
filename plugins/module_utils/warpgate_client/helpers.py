"""
Shared helpers for Warpgate Ansible modules.

Provides common functionality used across multiple modules:
- Role resolution (name or UUID to role ID)
- Robust by-name lookup with search-then-list-all fallback
"""

from typing import Any, Callable, List, Optional

from .client import WarpgateAPIError
from .role import get_role, get_roles


def find_by_exact_name(
    list_fn: Callable[..., List[Any]],
    client: Any,
    name: str,
) -> Optional[Any]:
    """
    Robustly look up an entity by its exact name.

    Warpgate's ``?search=`` filter on collection endpoints (targets, users,
    roles, groups, …) can miss matches when the name contains characters
    that the API tokenizes (notably spaces). When the search-based pass
    returns no exact match, this helper falls back to listing the full
    collection and re-scanning client-side. Both attempts compare on the
    full ``name`` (or ``username`` for users) string for equality.

    Args:
        list_fn: collection getter accepting ``(client, search=…)``
            (e.g. ``get_targets``, ``get_users``, ``get_roles``).
        client: WarpgateClient instance.
        name: The exact name to match.

    Returns:
        The matching entity object, or ``None`` if no exact match exists.
    """

    def _scan(items: List[Any]) -> Optional[Any]:
        for item in items:
            if (
                getattr(item, "name", None) == name
                or getattr(item, "username", None) == name
            ):
                return item
        return None

    try:
        match = _scan(list_fn(client, search=name))
    except WarpgateAPIError:
        match = None

    if match is not None:
        return match

    # Fallback: full listing — the search filter sometimes misses entries
    # whose name contains spaces or other tokenized characters.
    try:
        return _scan(list_fn(client))
    except WarpgateAPIError:
        return None


def find_id_by_exact_name(
    list_fn: Callable[..., List[Any]],
    client: Any,
    name: str,
) -> Optional[str]:
    """Convenience wrapper around :func:`find_by_exact_name` returning the ID."""
    item = find_by_exact_name(list_fn, client, name)
    return getattr(item, "id", None) if item is not None else None


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
