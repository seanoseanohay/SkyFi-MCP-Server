"""
SkyFi Platform API HTTP client.
Uses X-Skyfi-Api-Key auth, base URL from config, retries on 5xx.
"""

import time
from typing import Any

import requests

from src.config import get_logger, settings

logger = get_logger(__name__)

# Default request timeout (seconds)
DEFAULT_TIMEOUT = getattr(settings, "skyfi_request_timeout", 30)
MAX_RETRIES = getattr(settings, "skyfi_retry_count", 3)


class SkyFiClientError(Exception):
    """Raised when a SkyFi API request fails after retries or with a client error."""

    def __init__(self, message: str, status_code: int | None = None, body: str = ""):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class SkyFiClient:
    """
    HTTP client for SkyFi Platform API.
    - Auth via X-Skyfi-Api-Key header
    - Base URL from settings
    - Retries on 5xx (exponential backoff, up to MAX_RETRIES)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ):
        self.api_key = (api_key or settings.skyfi_api_key).strip()
        self.base_url = (base_url or settings.skyfi_api_base_url).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(self._headers())

    def _headers(self) -> dict[str, str]:
        return {
            "X-Skyfi-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        url = (
            f"{self.base_url}{path}"
            if path.startswith("/")
            else f"{self.base_url}/{path}"
        )
        timeout = kwargs.pop("timeout", self.timeout)
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = self._session.request(
                    method,
                    url,
                    json=json,
                    timeout=timeout,
                    **kwargs,
                )
            except requests.RequestException as e:
                last_exc = e
                logger.warning(
                    "Request failed (attempt %s/%s): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                )
                if attempt < self.max_retries:
                    sleep = 2**attempt
                    time.sleep(sleep)
                else:
                    raise SkyFiClientError(
                        f"Request failed after {self.max_retries + 1} attempts: {e}"
                    ) from e

            # Retry only on 5xx
            if 500 <= resp.status_code < 600:
                last_exc = SkyFiClientError(
                    f"Server error {resp.status_code}",
                    status_code=resp.status_code,
                    body=resp.text[:500],
                )
                logger.warning(
                    "5xx response (attempt %s/%s): %s %s",
                    attempt + 1,
                    self.max_retries + 1,
                    resp.status_code,
                    resp.text[:200],
                )
                if attempt < self.max_retries:
                    sleep = 2**attempt
                    time.sleep(sleep)
                else:
                    raise last_exc
            else:
                return resp

        raise last_exc or SkyFiClientError("Request failed")

    def post(
        self, path: str, json: dict[str, Any] | None = None, **kwargs: Any
    ) -> requests.Response:
        """POST to path (relative to base URL). Retries on 5xx."""
        return self._request("POST", path, json=json, **kwargs)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """GET path (relative to base URL). Retries on 5xx."""
        return self._request("GET", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        """DELETE path (relative to base URL). Retries on 5xx."""
        return self._request("DELETE", path, **kwargs)
