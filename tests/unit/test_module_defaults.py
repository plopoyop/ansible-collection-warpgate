"""Tests for the collection-wide module_defaults action group."""

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

COLLECTION_ROOT = Path(__file__).parents[2]
ACTION_GROUP = "warpgate"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _WarpgateStubHandler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self.__class__.requests.append(
            {
                "path": self.path,
                "token": self.headers.get("X-Warpgate-Token"),
            }
        )
        response = json.dumps(
            [
                {
                    "id": "group-id",
                    "name": "existing-group",
                    "description": "",
                    "color": "",
                }
            ]
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        """Silence HTTP server logs in the pytest output."""


@pytest.fixture
def warpgate_stub():
    _WarpgateStubHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _WarpgateStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _run_playbook(tmp_path, server_port):
    ansible_playbook = shutil.which("ansible-playbook")
    if ansible_playbook is None:
        pytest.skip("ansible-playbook is not installed")

    collections_root = tmp_path / "collections"
    collection_path = collections_root / "ansible_collections" / "plopoyop" / "warpgate"
    collection_path.parent.mkdir(parents=True)
    shutil.copytree(
        COLLECTION_ROOT,
        collection_path,
        ignore=shutil.ignore_patterns(
            ".ansible",
            ".devbox",
            ".git",
            ".pytest_cache",
            ".ruff_cache",
            "__pycache__",
        ),
    )

    playbook = tmp_path / "module_defaults.yml"
    playbook.write_text(
        f"""\
---
- name: Verify collection module defaults
  hosts: localhost
  gather_facts: false
  module_defaults:
    group/plopoyop.warpgate.{ACTION_GROUP}:
      host: http://127.0.0.1:{server_port}/@warpgate/admin/api/
      token: default-token
      timeout: 2

  tasks:
    - name: Use credentials from module defaults
      plopoyop.warpgate.warpgate_group:
        name: existing-group

    - name: Override one module default at task level
      plopoyop.warpgate.warpgate_group:
        name: existing-group
        token: task-token
"""
    )

    env = os.environ.copy()
    env.update(
        {
            "ANSIBLE_COLLECTIONS_PATH": str(collections_root),
            "ANSIBLE_LOCAL_TEMP": str(tmp_path / "ansible-local"),
            "ANSIBLE_REMOTE_TEMP": str(tmp_path / "ansible-remote"),
        }
    )
    return subprocess.run(
        [
            ansible_playbook,
            "--inventory",
            "localhost,",
            "--connection",
            "local",
            str(playbook),
        ],
        capture_output=True,
        env=env,
        text=True,
        timeout=30,
        check=False,
    )


# ---------------------------------------------------------------------------
# Module defaults
# ---------------------------------------------------------------------------


class TestModuleDefaults:
    def test_action_group_contains_every_module(self):
        runtime = yaml.safe_load((COLLECTION_ROOT / "meta" / "runtime.yml").read_text())
        action_group_modules = set(runtime["action_groups"][ACTION_GROUP])
        collection_modules = {
            path.stem
            for path in (COLLECTION_ROOT / "plugins" / "modules").glob("*.py")
            if path.name != "__init__.py"
        }

        assert action_group_modules == collection_modules

    def test_defaults_are_applied_and_task_args_take_precedence(
        self, tmp_path, warpgate_stub
    ):
        result = _run_playbook(tmp_path, warpgate_stub.server_port)

        assert result.returncode == 0, result.stdout + result.stderr
        assert _WarpgateStubHandler.requests == [
            {
                "path": "/@warpgate/admin/api/target-groups?search=existing-group",
                "token": "default-token",
            },
            {
                "path": "/@warpgate/admin/api/target-groups?search=existing-group",
                "token": "task-token",
            },
        ]
