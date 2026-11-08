"""Tests for WarpgateClient initialisation and URL helpers."""

import socket
import threading
from http.client import IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, Request

import pytest
from warpgate_client.client import (
    WarpgateAPIError,
    WarpgateClient,
    WarpgateClientError,
    _error_body,
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
        assert all(port != other.server_port for port, _, _ in _Handler.seen)

    def test_same_origin_redirect_is_followed(self, servers):
        api = servers({"/api/new": (200, {}, b'{"ok": true}')})
        api.RequestHandlerClass.routes["/api/old"] = (
            301,
            {"Location": "/api/new"},
            b"",
        )
        c = WarpgateClient(f"http://127.0.0.1:{api.server_port}/api", token="secret")
        assert c._request("GET", "/old") == {"ok": True}
        assert ("/api/new", "secret") in [(p, t) for _, p, t in _Handler.seen]


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
        assert all(port != other.server_port for port, _, _ in _Handler.seen)


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
        conn, _ = self.sock.accept()
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

    def test_logout_error_response_is_closed(self):
        fp = MagicMock()
        error = HTTPError("https://host/x", 500, "Error", {}, fp)
        with patch("warpgate_client.client.build_opener") as mock_build:
            mock_build.return_value.open.side_effect = error
            c = WarpgateClient("https://host", username="u", password="p")
            c._session_cookie = "s=1"
            c.logout()
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
        error.read.assert_called_once_with(1000 + 1)

    def test_error_without_body_does_not_report_the_reason(self):
        error = HTTPError("https://h/x", 502, "echo S3cretPass", {}, None)
        assert _error_body(error) == ""

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
        assert _error_body(error).startswith("<unreadable error body: ")

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
