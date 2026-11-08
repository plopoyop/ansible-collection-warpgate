"""
Base client for the Warpgate API

This module provides the core HTTP client functionality for interacting with the Warpgate API.
"""

import html
import http.client
import json
import re
import ssl
import urllib.parse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from ansible.module_utils.common.warnings import warn

# Responses larger than this are refused (protects against a misbehaving server
# or proxy streaming an unbounded body).
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024
# Server error bodies are reported in module messages: keep them short.
MAX_ERROR_BODY_BYTES = 1000
# Read a bit more than reported so that a secret cut by the limit is still masked.
MAX_ERROR_SCAN_BYTES = 64 * 1024


def _user_api_base(admin_base: str) -> str:
    """Derive user API base URL from admin API base (e.g. .../admin/api -> .../api/)."""
    base = admin_base.rstrip("/")
    admin_suffix = "/@warpgate/admin/api"
    base = base.removesuffix(admin_suffix)
    return base + "/@warpgate/api/"


def path_segment(value: Any) -> str:
    """Encode a value used as one segment of an API path."""
    if value is None:
        raise ValueError("Missing path segment")
    segment = str(value)
    if segment in ("", ".", ".."):
        raise ValueError(f"Invalid path segment: {segment!r}")
    return urllib.parse.quote(segment, safe="")


_SECRET_KEY = re.compile(
    r"(^|_)(password|token|secret|secret_id|secret_key|secret_access_key|private_key)$",
    re.IGNORECASE,
)
# Shorter secrets are not searched as raw substrings: that would garble
# messages (e.g. the password policy variants) and give the secret away.
MIN_MASKED_SUBSTRING = 8
# Escaped forms of a shorter secret are only masked from this length on, so
# that a one-character secret does not mask every escaped quote.
MIN_MASKED_FORM = 4
MASK = "********"


def _url_credentials(url: str) -> set[str]:
    try:
        parts = urllib.parse.urlsplit(url)
        userinfo = {parts.username, parts.password} if "@" in parts.netloc else set()
    except ValueError:
        return set()
    return {v for u in userinfo if u for v in (u, urllib.parse.unquote(u))}


def _secret_values(value: Any, secret: bool = False, key: str = "") -> set[str]:
    """Values held under secret-looking keys of a request body, and the
    userinfo of its URLs."""
    if isinstance(value, dict):
        found = set()
        for k, item in value.items():
            k = str(k)
            hidden = secret or key == "headers" or bool(_SECRET_KEY.search(k))
            found |= _secret_values(item, hidden, k)
        return found
    if isinstance(value, list):
        return set().union(*(_secret_values(item, secret, key) for item in value))
    if secret and isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return {str(value)} if str(value) else set()
    if isinstance(value, str) and key.lower().endswith("url"):
        return _url_credentials(value)
    return set()


def _secret_forms(secret: str) -> set[str]:
    """Forms of a secret echoed by a server: raw, JSON-escaped once or more
    (a request quoted inside a JSON string, as Python, Go or PHP encode it),
    Python repr and HTML-escaped."""
    escaped = html.escape(secret)
    forms = {secret, escaped, escaped.replace("&#x27;", "&#39;"), repr(secret)[1:-1]}
    for ensure_ascii in (True, False):
        form = secret
        for _ in range(3):
            form = json.dumps(form, ensure_ascii=ensure_ascii)[1:-1]
            forms.add(form)
            forms.add(
                form.replace("&", "\\u0026")
                .replace("<", "\\u003c")
                .replace(">", "\\u003e")
            )
            forms.add(form.replace("/", "\\/"))
    if len(secret) < MIN_MASKED_SUBSTRING:
        forms = {f for f in forms if f != secret and len(f) >= MIN_MASKED_FORM}
    return forms


def _masked_forms(secrets: list[str]) -> list[str]:
    """Forms to replace, longest secret first, then longest form first."""
    return [
        form
        for secret in secrets
        for form in sorted(_secret_forms(secret), key=len, reverse=True)
    ]


def _mask_text(text: str, forms: list[str]) -> str:
    for form in forms:
        text = text.replace(form, MASK)
    return text


def _mask_json(value: Any, secrets: list[str], forms: list[str]) -> Any:
    if isinstance(value, dict):
        return {k: _mask_json(v, secrets, forms) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_json(item, secrets, forms) for item in value]
    if isinstance(value, str):
        return MASK if value in secrets else _mask_text(value, forms)
    return value


def _unique_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate key")
    return dict(pairs)


def _error_body(error: HTTPError, secrets: set[str] = frozenset()) -> tuple[str, Any]:
    """Bounded error body with the request's secrets masked, in case the server
    echoes the request in a form no_log would not catch, and the unmasked
    parsed JSON body (None if not JSON)."""
    try:
        with error:
            raw = error.read(MAX_ERROR_SCAN_BYTES + 1)
    except (http.client.HTTPException, OSError, ValueError) as exc:
        return f"<unreadable error body: {_short(exc)}>", None
    body = raw.decode("utf-8", errors="replace")
    secrets = sorted(secrets, key=len, reverse=True)
    forms = _masked_forms(secrets)
    try:
        # Duplicate keys would hide a value from the parsed body.
        parsed = json.loads(body, object_pairs_hook=_unique_keys)
        masked = _mask_json(parsed, secrets, forms)
        # Re-serialized even when unchanged, so the text pass sees keys and
        # nested strings in a canonical form.
        body = (
            json.dumps(masked, ensure_ascii=False)
            .encode("utf-8", errors="replace")
            .decode("utf-8")
        )
    except (ValueError, RecursionError):
        parsed = None
    if parsed is None:
        for secret in secrets:
            for quoted in {json.dumps(secret), json.dumps(secret, ensure_ascii=False)}:
                body = body.replace(quoted, f'"{MASK}"')
    # Also masks the secrets found in JSON keys.
    body = _mask_text(body, forms)
    if len(raw) > MAX_ERROR_SCAN_BYTES or len(body) > MAX_ERROR_BODY_BYTES:
        body = body[:MAX_ERROR_BODY_BYTES] + "... (truncated)"
    return body, parsed


def _bounded(text: str) -> str:
    if len(text) > MAX_ERROR_BODY_BYTES:
        return text[:MAX_ERROR_BODY_BYTES] + "... (truncated)"
    return text


def _short(error: Exception) -> str:
    """Describe a network error without repr(): a UnicodeError's repr embeds the
    whole string being encoded (e.g. a header holding the token)."""
    return _bounded(f"{type(error).__name__}: {error}")


def _read_bounded(response) -> bytes:
    chunks = []
    size = 0
    while chunk := response.read(READ_CHUNK_BYTES):
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise WarpgateClientError(
                f"Response larger than {MAX_RESPONSE_BYTES} bytes"
            )
        chunks.append(chunk)
    # read(amt) does not raise IncompleteRead on a body cut short: http.client
    # keeps the number of bytes still expected from Content-Length.
    remaining = getattr(response, "length", None)
    if isinstance(remaining, int) and remaining > 0:
        raise WarpgateClientError(
            f"Incomplete response: {remaining} bytes missing after {size}"
        )
    return b"".join(chunks)


def _origin(url: str) -> tuple:
    parts = urllib.parse.urlsplit(url)
    default_port = {"http": 80, "https": 443}.get(parts.scheme)
    return parts.scheme, parts.hostname or "", parts.port or default_port


class WarpgateClientError(Exception):
    """Base exception for Warpgate client errors"""


class WarpgateAPIError(WarpgateClientError):
    """Exception for Warpgate API errors"""

    def __init__(self, status_code: int, message: str, details: Any = None):
        self.status_code = status_code
        self.message = message
        # Unmasked parsed body, for callers that interpret it; never reported.
        self.details = details
        super().__init__(f"API request failed with status {status_code}: {message}")


class _SameOriginRedirectHandler(HTTPRedirectHandler):
    """Refuse redirects to another scheme, host or port: the API token and the
    session cookie would be sent there."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urljoin(req.full_url, newurl)
        new = urllib.parse.urlsplit(target)
        try:
            same_origin = _origin(req.full_url) == _origin(target)
        except ValueError:
            same_origin = False
        if not same_origin or "@" in new.netloc:
            fp.close()
            old = urllib.parse.urlsplit(req.full_url)
            raise WarpgateClientError(
                _bounded(
                    f"Refusing to follow a redirect from {old.scheme}://{old.hostname} "
                    f"to {new.scheme}://{new.hostname}"
                )
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class WarpgateClient:
    """
    Client to interact with the Warpgate API.

    Authentication: pass token=... and/or (username=..., password=...).
    If a token is provided it is used directly. Otherwise, the client
    logs in via the user API with username/password and reuses the
    session cookie for subsequent admin API requests.
    """

    def __init__(
        self,
        host: str,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 30,
        insecure: bool = False,
    ):
        """
        Initialize the Warpgate client.

        Args:
            host: Base URL of the Warpgate admin API (e.g. https://host:8888/@warpgate/admin/api/)
            token: API token (takes priority over username/password if provided)
            username: Admin username (fallback when no token is provided)
            password: Admin password
            timeout: Request timeout in seconds
            insecure: If True, disables SSL certificate verification
        """
        if not host:
            raise ValueError("host cannot be empty")
        if not token and not (username and password):
            raise ValueError("Provide either token or both username and password")

        if not host.startswith(("http://", "https://")):
            host = f"https://{host}"
        if host.startswith("http://"):
            warn(
                "The Warpgate API is reached over plain HTTP: the API token or "
                "credentials are sent unencrypted."
            )

        self.base_url = host.rstrip("/")
        # Anything but printable ASCII (a trailing newline, a zero-width space
        # or a BOM pasted with the token) makes http.client fail on the header,
        # with the token in its error.
        if token and not (token.isascii() and token.isprintable()):
            raise ValueError(
                "The API token must only contain printable ASCII characters"
            )
        self._token = token
        self._username = username
        self._password = password
        self._session_cookie = None
        self.timeout = timeout
        self.insecure = insecure

        self.ssl_context = None
        if insecure:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        self._opener = build_opener(
            HTTPSHandler(context=self.ssl_context), _SameOriginRedirectHandler()
        )

    @property
    def token(self) -> str | None:
        return self._token

    def _login(self) -> None:
        """Login via user API and store session cookie for subsequent requests."""
        user_base = _user_api_base(self.base_url)
        login_url = user_base + "auth/login"

        login_body = json.dumps(
            {"username": self._username, "password": self._password}
        ).encode("utf-8")
        login_req = Request(login_url, data=login_body, method="POST")
        login_req.add_header("Content-Type", "application/json; charset=utf-8")
        login_req.add_header("Accept", "application/json; charset=utf-8")

        try:
            with self._opener.open(login_req, timeout=self.timeout) as resp:
                if resp.getcode() not in (200, 201):
                    raise WarpgateClientError(f"Login returned {resp.getcode()}")
                set_cookie = resp.headers.get("Set-Cookie")
                if not set_cookie:
                    raise WarpgateClientError(
                        "Login did not return Set-Cookie (session)"
                    )
                self._session_cookie = set_cookie.split(";")[0].strip()
        except HTTPError as e:
            e.close()
            raise WarpgateClientError(f"Login failed: HTTP {e.code}")
        except URLError as e:
            raise WarpgateClientError(
                f"Login request failed: {_bounded(str(e.reason))}"
            )
        except (http.client.HTTPException, OSError, ValueError) as e:
            raise WarpgateClientError(f"Login request failed: {_short(e)}")

    def logout(self) -> None:
        """
        Close the API session opened by :meth:`_login`.

        Warpgate keeps every login as an open HTTP session until it is either
        logged out or expired, so each module run must release its own.
        Best effort: never raises, so it can be called from a ``finally`` block.
        """
        if self._session_cookie is None:
            return

        logout_url = _user_api_base(self.base_url) + "auth/logout"
        req = Request(logout_url, data=b"", method="POST")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Accept", "application/json; charset=utf-8")
        req.add_header("Cookie", self._session_cookie)

        try:
            with self._opener.open(req, timeout=self.timeout):
                pass
        except HTTPError as e:
            e.close()
        except (OSError, ValueError, http.client.HTTPException, WarpgateClientError):
            pass
        finally:
            self._session_cookie = None

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> Any:
        """
        Performs an HTTP request to the Warpgate API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: Endpoint path (e.g., /users)
            body: Request body (will be serialized to JSON)

        Returns:
            Decoded JSON response (can be a dict, list, or other JSON-serializable type)

        Raises:
            WarpgateAPIError: On API error
            WarpgateClientError: On connection error
        """
        if self._token is None and self._session_cookie is None:
            self._login()

        if path.startswith("/"):
            url = f"{self.base_url}{path}"
        else:
            url = f"{self.base_url}/{path}"

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Accept", "application/json; charset=utf-8")
        if self._token:
            req.add_header("X-Warpgate-Token", self._token)
        elif self._session_cookie:
            req.add_header("Cookie", self._session_cookie)

        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                response_body = _read_bounded(response).decode("utf-8")

                if status_code == 204:  # No Content
                    return {}

                if not response_body:
                    return {}

                return json.loads(response_body)

        except HTTPError as e:
            secrets = _secret_values(body)
            secrets |= {
                v for v in (self._token, self._password, self._session_cookie) if v
            }
            if self._session_cookie and "=" in self._session_cookie:
                secrets.add(self._session_cookie.split("=", 1)[1])
            raise WarpgateAPIError(e.code, *_error_body(e, secrets))
        except URLError as e:
            raise WarpgateClientError(f"Request failed: {e.reason}")
        except json.JSONDecodeError as e:
            raise WarpgateClientError(f"Failed to decode response: {e}")
        except (http.client.HTTPException, OSError, ValueError) as e:
            raise WarpgateClientError(f"Request failed: {_short(e)}")
