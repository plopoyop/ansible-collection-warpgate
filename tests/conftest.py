"""Shared fixtures for warpgate tests."""

import importlib
import os
import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap: make module_utils/warpgate_client importable both as
# `warpgate_client` (direct) AND as `ansible.module_utils.warpgate_client`
# (the path used inside library/*.py modules).
# ---------------------------------------------------------------------------

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_module_utils = os.path.join(_root, "plugins", "module_utils")
_library = os.path.join(_root, "plugins", "modules")

if _module_utils not in sys.path:
    sys.path.insert(0, _module_utils)
if _library not in sys.path:
    sys.path.insert(0, _library)

# Register warpgate_client package under the FQCN namespace used by collection modules:
# ``from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import …``
_pkg = importlib.import_module("warpgate_client")

_fqcn_base = (
    "ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client"
)
sys.modules[_fqcn_base] = _pkg

# Also register each submodule under the FQCN path
for _sub in (
    "client",
    "user",
    "role",
    "credential",
    "target",
    "target_group",
    "ticket",
    "helpers",
):
    _mod = importlib.import_module(f"warpgate_client.{_sub}")
    sys.modules[f"{_fqcn_base}.{_sub}"] = _mod

# Ensure the parent namespace packages exist in sys.modules
for _ns in (
    "ansible_collections",
    "ansible_collections.plopoyop",
    "ansible_collections.plopoyop.warpgate",
    "ansible_collections.plopoyop.warpgate.plugins",
    "ansible_collections.plopoyop.warpgate.plugins.module_utils",
):
    if _ns not in sys.modules:
        _ns_mod = types.ModuleType(_ns)
        _ns_mod.__path__ = []  # type: ignore[attr-defined]
        _ns_mod.__package__ = _ns
        sys.modules[_ns] = _ns_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock  # noqa: E402

from warpgate_client.client import WarpgateClient  # noqa: E402


@pytest.fixture
def mock_client():
    """A WarpgateClient whose network layer (_request) is mocked."""
    client = MagicMock(spec=WarpgateClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def mock_module():
    """A minimal AnsibleModule mock with check_mode=False."""
    module = MagicMock()
    module.check_mode = False
    module.debug = MagicMock()
    module.fail_json = MagicMock(side_effect=SystemExit)
    return module
