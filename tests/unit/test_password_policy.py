"""Tests for the password-policy violation formatting helper (Warpgate >= 0.25)."""

import json

from warpgate_client.client import WarpgateAPIError
from warpgate_client.credential import format_password_policy_error


class TestFormatPasswordPolicyError:
    def test_formats_known_violations(self):
        error = WarpgateAPIError(422, json.dumps(["TooShort", "MissingDigit"]))
        msg = format_password_policy_error(error)
        assert msg is not None
        assert "password is too short" in msg
        assert "missing a digit" in msg

    def test_unknown_violation_kept_verbatim(self):
        error = WarpgateAPIError(422, json.dumps(["SomeFutureRule"]))
        msg = format_password_policy_error(error)
        assert "SomeFutureRule" in msg

    def test_non_422_returns_none(self):
        error = WarpgateAPIError(404, json.dumps(["TooShort"]))
        assert format_password_policy_error(error) is None

    def test_non_json_body_returns_none(self):
        error = WarpgateAPIError(422, "internal error")
        assert format_password_policy_error(error) is None

    def test_non_list_body_returns_none(self):
        error = WarpgateAPIError(422, json.dumps({"error": "nope"}))
        assert format_password_policy_error(error) is None

    def test_empty_list_returns_none(self):
        error = WarpgateAPIError(422, json.dumps([]))
        assert format_password_policy_error(error) is None
