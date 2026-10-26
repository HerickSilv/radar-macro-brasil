"""Cliente HTTP do ETL: timeout, intervalo mínimo entre chamadas, retry com backoff e checagem de JSON.

Por que existe: o gateway do BCB às vezes responde HTTP 200 com uma página HTML de "Requisição inválida" (limite de
taxa/WAF). Um `response.json()` ingênuo quebraria de forma obscura; aqui isso vira uma falha transitória com retry.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

log = logging.getLogger("radar_etl.http")

USER_AGENT = "radar-macro-brasil/1.0 (projeto de portfolio; consome apenas dados publicos)"


class FetchError(RuntimeError):
    """A fonte não respondeu um JSON válido depois de todas as tentativas."""


class Fetcher:
    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        retries: int = 4,
        min_interval: float = 0.9,
        backoff: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        )
        self._retries = retries
        self._min_interval = min_interval
        self._backoff = backoff
        self._sleep = sleep
        self._clock = clock
        self._last_call = float("-inf")

    def close(self) -> None:
        self._client.close()

    def get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        last_error = "sem detalhes"
        for attempt in range(self._retries):
            self._throttle()
            try:
                response = self._client.get(url, params=params)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                body = response.text
                if response.status_code == 200 and body.lstrip()[:1] in ("[", "{"):
                    try:
                        return response.json()
                    except ValueError as exc:
                        last_error = f"JSON inválido: {exc}"
                elif response.status_code == 200:
                    last_error = "HTTP 200 com corpo não-JSON (página de erro do gateway?)"
                else:
                    last_error = f"HTTP {response.status_code}"
            wait = self._backoff * (2**attempt)
            log.warning(
                "falha em %s (tentativa %d/%d): %s", url, attempt + 1, self._retries, last_error
            )
            if attempt < self._retries - 1:
                self._sleep(wait)
        raise FetchError(f"{url} -> {last_error}")

    def _throttle(self) -> None:
        elapsed = self._clock() - self._last_call
        if elapsed < self._min_interval:
            self._sleep(self._min_interval - elapsed)
        self._last_call = self._clock()
