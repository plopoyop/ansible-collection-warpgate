"""Tests for WarpgateClient initialisation and URL helpers."""

import json
import socket
import threading
from http.client import IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, Request

import pytest
from warpgate_client.credential import format_password_policy_error
from warpgate_client.client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    _error_body,
    _secret_values,
    _SameOriginRedirectHandler,
    _short,
    _user_api_base,
    path_segment,
)

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
    @patch("warpgate_client.client.build_opener")
    def test_token_header_used(self, mock_build):
        mock_urlopen = mock_build.return_value.open
        resp = MagicMock()
        resp.getcode.return_value = 200
        resp.read.side_effect = [b'{"ok": true}', b""]
        resp.headers = {}
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        c = WarpgateClient("https://host", token="my-token")
        c._request("GET", "/test")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("X-warpgate-token") == "my-token"

    @patch("warpgate_client.client.build_opener")
    def test_session_cookie_used_after_login(self, mock_build):
        mock_urlopen = mock_build.return_value.open
        c = WarpgateClient("https://host", token=None, username="u", password="p")
        c._session_cookie = "warpgate-session=abc"

        resp = MagicMock()
        resp.getcode.return_value = 200
        resp.read.side_effect = [b'{"ok": true}', b""]
        resp.headers = {}
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


# ---------------------------------------------------------------------------
# WarpgateClient.logout
# ---------------------------------------------------------------------------


class TestClientLogout:
    @patch("warpgate_client.client.build_opener")
    def test_logout_posts_to_user_api_with_cookie(self, mock_build):
        mock_urlopen = mock_build.return_value.open
        resp = MagicMock()
        resp.getcode.return_value = 201
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        c = WarpgateClient(
            "https://host:8888/@warpgate/admin/api", username="u", password="p"
        )
        c._session_cookie = "warpgate-session=abc"

        c.logout()

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://host:8888/@warpgate/api/auth/logout"
        assert req.get_method() == "POST"
        assert req.get_header("Cookie") == "warpgate-session=abc"
        assert c._session_cookie is None

    @patch("warpgate_client.client.build_opener")
    def test_logout_noop_without_session(self, mock_build):
        mock_urlopen = mock_build.return_value.open
        c = WarpgateClient("https://host", token="tok")

        c.logout()

        mock_urlopen.assert_not_called()

    @patch("warpgate_client.client.build_opener")
    def test_logout_swallows_errors(self, mock_build):
        mock_urlopen = mock_build.return_value.open
        mock_urlopen.side_effect = URLError("boom")
        c = WarpgateClient("https://host", username="u", password="p")
        c._session_cookie = "warpgate-session=abc"

        c.logout()

        assert c._session_cookie is None


# ---------------------------------------------------------------------------
# Transport hardening
# ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    routes = {}
    seen = []

    def do_POST(self):
        self.do_GET()

    def do_GET(self):
        self.__class__.seen.append(
            (self.server.server_port, self.path, self.headers.get("X-Warpgate-Token"))
        )
        status, headers, body = self.routes.get(self.path, (404, {}, b"{}"))
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def servers():
    started = []

    def start(routes):
        handler = type("H", (_Handler,), {"routes": routes, "seen": _Handler.seen})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        ).start()
        started.append(server)
        return server

    _Handler.seen.clear()
    yield start
    for server in started:
        server.shutdown()
        server.server_close()


class TestRedirects:
    def test_cross_origin_redirect_is_refused(self, servers):
        other = servers({"/steal": (200, {}, b"{}")})
        api = servers(
            {
                "/api/x": (
                    302,
                    {"Location": f"http://127.0.0.1:{other.server_port}/steal"},
                    b"",
                )
            }
        )
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="secret")
        with pytest.raises(WarpgateClientError, match="Refusing to follow a redirect"):
            c._request("GET", "/x")
        assert all(port != other.server_port for port, _path, _token in _Handler.seen)

    def test_same_origin_redirect_is_followed(self, servers):
        api = servers({"/api/new": (200, {}, b'{"ok": true}')})
        api.RequestHandlerClass.routes["/api/old"] = (
            301,
            {"Location": "/api/new"},
            b"",
        )
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="secret")
        assert c._request("GET", "/old") == {"ok": True}
        assert ("/api/new", "secret") in [(p, t) for _port, p, t in _Handler.seen]


class TestErrorsAndLimits:
    def test_error_body_is_truncated(self, servers):
        api = servers({"/api/x": (500, {}, b"x" * 5000)})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x")
        assert exc.value.message.endswith("(truncated)")
        assert len(exc.value.message) < 1100

    def test_oversized_response_is_refused(self, servers, monkeypatch):
        monkeypatch.setattr("warpgate_client.client.MAX_RESPONSE_BYTES", 10)
        api = servers({"/api/x": (200, {}, b'{"data": "0123456789"}')})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateClientError, match="larger than"):
            c._request("GET", "/x")

    def test_plain_http_warns(self):
        with patch("warpgate_client.client.warn") as mock_warn:
            WarpgateClient("http://host", token="t")
            WarpgateClient("https://host", token="t")
        mock_warn.assert_called_once()


class TestPathSegment:
    def test_id_is_encoded(self):
        assert path_segment("../users/x?y=1") == "..%2Fusers%2Fx%3Fy%3D1"

    def test_uuid_unchanged(self):
        uuid = "9c2a5f31-4d6e-4b7a-9c1d-2e3f4a5b6c7d"
        assert path_segment(uuid) == uuid

    @pytest.mark.parametrize("value", ["", ".", ".."])
    def test_dot_segments_rejected(self, value):
        with pytest.raises(ValueError):
            path_segment(value)


class TestTransportWiring:
    def test_opener_uses_tls_context_and_redirect_check(self):
        with patch("warpgate_client.client.build_opener") as mock_build:
            c = WarpgateClient("https://host", token="t", insecure=True)
        handlers = mock_build.call_args[0]
        https = next(h for h in handlers if isinstance(h, HTTPSHandler))
        assert https._context is c.ssl_context
        assert any(isinstance(h, _SameOriginRedirectHandler) for h in handlers)


class TestRedirectOrigins:
    @pytest.mark.parametrize(
        "old, new, allowed",
        [
            ("https://h/api/x", "http://h/api/x", False),
            ("https://h:8888/x", "http://h:8888/x", False),
            ("https://h/api/x", "https://h:8443/api/x", False),
            ("https://h/api/x", "https://evil@h/api/x", False),
            ("https://h/api/x", "https://:pw@h/api/x", False),
            ("https://h/api/x", "https://h:99999/api/x", False),
            ("https://h/api/x", "https://h:abc/api/x", False),
            ("https://h/api/x", "https://H:443/api/y", True),
            ("https://h/api/x", "https://h/api/y", True),
        ],
    )
    def test_origin_check(self, old, new, allowed):
        handler = _SameOriginRedirectHandler()
        req = Request(old)
        fp = MagicMock()
        if allowed:
            assert handler.redirect_request(req, fp, 302, "Found", {}, new) is not None
        else:
            with pytest.raises(WarpgateClientError):
                handler.redirect_request(req, fp, 302, "Found", {}, new)
            fp.close.assert_called_once()

    def test_refused_redirect_message_is_bounded(self):
        handler = _SameOriginRedirectHandler()
        target = "https://" + "a" * 3000 + ".example/x"
        with pytest.raises(WarpgateClientError) as exc:
            handler.redirect_request(
                Request("https://h/x"), MagicMock(), 302, "", {}, target
            )
        assert len(str(exc.value)) < 1100

    def test_login_redirect_to_other_origin_is_refused(self, servers):
        other = servers({})
        api = servers(
            {
                "/@warpgate/api/auth/login": (
                    302,
                    {"Location": f"http://127.0.0.1:{other.server_port}/steal"},
                    b"",
                )
            }
        )
        c = WarpgateClient(
            f"http://127.0.0.1:{api.server_port}/@warpgate/admin/api",
            username="u",
            password="secret",
        )
        with pytest.raises(WarpgateClientError, match="Refusing to follow a redirect"):
            c._request("GET", "/users")
        assert all(port != other.server_port for port, _path, _token in _Handler.seen)


class TestErrorBodyBytes:
    def test_multibyte_body_is_marked_truncated(self, servers):
        api = servers({"/api/x": (500, {}, "é".encode() * 1200)})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x")
        assert exc.value.message.endswith("(truncated)")

    def test_none_path_segment_rejected(self):
        with pytest.raises(ValueError):
            path_segment(None)


class TestLogoutAndBoundaries:
    def test_logout_swallows_a_refused_redirect(self, servers):
        api = servers(
            {
                "/@warpgate/api/auth/logout": (
                    302,
                    {"Location": "http://127.0.0.1:99999/x"},
                    b"",
                )
            }
        )
        c = WarpgateClient(
            f"http://127.0.0.1:{api.server_port}/@warpgate/admin/api",
            username="u",
            password="p",
        )
        c._session_cookie = "warpgate-session=abc"
        c.logout()
        assert c._session_cookie is None

    def test_multibyte_char_cut_at_the_limit(self, servers):
        api = servers({"/api/x": (500, {}, b"a" * 999 + "é".encode() * 10)})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x")
        assert exc.value.message.endswith("(truncated)")
        assert exc.value.message.startswith("a" * 999)


class TestBoundedRead:
    def test_large_body_read_in_chunks(self, servers, monkeypatch):
        monkeypatch.setattr("warpgate_client.client.READ_CHUNK_BYTES", 4)
        api = servers({"/api/x": (200, {}, b'{"data": "0123456789"}')})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        assert c._request("GET", "/x") == {"data": "0123456789"}

    def test_limit_applies_across_chunks(self, servers, monkeypatch):
        monkeypatch.setattr("warpgate_client.client.READ_CHUNK_BYTES", 4)
        monkeypatch.setattr("warpgate_client.client.MAX_RESPONSE_BYTES", 10)
        api = servers({"/api/x": (200, {}, b'{"data": "0123456789"}')})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateClientError, match="larger than"):
            c._request("GET", "/x")


class _RawServer:
    """Serves one raw HTTP response, to send what BaseHTTPRequestHandler won't."""

    def __init__(self, payload):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.payload = payload
        self.stop = threading.Event()
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        conn, _addr = self.sock.accept()
        with conn:
            request = b""
            while b"\r\n\r\n" not in request:
                data = conn.recv(65536)
                if not data:
                    break
                request += data
            if self.payload is None:
                self.stop.wait(10)
            else:
                conn.sendall(self.payload)

    def close(self):
        self.stop.set()
        self.sock.close()


class TestResponseEdgeCases:
    def test_no_content_with_content_length_is_accepted(self):
        raw = _RawServer(
            b"HTTP/1.1 204 No Content\r\nContent-Length: 5\r\nConnection: close\r\n\r\n"
        )
        try:
            c = WarpgateClient(f"http://127.0.0.1:{raw.port}/api", token="t")
            assert c._request("DELETE", "/x") == {}
        finally:
            raw.close()

    def test_truncated_chunked_body_is_a_client_error(self):
        raw = _RawServer(
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
            b'a\r\n[{"a": 1'
        )
        try:
            c = WarpgateClient(f"http://127.0.0.1:{raw.port}/api", token="t")
            with pytest.raises(WarpgateClientError):
                c._request("GET", "/x")
        finally:
            raw.close()

    def test_truncated_body_is_refused(self):
        raw = _RawServer(
            b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\nConnection: close\r\n\r\n"
            b'[{"a": 1}]'
        )
        try:
            c = WarpgateClient(f"http://127.0.0.1:{raw.port}/api", token="t")
            with pytest.raises(WarpgateClientError, match="Incomplete response"):
                c._request("GET", "/x")
        finally:
            raw.close()

    def test_logout_swallows_protocol_errors(self):
        raw = _RawServer(b"NOT-HTTP garbage\r\n\r\n")
        try:
            c = WarpgateClient(
                f"http://127.0.0.1:{raw.port}/@warpgate/admin/api",
                username="u",
                password="p",
            )
            c._session_cookie = "warpgate-session=abc"
            c.logout()
            assert c._session_cookie is None
        finally:
            raw.close()

    def test_responses_are_read_in_bounded_chunks(self, monkeypatch):
        sizes = []
        resp = MagicMock()
        resp.getcode.return_value = 200
        resp.headers = {}
        resp.read.side_effect = lambda n=-1: (
            sizes.append(n) or (b'{"ok": true}' if len(sizes) == 1 else b"")
        )
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        with patch("warpgate_client.client.build_opener") as mock_build:
            mock_build.return_value.open.return_value = resp
            WarpgateClient("https://host", token="t")._request("GET", "/x")
        assert sizes and all(0 < n <= 1024 * 1024 for n in sizes)

    def test_login_error_does_not_echo_the_body(self, servers):
        api = servers(
            {"/@warpgate/api/auth/login": (401, {}, b'{"password": "S3cr\\"et"}')}
        )
        c = WarpgateClient(
            f"http://127.0.0.1:{api.server_port}/@warpgate/admin/api",
            username="u",
            password='S3cr"et',
        )
        with pytest.raises(WarpgateClientError) as exc:
            c._request("GET", "/users")
        assert str(exc.value) == "Login failed: HTTP 401"

    def test_logout_error_response_is_closed(self):
        fp = MagicMock()
        error = HTTPError("https://host/x", 500, "Error", {}, fp)
        with patch("warpgate_client.client.build_opener") as mock_build:
            mock_build.return_value.open.side_effect = error
            c = WarpgateClient("https://host", username="u", password="p")
            c._session_cookie = "s=1"
            c.logout()
        fp.close.assert_called_once()

    def test_login_error_response_is_closed(self):
        fp = MagicMock()
        error = HTTPError("https://host/x", 401, "Unauthorized", {}, fp)
        with patch("warpgate_client.client.build_opener") as mock_build:
            mock_build.return_value.open.side_effect = error
            c = WarpgateClient("https://host", username="u", password="p")
            with pytest.raises(WarpgateClientError):
                c._login()
        fp.close.assert_called_once()


class TestNetworkErrors:
    def test_login_protocol_error_is_a_client_error(self):
        raw = _RawServer(b"garbage\r\n\r\n")
        try:
            c = WarpgateClient(
                f"http://127.0.0.1:{raw.port}/@warpgate/admin/api",
                username="u",
                password="p",
            )
            with pytest.raises(WarpgateClientError, match="Login request failed"):
                c._request("GET", "/users")
        finally:
            raw.close()

    def test_long_status_line_is_truncated(self):
        raw = _RawServer(b"X" * 60000 + b"\r\n\r\n")
        try:
            c = WarpgateClient(f"http://127.0.0.1:{raw.port}/api", token="t")
            with pytest.raises(WarpgateClientError) as exc:
                c._request("GET", "/x")
            assert len(str(exc.value)) < 1100
        finally:
            raw.close()

    def test_non_utf8_body_is_a_client_error(self, servers):
        api = servers({"/api/x": (200, {}, b"\xff\xfe")})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateClientError):
            c._request("GET", "/x")

    def test_error_body_read_is_bounded(self):
        error = MagicMock()
        error.read.return_value = b"x"
        error.__enter__ = MagicMock(return_value=error)
        error.__exit__ = MagicMock(return_value=False)
        _error_body(error)
        error.read.assert_called_once_with(64 * 1024 + 1)

    def test_error_without_body_does_not_report_the_reason(self):
        error = HTTPError("https://h/x", 502, "echo S3cretPass", {}, None)
        assert _error_body(error) == ("", None)

    @pytest.mark.parametrize(
        "exc",
        [
            TimeoutError("timed out"),
            ConnectionResetError(),
            IncompleteRead(b""),
            ValueError("I/O operation on closed file"),
        ],
    )
    def test_unreadable_error_body_keeps_the_status(self, exc):
        error = MagicMock()
        error.read.side_effect = exc
        error.__enter__ = MagicMock(return_value=error)
        error.__exit__ = MagicMock(return_value=False)
        assert _error_body(error)[0].startswith("<unreadable error body: ")

    @pytest.mark.parametrize(
        "token", ["abc\n", "abc\r", "a\x00b", "abc\u200bxyz", "\ufeffabc", "abcé"]
    )
    def test_token_with_control_characters_is_refused(self, token):
        with pytest.raises(ValueError) as exc:
            WarpgateClient("https://host", token=token)
        assert token not in str(exc.value)


class TestLoginNetworkErrors:
    def test_login_timeout_is_a_client_error(self):
        raw = _RawServer(None)
        try:
            c = WarpgateClient(
                f"http://127.0.0.1:{raw.port}/@warpgate/admin/api",
                username="u",
                password="p",
                timeout=1,
            )
            with pytest.raises(WarpgateClientError, match="Login request failed"):
                c._request("GET", "/users")
        finally:
            raw.close()

    def test_login_invalid_redirect_url_is_a_client_error(self):
        raw = _RawServer(
            b"HTTP/1.1 302 Found\r\nLocation: http://[::1/x\r\nContent-Length: 0\r\n\r\n"
        )
        try:
            c = WarpgateClient(
                f"http://127.0.0.1:{raw.port}/@warpgate/admin/api",
                username="u",
                password="p",
            )
            with pytest.raises(WarpgateClientError, match="Login request failed"):
                c._request("GET", "/users")
        finally:
            raw.close()

    def test_error_messages_do_not_embed_encoded_strings(self):
        error = UnicodeEncodeError("latin-1", "SECRETTOKEN\u200bxyz", 11, 12, "x")
        assert "SECRETTOKEN" not in _short(error)


class TestEchoedSecrets:
    @pytest.mark.parametrize(
        "echo",
        [
            'S3cr"et€',
            'S3cr\\"et\\u20ac',
            'S3cr\\"et€',
        ],
    )
    def test_secret_echoed_by_the_server_is_masked(self, servers, echo):
        api = servers(
            {"/api/x": (400, {}, f'{{"error": "bad", "echo": "{echo}"}}'.encode())}
        )
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x", {"name": "web", "auth": {"password": 'S3cr"et€'}})
        assert "S3cr" not in exc.value.message
        assert "********" in exc.value.message

    def test_non_secret_values_are_kept(self, servers):
        api = servers({"/api/x": (409, {}, b'{"error": "target web already exists"}')})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x", {"name": "web", "token": "tok-123"})
        assert "target web already exists" in exc.value.message

    def test_secret_cut_by_the_limit_is_masked(self, servers):
        secret = "SECRET-" + "z" * 40
        body = ("x" * 990 + secret).encode()
        api = servers({"/api/x": (400, {}, body)})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x", {"private_key": secret})
        assert "SECRET" not in exc.value.message

    @pytest.mark.parametrize("password", ["s", "ing", "a", "Short", '"', ",", "\\"])
    def test_short_password_keeps_the_policy_error_readable(self, servers, password):
        body = b'["TooShort","MissingUppercase","MissingDigit","MissingSpecial"]'
        api = servers({"/api/x": (422, {}, body)})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("POST", "/x", {"password": password})
        assert json.loads(exc.value.message) == json.loads(body)
        assert format_password_policy_error(exc.value).count(", ") == 3

    @pytest.mark.parametrize("password", ["MissingDigit", "TooShort"])
    def test_policy_error_does_not_reveal_a_password_named_like_a_violation(
        self, servers, password
    ):
        api = servers({"/api/x": (422, {}, b'["MissingDigit","TooShort"]')})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("POST", "/x", {"password": password})
        assert password not in exc.value.message
        assert format_password_policy_error(exc.value) == (
            "Password rejected by the server password policy: "
            "missing a digit, password is too short"
        )
        assert password not in str(exc.value)

    def test_short_secret_echoed_as_json_string_is_masked(self, servers):
        api = servers({"/api/x": (400, {}, b'{"password": "ab", "name": "abc"}')})
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="t")
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("POST", "/x", {"password": "ab", "name": "abc"})
        assert exc.value.message == '{"password": "********", "name": "abc"}'


class TestSecretValues:
    @pytest.mark.parametrize(
        "body",
        [
            {"password": "v"},
            {"auth": {"kind": "Password", "password": "v"}},
            {"auth": {"token": "v"}},
            {"auth": {"private_key": "v"}},
            {"auth": {"secret_id": "v"}},
            {"secret_key": "v"},
            {"recordings_storage": {"secret_access_key": "v"}},
            {"options": {"headers": {"Authorization": "v"}}},
            {"options": {"headers": {"X-Api-Key": "v"}}},
            {"options": {"headers": {"X-Hub-Signature": "v"}}},
            {"options": {"url": "https://u:v@host/"}},
            {"keys": [{"password": "v"}]},
            {"password": {"nested": "v"}},
            {"options": {"cluster_url": "https://u:v@host/"}},
            {"options": {"url": "https://%76:@host/"}, "x": "y"},
        ],
    )
    def test_secret_is_collected(self, body):
        assert "v" in _secret_values(body)

    def test_url_userinfo_is_collected(self):
        assert _secret_values({"url": "https://u:p%40ss@host/"}) == {
            "u",
            "p%40ss",
            "p@ss",
        }
        assert _secret_values({"url": "https://ghp_tok@host/"}) == {"ghp_tok"}

    def test_numeric_secret_is_collected(self):
        assert _secret_values({"password": 12345678}) == {"12345678"}

    @pytest.mark.parametrize(
        "body",
        [
            {"password_login_mode": "Disabled"},
            {"password_policy": {"min_length": 8}},
            {"name": "web", "kind": "Password"},
            {"options": {"url": "https://host/"}},
            {"options": {"url": "http://[bad"}},
            {"password": ""},
            {"secret": True},
        ],
    )
    def test_non_secret_is_ignored(self, body):
        assert _secret_values(body) == set()


def _echo(servers, body, payload, token="t"):
    api = servers({"/api/x": (400, {}, body.encode())})
    c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token=token)
    with pytest.raises(WarpgateAPIError) as exc:
        c._request("POST", "/x", payload)
    return exc.value


KEY = '-----BEGIN TEST KEY-----\nAAAAB3Nza\u00e9"x\n-----END-----'


class TestEchoForms:
    def test_request_quoted_in_a_json_string_is_masked(self, servers):
        inner = json.dumps({"secret_key": KEY})
        error = _echo(servers, json.dumps({"request": inner}), {"secret_key": KEY})
        assert "AAAAB3" not in error.message

    def test_request_quoted_twice_in_a_non_json_body_is_masked(self, servers):
        inner = json.dumps(json.dumps({"secret_key": KEY}))
        error = _echo(servers, f"<pre>{inner}</pre>", {"secret_key": KEY})
        assert "AAAAB3" not in error.message

    @pytest.mark.parametrize("ensure_ascii", [True, False])
    def test_escaped_long_secret_in_a_non_json_body_is_masked(
        self, servers, ensure_ascii
    ):
        echo = json.dumps(KEY, ensure_ascii=ensure_ascii)[1:-1]
        error = _echo(servers, f"<html>{echo}</html>", {"secret_key": KEY})
        assert "AAAAB3" not in error.message

    def test_secret_escaped_three_times_is_masked(self, servers):
        echo = json.dumps(json.dumps(json.dumps({"password": 'Pa"ss-long'})))
        error = _echo(servers, f"<pre>{echo}</pre>", {"password": 'Pa"ss-long'})
        assert "ss-long" not in error.message

    def test_large_body_is_marked_truncated_even_when_masking_shortens_it(
        self, servers
    ):
        secret = "S3cret-" + "x" * 4089
        error = _echo(servers, secret * 17, {"password": secret})
        assert len(error.message) < 1000
        assert error.message.endswith("... (truncated)")

    def test_html_escaped_secret_is_masked(self, servers):
        error = _echo(
            servers, "<p>S3cr&amp;t&lt;pass&gt;</p>", {"password": "S3cr&t<pass>"}
        )
        assert "S3cr" not in error.message

    def test_long_secret_inside_a_json_string_is_masked(self, servers):
        body = json.dumps({"error": "invalid password Sup3rSecret! given"})
        error = _echo(servers, body, {"password": "Sup3rSecret!"})
        assert "Sup3r" not in error.message
        assert "invalid password" in error.message

    def test_escaped_short_secret_inside_a_json_string_is_masked(self, servers):
        body = json.dumps({"error": 'invalid password p"\\1 given'})
        error = _echo(servers, body, {"password": 'p"\\1'})
        assert 'p\\"' not in error.message
        assert "invalid password" in error.message

    def test_short_secret_quoted_in_a_non_json_body_is_masked(self, servers):
        error = _echo(servers, 'bad request: "ab"', {"password": "ab"})
        assert error.message == 'bad request: "********"'

    def test_nested_secrets_are_masked_longest_first(self, servers):
        error = _echo(
            servers,
            "abcdefgh123 abcdefgh",
            {"password": "abcdefgh", "token": "abcdefgh123"},
        )
        assert error.message == "******** ********"

    def test_json_keys_are_kept_for_short_secrets(self, servers):
        error = _echo(servers, '{"name": "ab"}', {"password": "name"})
        assert error.message == '{"name": "ab"}'

    def test_short_secret_in_a_reserialized_body_is_masked(self, servers):
        body = json.dumps({"t": "LongSecret-123", "msg": 'bad pw p"w1 é'})
        error = _echo(servers, body, {"token": "LongSecret-123", "password": 'p"w1'})
        assert error.message == '{"t": "********", "msg": "bad pw ******** é"}'

    def test_python_repr_form_is_masked(self, servers):
        secret = 'it\'s "both" secret'
        error = _echo(servers, f"got {{'password': {secret!r}}}", {"password": secret})
        assert "both" not in error.message

    def test_one_char_secret_does_not_mask_escaped_quotes(self, servers):
        body = '{"msg": "bad \\"quote\\" here"}'
        error = _echo(servers, body, {"password": '"'})
        assert error.message == body

    def test_php_escaped_secret_is_masked(self, servers):
        echo = json.dumps(json.dumps({"password": "p/assword-long"})).replace(
            "/", "\\/"
        )
        error = _echo(servers, f"<pre>{echo}</pre>", {"password": "p/assword-long"})
        assert "-long" not in error.message

    def test_long_secret_in_an_escaped_json_key_is_masked(self, servers):
        body = '{"pass\\u002dsecret\\u002dlong": "x"}'
        error = _echo(servers, body, {"password": "pass-secret-long"})
        assert "secret" not in error.message

    def test_login_password_echoed_by_the_api_is_masked(self, servers):
        api = servers({"/api/x": (400, {}, b"bad credentials Adm1nPassw0rd")})
        c = WarpgateClient(
            f"http://127.0.0.1:{api.server_port}/api",
            username="u",
            password="Adm1nPassw0rd",
        )
        c._session_cookie = "warpgate-http-session=s"
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x")
        assert exc.value.message == "bad credentials ********"

    def test_lone_surrogate_is_replaced(self, servers):
        error = _echo(servers, '{"error": "bad \\ud83d value"}', {"password": "ab"})
        error.message.encode("utf-8")

    def test_long_secret_used_as_a_json_key_is_masked(self, servers):
        error = _echo(
            servers, '{"S3cretPassw0rd": "x"}', {"password": "S3cretPassw0rd"}
        )
        assert "S3cret" not in error.message

    def test_secret_hidden_by_a_duplicate_key_is_masked(self, servers):
        error = _echo(servers, '{"a": "ab", "a": "x"}', {"password": "ab"})
        assert error.message == '{"a": "********", "a": "x"}'

    @pytest.mark.parametrize(
        ("secret", "echo"),
        [
            ("a&b<c>dPassword", "a\\u0026b\\u003cc\\u003edPassword"),
            ("it's-a-Password", "it&#39;s-a-Password"),
        ],
    )
    def test_go_and_html_entity_forms_are_masked(self, servers, secret, echo):
        error = _echo(servers, f"<p>{echo}</p>", {"password": secret})
        assert "Password" not in error.message

    def test_deeply_nested_error_body_keeps_the_api_error(self, servers):
        error = _echo(servers, "[" * 60000, {"password": "ab"})
        assert error.status_code == 400

    def test_session_cookie_is_masked(self, servers):
        api = servers(
            {"/api/x": (400, {}, b"Cookie: warpgate-http-session=sess-value-123")}
        )
        c = WarpgateClient(
            f"http://127.0.0.1:{api.server_port}/api", username="u", password="p"
        )
        c._session_cookie = "warpgate-http-session=sess-value-123"
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x")
        assert "sess-value" not in exc.value.message

    def test_session_cookie_value_alone_is_masked(self, servers):
        api = servers({"/api/x": (400, {}, b"unknown session sess-value-123")})
        c = WarpgateClient(
            f"http://127.0.0.1:{api.server_port}/api", username="u", password="p"
        )
        c._session_cookie = "warpgate-http-session=sess-value-123"
        with pytest.raises(WarpgateAPIError) as exc:
            c._request("GET", "/x")
        assert exc.value.message == "unknown session ********"

    def test_escaped_form_is_masked_whole(self, servers):
        error = _echo(servers, "key: abcdefg\\\\", {"password": "abcdefg\\"})
        assert error.message == "key: ********"

    def test_token_is_masked(self, servers):
        error = _echo(
            servers, "X-Warpgate-Token: tok-abcdef-123", None, token="tok-abcdef-123"
        )
        assert "tok-abcdef" not in error.message


class TestHostCredentials:
    @pytest.mark.parametrize(
        "host",
        [
            "https://admin:S3cretPass@h/api",
            "admin:S3cretPass@h",
            "https://tok@h",
            "HTTPS://admin:S3cretPass@h\n",
            "https:/admin:S3cretPass@h\x7f",
            "https:/admin:S3cretPass@h",
            "https//admin:S3cretPass@h",
            "http:/admin:S3cretPass@h",
            "ftp://u:S3cretPass@h",
            "h\x00S3cretPass",
            "https://h\x7fS3cretPass",
            "warpgate\u200b.example",
            "https://h:8888#@S3cretPass",
            "h/path?q=S3cretPass",
            "https://h?",
            "https://h/?",
            "h#",
            "https://h:S3cretPass/api",
            "https://[S3cretPass/api",
            "https:///S3cretPass",
            "https://h/S3cretPass tok",
        ],
    )
    def test_credentials_in_host_are_refused(self, host):
        with pytest.raises(ValueError) as exc:
            WarpgateClient(host, token="t")
        assert "S3cret" not in str(exc.value) and "tok" not in str(exc.value)

    @pytest.mark.parametrize("host", ["HTTP://h", "Http://h:8888/x"])
    def test_scheme_is_case_insensitive(self, host):
        with patch("warpgate_client.client.warn") as warn:
            c = WarpgateClient(host, token="t")
        warn.assert_called_once()
        assert c.base_url == host.rstrip("/")

    @pytest.mark.parametrize(
        "host",
        [
            "h:8888",
            "localhost:",
            "[::1]:8888",
            "https://[::1]:8888/@warpgate/admin/api/",
            "bastión.example:8888",
            "localhost:8888/@warpgate/admin/api/",
        ],
    )
    def test_legitimate_hosts_are_accepted(self, host):
        assert WarpgateClient(host, token="t").base_url.startswith("https://")
