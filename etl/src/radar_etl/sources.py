"""Coletores das fontes públicas. Cada função recebe um `Fetcher` e devolve estruturas simples (pandas/dicts).

Fontes (todas abertas, sem chave):
  * BCB SGS      https://api.bcb.gov.br/dados/serie/bcdata.sgs.<id>/dados
  * BCB Olinda   PTAX (cotação do dólar) e Boletim Focus (expectativas de mercado)
  * IBGE         API de dados agregados (SIDRA): IPCA por grupo
  * Frankfurter  câmbio de referência do BCE, usado só como conferência independente do dólar
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import quote, urlencode

import pandas as pd

from .http import Fetcher

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{id}/dados"
OLINDA_PTAX = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@di,dataFinalCotacao=@df)"
OLINDA_FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
IBGE_IPCA = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/7060/periodos/{periods}/variaveis/63%7C2265"
)
FRANKFURTER = "https://api.frankfurter.dev/v1/latest"

# Séries do SGS (ids validados em 2026-10-26)
SGS_SELIC_META = 432  # Meta Selic definida pelo Copom (% a.a.), diária
SGS_CDI_ANUAL = 4389  # CDI anualizado base 252 (% a.a.), diária
SGS_IPCA_MENSAL = 433  # IPCA variação mensal (%)
SGS_IPCA_12M = 13522  # IPCA acumulado em 12 meses (%)

# Grupos do IPCA no agregado 7060 / classificação 315 do IBGE
IBGE_GENERAL_ID = 7169
IBGE_GROUP_IDS = (7170, 7445, 7486, 7558, 7625, 7660, 7712, 7766, 7786)


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def sgs_series(fetcher: Fetcher, series_id: int, start: date, end: date) -> pd.Series:
    """Série do SGS entre `start` e `end` (inclusive) como Series float indexada por data.

    Sempre passa `dataFinal`: sem ele a série da Selic meta devolve datas futuras já programadas.
    """
    rows = fetcher.get_json(
        SGS_URL.format(id=series_id),
        {"formato": "json", "dataInicial": _br(start), "dataFinal": _br(end)},
    )
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"SGS {series_id}: resposta vazia ou em formato inesperado")
    index = pd.to_datetime([r["data"] for r in rows], format="%d/%m/%Y")
    values = pd.to_numeric([r["valor"] for r in rows], errors="coerce")
    series = pd.Series(values, index=index, name=f"sgs_{series_id}", dtype="float64").dropna()
    series = series[~series.index.duplicated(keep="last")].sort_index()
    return series[series.index <= pd.Timestamp(end)]


def ptax_venda(fetcher: Fetcher, start: date, end: date) -> pd.Series:
    """PTAX de venda (R$ por US$), um valor por dia útil (último boletim do dia)."""
    data = fetcher.get_json(
        OLINDA_PTAX,
        {
            "@di": f"'{start:%m-%d-%Y}'",
            "@df": f"'{end:%m-%d-%Y}'",
            "$top": "10000",
            "$format": "json",
            "$select": "cotacaoVenda,dataHoraCotacao",
        },
    )
    rows = data.get("value") if isinstance(data, dict) else None
    if not rows:
        raise ValueError("PTAX: resposta vazia")
    frame = pd.DataFrame(rows)
    frame["ts"] = pd.to_datetime(frame["dataHoraCotacao"])
    frame = frame.sort_values("ts")
    frame["day"] = frame["ts"].dt.normalize()
    last_per_day = frame.groupby("day")["cotacaoVenda"].last()
    last_per_day.name = "ptax"
    return last_per_day.astype("float64")


@dataclass(frozen=True)
class FocusRow:
    indicator: str
    reference_year: int
    survey_date: date
    median: float
    mean: float
    minimum: float
    maximum: float
    respondents: int


def _odata_focus(fetcher: Fetcher, entity: str, filter_: str, top: int = 500) -> list[dict]:
    # O OData do BCB rejeita '+' como espaço (HTTP 400): a query precisa sair com %20.
    query = urlencode(
        {"$top": str(top), "$format": "json", "$orderby": "Data desc", "$filter": filter_},
        quote_via=quote,
    )
    data = fetcher.get_json(f"{OLINDA_FOCUS}{entity}?{query}")
    rows = data.get("value") if isinstance(data, dict) else None
    if not rows:
        raise ValueError(f"Focus/{entity}: resposta vazia para {filter_!r}")
    return rows


def focus_annual(fetcher: Fetcher, indicator: str, since: date) -> list[FocusRow]:
    """Expectativas anuais (mediana, base de cálculo 0 = últimos 30 dias) das últimas semanas."""
    rows = _odata_focus(
        fetcher,
        "ExpectativasMercadoAnuais",
        f"Indicador eq '{indicator}' and baseCalculo eq 0 and Data ge '{since:%Y-%m-%d}'",
    )
    return [
        FocusRow(
            indicator=r["Indicador"],
            reference_year=int(r["DataReferencia"]),
            survey_date=datetime.strptime(r["Data"], "%Y-%m-%d").date(),
            median=float(r["Mediana"]),
            mean=float(r["Media"]),
            minimum=float(r["Minimo"]),
            maximum=float(r["Maximo"]),
            respondents=int(r["numeroRespondentes"]),
        )
        for r in rows
    ]


def focus_ipca_12m_ahead(fetcher: Fetcher, since: date) -> tuple[date, float]:
    """Mediana suavizada da expectativa de IPCA para os próximos 12 meses (data da pesquisa, valor)."""
    rows = _odata_focus(
        fetcher,
        "ExpectativasMercadoInflacao12Meses",
        f"Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0 and Data ge '{since:%Y-%m-%d}'",
        top=50,
    )
    latest = max(rows, key=lambda r: r["Data"])
    return datetime.strptime(latest["Data"], "%Y-%m-%d").date(), float(latest["Mediana"])


def ibge_ipca_groups(fetcher: Fetcher, n_months: int) -> dict:
    """IPCA mensal e acumulado em 12 meses por grupo (índice geral + 9 grupos), últimos `n_months` meses.

    Devolve `{"names": {id: nome}, "monthly": {id: {"YYYYMM": valor}}, "acc12m": {id: {"YYYYMM": valor}}}`.
    """
    ids = ",".join(str(i) for i in (IBGE_GENERAL_ID, *IBGE_GROUP_IDS))
    url = (
        IBGE_IPCA.format(periods=f"-{n_months}")
        + f"?localidades=N1%5Ball%5D&classificacao=315%5B{ids}%5D"
    )
    payload = fetcher.get_json(url)
    out: dict = {"names": {}, "monthly": {}, "acc12m": {}}
    for variable in payload:
        bucket = "monthly" if str(variable["id"]) == "63" else "acc12m"
        for result in variable["resultados"]:
            category = result["classificacoes"][0]["categoria"]
            cat_id, name = next(iter(category.items()))
            out["names"][int(cat_id)] = name
            series = result["series"][0]["serie"]
            out[bucket][int(cat_id)] = {
                period: (None if value in ("...", "-", "X", "") else float(value))
                for period, value in series.items()
            }
    return out


def frankfurter_usd_brl(fetcher: Fetcher) -> tuple[date, float] | None:
    """Câmbio de referência independente (BCE via Frankfurter). Falha silenciosa: é só conferência."""
    try:
        data = fetcher.get_json(FRANKFURTER, {"base": "USD", "symbols": "BRL"})
        return datetime.strptime(data["date"], "%Y-%m-%d").date(), float(data["rates"]["BRL"])
    except Exception:  # noqa: BLE001 - a conferência é opcional por desenho
        return None


def months_back(today: date, months: int) -> date:
    """Primeiro dia do mês, `months` meses antes de `today`."""
    total = today.year * 12 + (today.month - 1) - months
    return date(total // 12, total % 12 + 1, 1)


def days_back(today: date, days: int) -> date:
    return today - timedelta(days=days)
