"""Fixtures compartilhadas. Nenhum teste faz chamada de rede: os payloads abaixo são inventados e pequenos."""

from __future__ import annotations

from typing import Any

import pytest


class FakeFetcher:
    """Substitui o `Fetcher` real: responde pela primeira chave que aparece na URL, sem rede.

    Se a chave for uma exceção, ela é lançada (útil para simular falha de fonte opcional).
    """

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    def get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        self.calls.append((url, params))
        for key, value in self.responses.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise AssertionError(f"chamada inesperada no teste: {url}")

    def close(self) -> None:
        pass


@pytest.fixture
def make_fetcher():
    def _make(responses: dict[str, Any]) -> FakeFetcher:
        return FakeFetcher(responses)

    return _make


@pytest.fixture
def snapshot_payload() -> dict[str, Any]:
    """Snapshot mínimo e válido no formato camelCase do `macro.json` (valores inventados)."""
    point = {"d": "2026-10-01", "v": 15.0}
    return {
        "meta": {
            "schemaVersion": 1,
            "generatedAt": "2026-10-26T12:00:00Z",
            "asOf": "2026-10-26",
            "sources": [
                {
                    "id": "bcb-sgs",
                    "name": "BCB (teste)",
                    "url": "https://example.invalid/",
                    "lastObservation": "2026-10-26",
                }
            ],
        },
        "kpis": [
            {
                "id": "selic",
                "label": "Selic meta",
                "value": 15.0,
                "unit": "% a.a.",
                "asOf": "2026-10-01",
                "delta": 2.0,
                "deltaUnit": "p.p.",
                "deltaLabel": "vs. 6 meses",
                "upIsGood": None,
                "spark": [14.0, 15.0],
                "sparkLabel": "últimos 12 meses",
            }
        ],
        "series": {
            "selic": [point],
            "cdi": [point],
            "ipca12m": [{"d": "2026-09-01", "v": 4.5}],
            "ipcaMonthly": [{"d": "2026-09-01", "v": 0.3}],
            "realRate": [{"d": "2026-09-01", "v": 10.1}],
            "usd": [{"d": "2026-10-26", "v": 5.5, "ma90": None, "lo": None, "hi": None}],
        },
        "focus": {
            "asOf": "2026-10-23",
            "items": [
                {
                    "indicator": "IPCA",
                    "year": 2026,
                    "median": 4.5,
                    "mean": 4.6,
                    "minimum": 4.0,
                    "maximum": 5.2,
                    "respondents": 120,
                    "previousMedian": None,
                    "previousDate": None,
                }
            ],
            "ipca12mAhead": 4.2,
        },
        "ipcaGroups": {
            "months": ["2026-09"],
            "general": {"id": "geral", "name": "IPCA geral", "monthly": [0.3], "acc12m": 4.5},
            "groups": [
                {
                    "id": "alimentacao-e-bebidas",
                    "name": "Alimentação e bebidas",
                    "monthly": [0.5],
                    "acc12m": 6.1,
                }
            ],
        },
        "targets": {"inflationCenter": 3.0, "inflationTolerance": 1.5},
        "macro": {
            "severity": "atencao",
            "label": "Cenário em atenção",
            "summary": "1 de 3 frentes pedem atenção: juros.",
            "lanes": [
                {"id": "juros", "label": "Juros", "severity": "atencao", "headline": "Juro alto"}
            ],
            "rule": "Pior estado entre os insights.",
        },
        "insights": [
            {
                "id": "juro-real",
                "lane": "juros",
                "severity": "atencao",
                "headline": "Juro real 10,1% a.a. · alto",
                "title": "Juro real",
                "meaning": "Texto de teste.",
                "tip": "Dica de teste.",
                "evidence": [{"label": "Selic meta", "value": "15,00% a.a."}],
                "rule": "Regra de teste.",
            }
        ],
    }
