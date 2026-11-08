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

    def test_unknown_violation_falls_back_to_the_masked_message(self):
        error = WarpgateAPIError(422, json.dumps(["SomeFutureRule"]))
        assert format_password_policy_error(error) is None

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

    def test_unexpected_entries_are_not_reported(self):
        for body in (
            ["TooShort", "Pa$$w0rdLong!"],
            ["Hunterpassword"],
            ["TooShort", ["x\\'y"]],
            [1],
        ):
            error = WarpgateAPIError(422, "masked", details=body)
            assert format_password_policy_error(error) is None

    def test_details_are_preferred_to_the_masked_message(self):
        error = WarpgateAPIError(422, '["********"]', details=["MissingDigit"])
        assert format_password_policy_error(error).endswith("missing a digit")
