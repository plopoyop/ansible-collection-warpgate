"""
Base client for the Warpgate API

This module provides the core HTTP client functionality for interacting with the Warpgate API.
"""

import json
import ssl
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _user_api_base(admin_base: str) -> str:
    """Derive user API base URL from admin API base (e.g. .../admin/api -> .../api/)."""
    base = admin_base.rstrip("/")
    admin_suffix = "/@warpgate/admin/api"
    if base.endswith(admin_suffix):
        base = base[: -len(admin_suffix)]
    return base + "/@warpgate/api/"


class WarpgateClientError(Exception):
    """Base exception for Warpgate client errors"""

    pass


class WarpgateAPIError(WarpgateClientError):
    """Exception for Warpgate API errors"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API request failed with status {status_code}: {message}")


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
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
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

        self.base_url = host.rstrip("/")
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

    @property
    def token(self) -> Optional[str]:
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
            with urlopen(
                login_req, timeout=self.timeout, context=self.ssl_context
            ) as resp:
                if resp.getcode() not in (200, 201):
                    raise WarpgateClientError(f"Login returned {resp.getcode()}")
                set_cookie = resp.headers.get("Set-Cookie")
                if not set_cookie:
                    raise WarpgateClientError(
                        "Login did not return Set-Cookie (session)"
                    )
                self._session_cookie = set_cookie.split(";")[0].strip()
        except HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else str(e)
            raise WarpgateClientError(f"Login failed: {e.code} {body}")
        except URLError as e:
            raise WarpgateClientError(f"Login request failed: {e.reason}")

    def _request(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None
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
            with urlopen(
                req, timeout=self.timeout, context=self.ssl_context
            ) as response:
                status_code = response.getcode()
                response_body = response.read().decode("utf-8")

                if status_code == 204:  # No Content
                    return {}

                if not response_body:
                    return {}

                return json.loads(response_body)

        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            raise WarpgateAPIError(e.code, error_body)
        except URLError as e:
            raise WarpgateClientError(f"Request failed: {e.reason}")
        except json.JSONDecodeError as e:
            raise WarpgateClientError(f"Failed to decode response: {e}")
