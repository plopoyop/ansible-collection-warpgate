"""Tests for warpgate_group module."""

from unittest.mock import patch, MagicMock


import warpgate_group  # noqa: E402
from warpgate_client.target_group import TargetGroup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_params(**overrides):
    params = dict(
        host="https://host/@warpgate/admin/api/",
        token="tok",
        api_username=None,
        api_password=None,
        id=None,
        name="production",
        description="Prod servers",
        color="Danger",
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    with patch("warpgate_group.AnsibleModule") as mock_cls:
        mod = MagicMock()
        mod.params = params
        mod.check_mode = check_mode
        mod.debug = MagicMock()
        mock_cls.return_value = mod

        result = {}

        def capture_exit(**kwargs):
            result.update(kwargs)
            raise SystemExit(0)

        def capture_fail(**kwargs):
            result.update(kwargs)
            raise SystemExit(1)

        mod.exit_json = MagicMock(side_effect=capture_exit)
        mod.fail_json = MagicMock(side_effect=capture_fail)

        with patch("warpgate_group.WarpgateClient"):
            try:
                warpgate_group.main()
            except SystemExit:
                pass

        return result, mod


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestGroupCreate:
    def test_create_new_group(self):
        created = TargetGroup(
            id="g1", name="production", description="Prod servers", color="Danger"
        )
        params = _base_params()
        with (
            patch("warpgate_group.get_target_groups", return_value=[]),
            patch("warpgate_group.create_target_group", return_value=created),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["id"] == "g1"
        assert result["diff"]["before"] == {}
        assert result["diff"]["after"]["name"] == "production"
        assert result["diff"]["after"]["color"] == "Danger"

    def test_create_check_mode(self):
        params = _base_params()
        with (
            patch("warpgate_group.get_target_groups", return_value=[]),
            patch("warpgate_group.create_target_group") as mock_create,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert result["id"] == "new-target-group-id"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestGroupUpdate:
    def test_update_existing_group(self):
        existing = TargetGroup(
            id="g1", name="production", description="Old", color="Info"
        )
        updated = TargetGroup(
            id="g1", name="production", description="Prod servers", color="Danger"
        )
        params = _base_params()
        with (
            patch("warpgate_group.get_target_groups", return_value=[existing]),
            patch("warpgate_group.update_target_group", return_value=updated),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["diff"]["before"]["description"] == "Old"
        assert result["diff"]["before"]["color"] == "Info"
        assert result["diff"]["after"]["description"] == "Prod servers"
        assert result["diff"]["after"]["color"] == "Danger"

    def test_no_change_when_identical(self):
        existing = TargetGroup(
            id="g1", name="production", description="Prod servers", color="Danger"
        )
        params = _base_params()
        with patch("warpgate_group.get_target_groups", return_value=[existing]):
            result, mod = _run_module(params)
        assert result["changed"] is False
        assert "diff" not in result

    def test_update_check_mode(self):
        existing = TargetGroup(
            id="g1", name="production", description="Old", color="Info"
        )
        params = _base_params()
        with (
            patch("warpgate_group.get_target_groups", return_value=[existing]),
            patch("warpgate_group.update_target_group") as mock_update,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestGroupDelete:
    def test_delete_existing_group(self):
        existing = TargetGroup(
            id="g1", name="production", description="Prod servers", color="Danger"
        )
        params = _base_params(state="absent")
        with (
            patch("warpgate_group.get_target_groups", return_value=[existing]),
            patch("warpgate_group.delete_target_group"),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["diff"]["before"]["name"] == "production"
        assert result["diff"]["after"] == {}

    def test_delete_nonexistent_is_noop(self):
        params = _base_params(state="absent")
        with patch("warpgate_group.get_target_groups", return_value=[]):
            result, mod = _run_module(params)
        assert result["changed"] is False

    def test_delete_check_mode(self):
        existing = TargetGroup(
            id="g1", name="production", description="Prod servers", color="Danger"
        )
        params = _base_params(state="absent")
        with (
            patch("warpgate_group.get_target_groups", return_value=[existing]),
            patch("warpgate_group.delete_target_group") as mock_del,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert result["changed"] is True
