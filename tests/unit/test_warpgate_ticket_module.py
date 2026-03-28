"""Tests for warpgate_ticket module."""

from unittest.mock import patch, MagicMock


import warpgate_ticket  # noqa: E402
from warpgate_client.ticket import Ticket, TicketAndSecret


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
        username="admin",
        target_name="web-app",
        expiry="2099-12-31",
        number_of_uses=0,
        description="test ticket",
        state="present",
        insecure=False,
        timeout=30,
    )
    params.update(overrides)
    return params


def _run_module(params, check_mode=False):
    with patch("warpgate_ticket.AnsibleModule") as mock_cls:
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

        with patch("warpgate_ticket.WarpgateClient"):
            try:
                warpgate_ticket.main()
            except SystemExit:
                pass

        return result, mod


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestTicketCreate:
    def test_create_ticket(self):
        ticket = Ticket(
            id="tk1", username="admin", target="web-app", expiry="2099-12-31"
        )
        tas = TicketAndSecret(ticket=ticket, secret="s3cr3t")
        params = _base_params()
        with patch("warpgate_ticket.create_ticket", return_value=tas):
            result, mod = _run_module(params)
        assert result["changed"] is True
        assert result["id"] == "tk1"
        assert result["secret"] == "s3cr3t"
        assert result["diff"]["before"] == {}
        assert result["diff"]["after"]["username"] == "admin"
        assert result["diff"]["after"]["target"] == "web-app"

    def test_create_check_mode(self):
        params = _base_params()
        with patch("warpgate_ticket.create_ticket") as mock_create:
            result, mod = _run_module(params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert result["id"] == "new-ticket-id"
        assert result["diff"]["before"] == {}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestTicketDelete:
    def test_delete_ticket(self):
        params = _base_params(state="absent", id="tk1")
        with patch("warpgate_ticket.delete_ticket") as mock_del:
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["id"] == "tk1"
        assert result["diff"]["after"] == {}

    def test_delete_check_mode(self):
        params = _base_params(state="absent", id="tk1")
        with patch("warpgate_ticket.delete_ticket") as mock_del:
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert result["changed"] is True
