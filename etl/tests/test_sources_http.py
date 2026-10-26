"""Parsers das fontes (com payloads inventados) e cliente HTTP (com httpx.MockTransport). Sem rede."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
import pandas as pd
import pytest

from radar_etl import sources as src
from radar_etl.http import Fetcher, FetchError
from radar_etl.sources import FocusRow

# ---- Parsers das fontes ---------------------------------------------------------------------------------------


def test_sgs_series_converte_datas_descarta_vazios_e_duplicados(make_fetcher):
    payload = [
        {"data": "02/01/2026", "valor": "14.25"},
        {"data": "03/01/2026", "valor": ""},  # vazio vira NaN e sai
        {"data": "05/01/2026", "valor": "14.50"},
        {"data": "05/01/2026", "valor": "14.75"},  # duplicado: fica o último
        {"data": "10/01/2026", "valor": "14.75"},  # depois do fim: a série não pode trazer
    ]
    fetcher = make_fetcher({"sgs.432": payload})

    series = src.sgs_series(fetcher, 432, date(2026, 1, 1), date(2026, 1, 8))

    assert list(series.index) == [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-05")]
    assert list(series.values) == [14.25, 14.75]
    _, params = fetcher.calls[0]
    assert params == {"formato": "json", "dataInicial": "01/01/2026", "dataFinal": "08/01/2026"}


def test_sgs_series_resposta_vazia_falha(make_fetcher):
    fetcher = make_fetcher({"sgs.432": []})

    with pytest.raises(ValueError, match="resposta vazia"):
        src.sgs_series(fetcher, 432, date(2026, 1, 1), date(2026, 1, 8))


def test_sgs_series_formato_inesperado_falha(make_fetcher):
    fetcher = make_fetcher({"sgs.432": {"erro": "requisição inválida"}})

    with pytest.raises(ValueError, match="formato inesperado"):
        src.sgs_series(fetcher, 432, date(2026, 1, 1), date(2026, 1, 8))


def test_ptax_venda_usa_ultimo_boletim_do_dia(make_fetcher):
    payload = {
        "value": [
            {"cotacaoVenda": 5.30, "dataHoraCotacao": "2026-01-05 13:00:00.000"},
            {"cotacaoVenda": 5.20, "dataHoraCotacao": "2026-01-02 13:09:00.000"},
            {"cotacaoVenda": 5.10, "dataHoraCotacao": "2026-01-02 10:00:00.000"},
        ]
    }
    fetcher = make_fetcher({"CotacaoDolarPeriodo": payload})

    ptax = src.ptax_venda(fetcher, date(2026, 1, 1), date(2026, 1, 9))

    assert list(ptax.index) == [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-05")]
    assert list(ptax.values) == [5.20, 5.30]
    _, params = fetcher.calls[0]
    assert params is not None and params["@di"] == "'01-01-2026'"
    assert params["@df"] == "'01-09-2026'"


def test_ptax_venda_resposta_vazia_falha(make_fetcher):
    fetcher = make_fetcher({"CotacaoDolarPeriodo": {"value": []}})

    with pytest.raises(ValueError, match="PTAX: resposta vazia"):
        src.ptax_venda(fetcher, date(2026, 1, 1), date(2026, 1, 9))


def test_focus_annual_converte_linhas_e_codifica_espacos_com_percent20(make_fetcher):
    payload = {
        "value": [
            {
                "Indicador": "IPCA",
                "DataReferencia": "2026",
                "Data": "2026-10-23",
                "Mediana": "4.5",
                "Media": 4.6,
                "Minimo": 4.0,
                "Maximo": 5.2,
                "numeroRespondentes": 120,
            }
        ]
    }
    fetcher = make_fetcher({"ExpectativasMercadoAnuais": payload})

    rows = src.focus_annual(fetcher, "IPCA", date(2026, 9, 1))

    assert rows == [
        FocusRow(
            indicator="IPCA",
            reference_year=2026,
            survey_date=date(2026, 10, 23),
            median=4.5,
            mean=4.6,
            minimum=4.0,
            maximum=5.2,
            respondents=120,
        )
    ]
    url, _ = fetcher.calls[0]
    # O OData do BCB rejeita '+' como espaço: a query precisa usar %20.
    assert "%20eq%20" in url
    assert "+" not in url


def test_focus_annual_resposta_vazia_falha(make_fetcher):
    fetcher = make_fetcher({"ExpectativasMercadoAnuais": {"value": []}})

    with pytest.raises(ValueError, match="Focus"):
        src.focus_annual(fetcher, "IPCA", date(2026, 9, 1))


def test_focus_ipca_12m_ahead_pega_a_pesquisa_mais_recente(make_fetcher):
    payload = {
        "value": [
            {"Data": "2026-10-09", "Mediana": 4.3},
            {"Data": "2026-10-23", "Mediana": 4.2},
            {"Data": "2026-10-16", "Mediana": 4.25},
        ]
    }
    fetcher = make_fetcher({"Inflacao12Meses": payload})

    assert src.focus_ipca_12m_ahead(fetcher, date(2026, 9, 1)) == (date(2026, 10, 23), 4.2)


def test_ibge_ipca_groups_separa_mensal_de_acumulado_e_trata_marcadores(make_fetcher):
    payload: list[dict[str, Any]] = [
        {
            "id": 63,
            "resultados": [
                {
                    "classificacoes": [{"categoria": {"7169": "Índice geral"}}],
                    "series": [{"serie": {"202608": "0.1", "202609": "0.3"}}],
                },
                {
                    "classificacoes": [{"categoria": {"7170": "1.Alimentação e bebidas"}}],
                    "series": [{"serie": {"202608": "0.5", "202609": "..."}}],
                },
            ],
        },
        {
            "id": 2265,
            "resultados": [
                {
                    "classificacoes": [{"categoria": {"7169": "Índice geral"}}],
                    "series": [{"serie": {"202609": "4.5"}}],
                },
                {
                    "classificacoes": [{"categoria": {"7170": "1.Alimentação e bebidas"}}],
                    "series": [{"serie": {"202609": "6.1"}}],
                },
            ],
        },
    ]
    fetcher = make_fetcher({"agregados/7060": payload})

    out = src.ibge_ipca_groups(fetcher, n_months=2)

    assert out["names"] == {7169: "Índice geral", 7170: "1.Alimentação e bebidas"}
    assert out["monthly"][7169] == {"202608": 0.1, "202609": 0.3}
    assert out["monthly"][7170] == {"202608": 0.5, "202609": None}  # "..." vira None
    assert out["acc12m"][7170] == {"202609": 6.1}


def test_frankfurter_falha_vira_none_porque_a_conferencia_e_opcional(make_fetcher):
    fetcher = make_fetcher({"frankfurter.dev": RuntimeError("fora do ar")})

    assert src.frankfurter_usd_brl(fetcher) is None


def test_frankfurter_sucesso_devolve_data_e_taxa(make_fetcher):
    fetcher = make_fetcher({"frankfurter.dev": {"date": "2026-10-23", "rates": {"BRL": 5.4}}})

    assert src.frankfurter_usd_brl(fetcher) == (date(2026, 10, 23), 5.4)


def test_months_back_e_days_back():
    assert src.months_back(date(2026, 10, 26), 12) == date(2025, 10, 1)
    assert src.months_back(date(2026, 1, 15), 1) == date(2025, 12, 1)
    assert src.days_back(date(2026, 3, 1), 1) == date(2026, 2, 28)


# ---- Cliente HTTP ---------------------------------------------------------------------------------------------


def make_client_fetcher(handler, **kwargs) -> tuple[Fetcher, list[float]]:
    sleeps: list[float] = []
    options = {"retries": 3, "min_interval": 0.0, "backoff": 2.0, "sleep": sleeps.append}
    options.update(kwargs)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Fetcher(client, **options), sleeps


def test_http_resposta_html_com_200_e_retentada_ate_vir_json():
    responses = iter(
        [
            httpx.Response(200, text="<html>Requisição inválida</html>"),
            httpx.Response(200, json=[{"ok": 1}]),
        ]
    )
    fetcher, sleeps = make_client_fetcher(lambda request: next(responses))

    assert fetcher.get_json("https://example.invalid/x") == [{"ok": 1}]
    assert sleeps == [2.0]  # backoff da primeira tentativa


def test_http_falha_persistente_levanta_fetcherror_com_backoff_crescente():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    fetcher, sleeps = make_client_fetcher(handler)

    with pytest.raises(FetchError, match="HTTP 500"):
        fetcher.get_json("https://example.invalid/x")
    assert calls == 3
    assert sleeps == [2.0, 4.0]  # sem espera depois da última tentativa


def test_http_erro_de_transporte_e_tratado_como_transitorio():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rota")

    fetcher, sleeps = make_client_fetcher(handler, retries=2)

    with pytest.raises(FetchError, match="ConnectError"):
        fetcher.get_json("https://example.invalid/x")
    assert sleeps == [2.0]


def test_http_throttle_espera_o_intervalo_minimo_entre_chamadas():
    now = [0.0]
    fetcher, sleeps = make_client_fetcher(
        lambda request: httpx.Response(200, json={"ok": True}),
        min_interval=0.9,
        clock=lambda: now[0],
    )

    fetcher.get_json("https://example.invalid/a")  # primeira chamada: sem espera
    fetcher.get_json("https://example.invalid/b")  # mesmo instante: espera o intervalo inteiro

    assert sleeps == [0.9]
