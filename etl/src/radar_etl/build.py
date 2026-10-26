"""Orquestra a coleta, as checagens, as transformações e os insights, e devolve o snapshot validado."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from . import sources as src
from .checks import (
    check_cdi_vs_selic,
    check_dollar_jump,
    check_fresh,
    check_series,
)
from .http import Fetcher
from .insights import DollarStats, InsightInputs, build_insights, build_macro
from .models import (
    SCHEMA_VERSION,
    Focus,
    MacroSnapshot,
    Meta,
    Series,
    Source,
    Targets,
)
from .transform import (
    build_focus_items,
    build_ipca_groups,
    build_kpis,
    consecutive_above,
    dollar_with_bands,
    percentile_rank,
    real_rate_ex_post,
    to_points,
    to_weekly,
    value_on_or_before,
)

log = logging.getLogger("radar_etl.build")

# Meta de inflação contínua (CMN): centro e tolerância, em p.p.
INFLATION_CENTER = 3.0
INFLATION_TOLERANCE = 1.5

HISTORY_YEARS = 5
USD_HISTORY_DAYS = 730
USD_BUFFER_DAYS = 160  # histórico extra só para a média móvel de 90 pregões já nascer completa
IPCA_GROUP_MONTHS = 12
FOCUS_INDICATORS = ("IPCA", "Selic", "Câmbio", "PIB Total")


def _dollar_stats(ptax: pd.Series, cross_check: tuple[date, float] | None) -> DollarStats:
    window = ptax.iloc[-90:]
    last_year = ptax.iloc[-253:]
    moves = last_year.pct_change().abs().dropna()
    day_move = abs(float(ptax.iloc[-1] / ptax.iloc[-2] - 1))
    return DollarStats(
        last=float(ptax.iloc[-1]),
        previous=float(ptax.iloc[-2]),
        ma90=float(window.mean()),
        sd90=float(window.std()),
        percentile_12m=percentile_rank(last_year, float(ptax.iloc[-1])),
        is_largest_move_12m=bool(day_move >= moves.max() - 1e-12),
        cross_check=cross_check,
    )


def build_snapshot(fetcher: Fetcher, today: date, now: datetime | None = None) -> MacroSnapshot:
    now = now or datetime.now(UTC)
    start = date(today.year - HISTORY_YEARS, today.month, 1)

    log.info("coletando séries do BCB (SGS)…")
    selic = src.sgs_series(fetcher, src.SGS_SELIC_META, start, today)
    cdi = src.sgs_series(fetcher, src.SGS_CDI_ANUAL, start, today)
    ipca12m = src.sgs_series(fetcher, src.SGS_IPCA_12M, start, today)
    ipca_m = src.sgs_series(fetcher, src.SGS_IPCA_MENSAL, start, today)

    log.info("coletando PTAX (Olinda)…")
    ptax = src.ptax_venda(
        fetcher, today - timedelta(days=USD_HISTORY_DAYS + USD_BUFFER_DAYS), today
    )

    log.info("coletando Boletim Focus (Olinda)…")
    since = today - timedelta(days=50)
    focus_rows = {ind: src.focus_annual(fetcher, ind, since) for ind in FOCUS_INDICATORS}
    focus_12m_date, focus_12m = src.focus_ipca_12m_ahead(fetcher, since)

    log.info("coletando IPCA por grupo (IBGE)…")
    ibge = src.ibge_ipca_groups(fetcher, IPCA_GROUP_MONTHS)

    log.info("conferência independente do dólar (Frankfurter)…")
    cross_check = src.frankfurter_usd_brl(fetcher)

    # ---- Qualidade: falha alto ----
    check_series("selic", selic, today)
    check_series("cdi", cdi, today)
    check_series("ipca12m", ipca12m, today)
    check_series("ipca_mensal", ipca_m, today)
    check_series("ptax", ptax, today)
    check_cdi_vs_selic(float(selic.iloc[-1]), float(cdi.iloc[-1]))
    check_dollar_jump(ptax, cross_check)
    focus_latest = max(row.survey_date for rows in focus_rows.values() for row in rows)
    check_fresh("focus", focus_latest, today)

    # ---- Transformações ----
    ipca_groups = build_ipca_groups(ibge, src.IBGE_GENERAL_ID, src.IBGE_GROUP_IDS)
    ipca_ref_month = ipca12m.index[-1].strftime("%Y-%m")
    if ipca_groups.months[-1] != ipca_ref_month:
        log.warning(
            "IBGE (%s) e BCB (%s) em meses de referência diferentes para o IPCA",
            ipca_groups.months[-1],
            ipca_ref_month,
        )

    focus_items, _ = build_focus_items(focus_rows, first_year=today.year)
    by_key = {(i.indicator, i.year): i for i in focus_items}

    keep_from = pd.Timestamp(today - timedelta(days=USD_HISTORY_DAYS))
    kpis = build_kpis(selic, cdi, ipca12m, ptax.loc[ptax.index >= keep_from])
    real = real_rate_ex_post(selic, ipca12m)

    inputs = InsightInputs(
        selic=float(selic.iloc[-1]),
        selic_6m_ago=value_on_or_before(selic, selic.index[-1] - pd.DateOffset(months=6)),
        ipca12m=float(ipca12m.iloc[-1]),
        ipca12m_ref_month=ipca_ref_month,
        months_above_ceiling=consecutive_above(ipca12m, INFLATION_CENTER + INFLATION_TOLERANCE),
        target_center=INFLATION_CENTER,
        target_tolerance=INFLATION_TOLERANCE,
        focus_ipca_12m_ahead=focus_12m,
        focus_year=today.year,
        focus_selic_year_end=by_key[("Selic", today.year)].median,
        focus_selic_next_year=by_key[("Selic", today.year + 1)].median,
        focus_ipca_far_year=today.year + 2,
        focus_ipca_far=by_key[("IPCA", today.year + 2)].median,
        usd=_dollar_stats(ptax, cross_check),
        groups_acc12m=[(g.name, g.acc12m) for g in ipca_groups.groups if g.acc12m is not None],
    )
    insights = build_insights(inputs)

    sources = [
        Source(
            id="bcb-sgs",
            name="BCB · Sistema Gerenciador de Séries (Selic meta, CDI, IPCA)",
            url="https://api.bcb.gov.br/dados/serie/",
            last_observation=max(selic.index[-1], cdi.index[-1], ipca12m.index[-1]).date(),
        ),
        Source(
            id="bcb-ptax",
            name="BCB · PTAX (Olinda)",
            url="https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/aplicacao#!/recursos",
            last_observation=ptax.index[-1].date(),
        ),
        Source(
            id="bcb-focus",
            name="BCB · Expectativas de Mercado / Boletim Focus (Olinda)",
            url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/aplicacao#!/recursos",
            last_observation=max(focus_latest, focus_12m_date),
        ),
        Source(
            id="ibge-sidra",
            name="IBGE · IPCA por grupo (agregado 7060)",
            url="https://servicodados.ibge.gov.br/api/docs/agregados?versao=3",
            last_observation=date(int(ipca_ref_month[:4]), int(ipca_ref_month[5:]), 1),
        ),
    ]
    if cross_check is not None:
        sources.append(
            Source(
                id="frankfurter",
                name="Frankfurter · câmbio de referência do BCE (conferência do dólar)",
                url="https://frankfurter.dev/",
                last_observation=cross_check[0],
            )
        )

    snapshot = MacroSnapshot(
        meta=Meta(
            schema_version=SCHEMA_VERSION,
            generated_at=now.astimezone(UTC),
            as_of=max(k.as_of for k in kpis),
            sources=sources,
        ),
        kpis=kpis,
        series=Series(
            selic=to_points(to_weekly(selic)),
            cdi=to_points(to_weekly(cdi)),
            ipca12m=to_points(ipca12m),
            ipca_monthly=to_points(ipca_m),
            real_rate=to_points(real),
            usd=dollar_with_bands(ptax, keep_from),
        ),
        focus=Focus(as_of=focus_latest, items=focus_items, ipca_12m_ahead=round(focus_12m, 2)),
        ipca_groups=ipca_groups,
        targets=Targets(inflation_center=INFLATION_CENTER, inflation_tolerance=INFLATION_TOLERANCE),
        macro=build_macro(insights),
        insights=insights,
    )
    log.info(
        "snapshot montado: %d insights, estado geral '%s'", len(insights), snapshot.macro.severity
    )
    return snapshot
