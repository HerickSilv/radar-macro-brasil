"""Checagens de sanidade e de atualidade. Se algo estiver errado o ETL falha: é melhor manter o deploy anterior do
que publicar um número velho ou absurdo com cara de dado novo."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

log = logging.getLogger("radar_etl.checks")


class DataQualityError(RuntimeError):
    """Os dados coletados não passam nas checagens de qualidade."""


# (mín, máx) plausíveis por série; fora disso é quase certamente erro de fonte/parsing
RANGES: dict[str, tuple[float, float]] = {
    "selic": (0.0, 40.0),
    "cdi": (0.0, 40.0),
    "ipca12m": (-5.0, 60.0),
    "ipca_mensal": (-5.0, 10.0),
    "ptax": (1.0, 20.0),
}
# Idade máxima (dias) da última observação em relação a hoje
MAX_AGE_DAYS: dict[str, int] = {
    "selic": 7,
    "cdi": 7,
    "ptax": 7,
    "ipca12m": 100,  # divulgado ~dia 10 do mês seguinte; mês de referência = dia 1
    "ipca_mensal": 100,
    "focus": 10,
}
DOLLAR_JUMP_CROSSCHECK = 5.0  # variação diária (%) que exige conferência com fonte independente
DOLLAR_JUMP_IMPLAUSIBLE = 25.0  # acima disso nunca publicamos
DOLLAR_CROSSCHECK_TOLERANCE = 5.0  # divergência máxima (%) entre PTAX e a fonte independente
CDI_SELIC_MAX_GAP = 0.5  # p.p.; o CDI anda colado à Selic meta


def check_series(name: str, series: pd.Series, today: date) -> None:
    if series.empty:
        raise DataQualityError(f"{name}: série vazia")
    low, high = RANGES[name]
    bad = series[(series < low) | (series > high)]
    if not bad.empty:
        raise DataQualityError(
            f"{name}: {len(bad)} valor(es) fora da faixa plausível [{low}, {high}] "
            f"(ex.: {bad.index[0].date()} = {bad.iloc[0]})"
        )
    check_fresh(name, series.index[-1].date(), today)


def check_fresh(name: str, last: date, today: date) -> None:
    age = (today - last).days
    limit = MAX_AGE_DAYS[name]
    if age > limit:
        raise DataQualityError(
            f"{name}: dado velho (última observação {last}, {age} dias; limite {limit})"
        )


def check_cdi_vs_selic(selic_last: float, cdi_last: float) -> None:
    if abs(selic_last - cdi_last) > CDI_SELIC_MAX_GAP:
        raise DataQualityError(
            f"CDI ({cdi_last}) e Selic meta ({selic_last}) divergem mais de {CDI_SELIC_MAX_GAP} p.p."
        )


def check_dollar_jump(ptax: pd.Series, cross_check: tuple[date, float] | None) -> None:
    """Saltos grandes na PTAX só passam se uma fonte independente confirmar o nível."""
    if len(ptax) < 2:
        raise DataQualityError("ptax: menos de 2 observações")
    last, prev = float(ptax.iloc[-1]), float(ptax.iloc[-2])
    jump = abs(last / prev - 1) * 100
    if jump > DOLLAR_JUMP_IMPLAUSIBLE:
        raise DataQualityError(f"ptax: variação diária implausível ({jump:.1f}%)")
    if jump <= DOLLAR_JUMP_CROSSCHECK:
        return
    if cross_check is None:
        raise DataQualityError(
            f"ptax: variação diária de {jump:.1f}% sem fonte independente para confirmar (conferência indisponível)"
        )
    _, reference = cross_check
    divergence = abs(last / reference - 1) * 100
    if divergence > DOLLAR_CROSSCHECK_TOLERANCE:
        raise DataQualityError(
            f"ptax: salto de {jump:.1f}% não confirmado (PTAX {last:.4f} vs referência {reference:.4f}, "
            f"divergência {divergence:.1f}%)"
        )
    log.warning(
        "PTAX variou %.1f%% no dia e a fonte independente confirma o nível (%.4f vs %.4f): salto tratado como real.",
        jump,
        last,
        reference,
    )
