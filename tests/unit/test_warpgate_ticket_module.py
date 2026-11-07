"""Tests for warpgate_ticket module."""

from unittest.mock import MagicMock, patch

import warpgate_ticket
from warpgate_client.client import WarpgateAPIError
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
    def _patch_existing(self, *ids):
        return patch(
            "warpgate_ticket.get_tickets", return_value=[Ticket(id=i) for i in ids]
        )

    def test_delete_missing_is_noop(self):
        params = _base_params(state="absent", id="tk1")
        with (
            self._patch_existing("tk2"),
            patch("warpgate_ticket.delete_ticket") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_not_called()
        assert result["changed"] is False

    def test_delete_ticket(self):
        params = _base_params(state="absent", id="tk1")
        with (
            self._patch_existing("tk1"),
            patch("warpgate_ticket.delete_ticket") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True
        assert result["diff"]["before"]["id"] == "tk1"
        assert result["diff"]["after"] == {}

    def test_delete_check_mode(self):
        params = _base_params(state="absent", id="tk1")
        with (
            self._patch_existing("tk1"),
            patch("warpgate_ticket.delete_ticket") as mock_del,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert result["changed"] is True


class TestTicketDeleteListingFallback:
    def test_listing_error_falls_back_to_delete(self):
        params = _base_params(state="absent", id="tk1")
        with (
            patch(
                "warpgate_ticket.get_tickets",
                side_effect=WarpgateAPIError(500, "inconsistent"),
            ),
            patch("warpgate_ticket.delete_ticket") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()
        assert result["changed"] is True

    def test_listing_error_and_missing_ticket_is_noop(self):
        params = _base_params(state="absent", id="tk1")
        with (
            patch(
                "warpgate_ticket.get_tickets",
                side_effect=WarpgateAPIError(500, "inconsistent"),
            ),
            patch(
                "warpgate_ticket.delete_ticket",
                side_effect=WarpgateAPIError(404, "not found"),
            ),
        ):
            result, mod = _run_module(params)
        assert result["changed"] is False

    def test_id_match_ignores_case(self):
        params = _base_params(state="absent", id="TK1")
        with (
            patch("warpgate_ticket.get_tickets", return_value=[Ticket(id="tk1")]),
            patch("warpgate_ticket.delete_ticket") as mock_del,
        ):
            result, mod = _run_module(params)
        mock_del.assert_called_once()


class TestTicketDeleteCheckModeListingError:
    def test_listing_error_fails_in_check_mode(self):
        params = _base_params(state="absent", id="tk1")
        with (
            patch(
                "warpgate_ticket.get_tickets",
                side_effect=WarpgateAPIError(500, "inconsistent"),
            ),
            patch("warpgate_ticket.delete_ticket") as mock_del,
        ):
            result, mod = _run_module(params, check_mode=True)
        mock_del.assert_not_called()
        assert "inconsistent" in result["msg"]
