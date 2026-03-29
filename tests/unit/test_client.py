"""Tests for WarpgateClient initialisation and URL helpers."""

from unittest.mock import MagicMock, patch

import pytest
from warpgate_client.client import WarpgateClient, _user_api_base

# ---------------------------------------------------------------------------
# _user_api_base
# ---------------------------------------------------------------------------


class TestUserApiBase:
    def test_standard_admin_url(self):
        assert (
            _user_api_base("https://host:8888/@warpgate/admin/api")
            == "https://host:8888/@warpgate/api/"
        )

    def test_admin_url_with_trailing_slash(self):
        assert (
            _user_api_base("https://host:8888/@warpgate/admin/api/")
            == "https://host:8888/@warpgate/api/"
        )

    def test_url_without_admin_suffix(self):
        result = _user_api_base("https://host:8888/custom")
        assert result == "https://host:8888/custom/@warpgate/api/"


# ---------------------------------------------------------------------------
# WarpgateClient.__init__ — auth validation
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_token_only(self):
        c = WarpgateClient("https://host", token="tok")
        assert c._token == "tok"
        assert c._username is None

    def test_username_password_only(self):
        c = WarpgateClient("https://host", username="u", password="p")
        assert c._token is None
        assert c._username == "u"
        assert c._password == "p"

    def test_token_and_username_accepted(self):
        """Both can be provided — token takes priority at request time."""
        c = WarpgateClient("https://host", token="tok", username="u", password="p")
        assert c._token == "tok"
        assert c._username == "u"

    def test_no_auth_raises(self):
        with pytest.raises(ValueError, match="Provide either token"):
            WarpgateClient("https://host")

    def test_username_without_password_raises(self):
        with pytest.raises(ValueError, match="Provide either token"):
            WarpgateClient("https://host", username="u")

    def test_password_without_username_raises(self):
        with pytest.raises(ValueError, match="Provide either token"):
            WarpgateClient("https://host", password="p")

    def test_empty_host_raises(self):
        with pytest.raises(ValueError, match="host cannot be empty"):
            WarpgateClient("", token="tok")

    def test_auto_https_prefix(self):
        c = WarpgateClient("myhost.local", token="tok")
        assert c.base_url.startswith("https://")

    def test_trailing_slash_stripped(self):
        c = WarpgateClient("https://host/api/", token="tok")
        assert not c.base_url.endswith("/")

    def test_insecure_creates_ssl_context(self):
        c = WarpgateClient("https://host", token="tok", insecure=True)
        assert c.ssl_context is not None
        assert c.ssl_context.check_hostname is False

    def test_secure_no_ssl_context(self):
        c = WarpgateClient("https://host", token="tok", insecure=False)
        assert c.ssl_context is None


# ---------------------------------------------------------------------------
# WarpgateClient._request — auth header selection
# ---------------------------------------------------------------------------


class TestClientRequest:
    @patch("warpgate_client.client.urlopen")
    def test_token_header_used(self, mock_urlopen):
        resp = MagicMock()
        resp.getcode.return_value = 200
        resp.read.return_value = b'{"ok": true}'
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        c = WarpgateClient("https://host", token="my-token")
        c._request("GET", "/test")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("X-warpgate-token") == "my-token"

    @patch("warpgate_client.client.urlopen")
    def test_session_cookie_used_after_login(self, mock_urlopen):
        c = WarpgateClient("https://host", token=None, username="u", password="p")
        c._session_cookie = "warpgate-session=abc"

        resp = MagicMock()
        resp.getcode.return_value = 200
        resp.read.return_value = b'{"ok": true}'
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        c._request("GET", "/test")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Cookie") == "warpgate-session=abc"

    def test_request_triggers_login_when_no_auth(self):
        c = WarpgateClient("https://host", username="u", password="p")
        assert c._token is None
        assert c._session_cookie is None
        # _login should be called on first _request; we just verify it's attempted
        with patch.object(c, "_login", side_effect=Exception("login called")):
            with pytest.raises(Exception, match="login called"):
                c._request("GET", "/test")
