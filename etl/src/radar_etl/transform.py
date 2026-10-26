"""Transformações puras (pandas) das séries: reamostragem, juro real, bandas do dólar, KPIs, grupos do IPCA."""

from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd

from .models import DollarPoint, FocusItem, IpcaGroup, IpcaGroups, Kpi, Point
from .sources import FocusRow


def r(value: float, ndigits: int = 2) -> float:
    return round(float(value), ndigits)


def to_weekly(series: pd.Series) -> pd.Series:
    """Mantém a última observação de cada semana (com a data real da observação, não a sexta-feira)."""
    weeks = series.index.to_period("W")
    return series[~weeks.duplicated(keep="last")]


def to_points(series: pd.Series, ndigits: int = 2) -> list[Point]:
    return [Point(d=ts.date(), v=r(v, ndigits)) for ts, v in series.items()]


def real_rate_ex_post(selic_daily: pd.Series, ipca12m: pd.Series) -> pd.Series:
    """Juro real ex-post mensal, em %: (1 + Selic no fim do mês) / (1 + IPCA 12m) - 1.

    `ipca12m` é indexado pelo 1º dia do mês de referência; a Selic usada é a última observação do mesmo mês.
    """
    month_end_selic = selic_daily.groupby(selic_daily.index.to_period("M")).last()
    out = {}
    for ts, ipca in ipca12m.items():
        period = ts.to_period("M")
        if period in month_end_selic.index:
            selic = month_end_selic.loc[period]
            out[ts] = ((1 + selic / 100) / (1 + ipca / 100) - 1) * 100
    return pd.Series(out, dtype="float64")


def dollar_with_bands(
    ptax: pd.Series, keep_from: pd.Timestamp, window: int = 90
) -> list[DollarPoint]:
    """PTAX + média móvel de `window` dias úteis + banda de ±1 desvio-padrão; devolve só de `keep_from` em diante."""
    ma = ptax.rolling(window, min_periods=window).mean()
    sd = ptax.rolling(window, min_periods=window).std()
    frame = pd.DataFrame({"v": ptax, "ma": ma, "lo": ma - sd, "hi": ma + sd})
    frame = frame[frame.index >= keep_from]

    def opt(x: float) -> float | None:
        return None if pd.isna(x) else r(x, 4)

    return [
        DollarPoint(d=ts.date(), v=r(row.v, 4), ma90=opt(row.ma), lo=opt(row.lo), hi=opt(row.hi))
        for ts, row in frame.iterrows()
    ]


def percentile_rank(window: pd.Series, value: float) -> float:
    """Percentil (0-100) de `value` dentro de `window`: fração de observações menores ou iguais."""
    return float((window <= value).mean() * 100)


def consecutive_above(series: pd.Series, threshold: float) -> int:
    """Quantos pontos finais consecutivos estão acima de `threshold`."""
    count = 0
    for value in reversed(series.tolist()):
        if value > threshold:
            count += 1
        else:
            break
    return count


def value_on_or_before(series: pd.Series, ts: pd.Timestamp) -> float:
    prior = series[series.index <= ts]
    if prior.empty:
        raise ValueError(f"sem observação em ou antes de {ts.date()}")
    return float(prior.iloc[-1])


def build_kpis(selic: pd.Series, cdi: pd.Series, ipca12m: pd.Series, ptax: pd.Series) -> list[Kpi]:
    """KPIs do topo do painel. Cada um traz valor, variação com rótulo do período e sparkline."""
    sel_last = selic.index[-1]
    sel_ref = value_on_or_before(selic, sel_last - pd.DateOffset(months=6))
    cdi_last = cdi.index[-1]
    cdi_ref = value_on_or_before(cdi, cdi_last - pd.DateOffset(months=6))
    spark_sel = to_weekly(selic[selic.index > sel_last - pd.DateOffset(months=12)])
    spark_cdi = to_weekly(cdi[cdi.index > cdi_last - pd.DateOffset(months=12)])

    ipca_last_ts = ipca12m.index[-1]
    usd_last = float(ptax.iloc[-1])
    usd_prev = float(ptax.iloc[-2])

    return [
        Kpi(
            id="selic",
            label="Selic meta",
            value=r(selic.iloc[-1]),
            unit="% a.a.",
            as_of=sel_last.date(),
            delta=r(selic.iloc[-1] - sel_ref),
            delta_unit="p.p.",
            delta_label="vs. 6 meses",
            up_is_good=None,
            spark=[r(v) for v in spark_sel],
            spark_label="últimos 12 meses",
        ),
        Kpi(
            id="cdi",
            label="CDI",
            value=r(cdi.iloc[-1]),
            unit="% a.a.",
            as_of=cdi_last.date(),
            delta=r(cdi.iloc[-1] - cdi_ref),
            delta_unit="p.p.",
            delta_label="vs. 6 meses",
            up_is_good=None,
            spark=[r(v) for v in spark_cdi],
            spark_label="últimos 12 meses",
        ),
        Kpi(
            id="ipca12m",
            label="IPCA em 12 meses",
            value=r(ipca12m.iloc[-1]),
            unit="% a.a.",
            as_of=ipca_last_ts.date(),
            delta=r(ipca12m.iloc[-1] - ipca12m.iloc[-2]),
            delta_unit="p.p.",
            delta_label="vs. mês anterior",
            up_is_good=False,
            spark=[r(v) for v in ipca12m.iloc[-12:]],
            spark_label="últimos 12 meses",
        ),
        Kpi(
            id="usd",
            label="Dólar PTAX",
            value=r(usd_last, 4),
            unit="R$",
            as_of=ptax.index[-1].date(),
            delta=r((usd_last / usd_prev - 1) * 100),
            delta_unit="%",
            delta_label="vs. dia anterior",
            up_is_good=False,
            spark=[r(v, 4) for v in ptax.iloc[-60:]],
            spark_label="últimos 60 pregões",
        ),
    ]


def build_focus_items(
    rows_by_indicator: dict[str, list[FocusRow]],
    first_year: int,
    n_years: int = 3,
    lookback_days: int = 28,
) -> tuple[list[FocusItem], date]:
    """Itens do Focus (anos `first_year`..+n_years-1) na pesquisa mais recente, com a mediana de ~4 semanas antes."""
    items: list[FocusItem] = []
    latest_overall = None
    for indicator, rows in rows_by_indicator.items():
        latest = max(r_.survey_date for r_ in rows)
        latest_overall = latest if latest_overall is None else max(latest_overall, latest)
        cutoff = latest - timedelta(days=lookback_days)
        past_dates = [r_.survey_date for r_ in rows if r_.survey_date <= cutoff]
        previous_date = max(past_dates) if past_dates else None
        for year in range(first_year, first_year + n_years):
            now = next(r_ for r_ in rows if r_.survey_date == latest and r_.reference_year == year)
            before = next(
                (
                    r_
                    for r_ in rows
                    if previous_date
                    and r_.survey_date == previous_date
                    and r_.reference_year == year
                ),
                None,
            )
            items.append(
                FocusItem(
                    indicator=indicator,  # type: ignore[arg-type]
                    year=year,
                    median=r(now.median),
                    mean=r(now.mean),
                    minimum=r(now.minimum),
                    maximum=r(now.maximum),
                    respondents=now.respondents,
                    previous_median=r(before.median) if before else None,
                    previous_date=before.survey_date if before else None,
                )
            )
    assert latest_overall is not None
    return items, latest_overall


_GROUP_PREFIX = re.compile(r"^\d+\.\s*")


def clean_group_name(name: str) -> str:
    """'1.Alimentação e bebidas' -> 'Alimentação e bebidas'."""
    return _GROUP_PREFIX.sub("", name.strip()).strip()


def _slug(name: str) -> str:
    base = clean_group_name(name).lower()
    for src, dst in (
        ("ç", "c"),
        ("ã", "a"),
        ("á", "a"),
        ("â", "a"),
        ("é", "e"),
        ("ê", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ô", "o"),
        ("ú", "u"),
    ):
        base = base.replace(src, dst)
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def build_ipca_groups(raw: dict, general_id: int, group_ids: tuple[int, ...]) -> IpcaGroups:
    """Monta o heatmap grupo × mês a partir da resposta do IBGE (`sources.ibge_ipca_groups`)."""
    months = sorted(raw["monthly"][general_id].keys())

    def make(cat_id: int, *, general: bool = False) -> IpcaGroup:
        monthly = [raw["monthly"][cat_id].get(m) for m in months]
        acc = raw["acc12m"][cat_id].get(months[-1])
        name = "IPCA geral" if general else clean_group_name(raw["names"][cat_id])
        return IpcaGroup(
            id="geral" if general else _slug(raw["names"][cat_id]),
            name=name,
            monthly=[None if v is None else r(v) for v in monthly],
            acc12m=None if acc is None else r(acc),
        )

    return IpcaGroups(
        months=[f"{m[:4]}-{m[4:]}" for m in months],
        general=make(general_id, general=True),
        groups=[make(i) for i in group_ids],
    )
