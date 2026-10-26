from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from radar_etl.checks import (
    DataQualityError,
    check_cdi_vs_selic,
    check_dollar_jump,
    check_fresh,
    check_series,
)

TODAY = date(2026, 10, 26)


def daily(values: list[float], end: date = TODAY) -> pd.Series:
    index = pd.date_range(end=pd.Timestamp(end), periods=len(values), freq="D")
    return pd.Series(values, index=index, dtype="float64")


def test_serie_vazia_falha():
    with pytest.raises(DataQualityError, match="série vazia"):
        check_series("selic", pd.Series([], dtype="float64"), TODAY)


def test_valor_fora_da_faixa_plausivel_falha():
    with pytest.raises(DataQualityError, match="fora da faixa"):
        check_series("selic", daily([14.0, 150.0]), TODAY)


def test_serie_plausivel_e_recente_passa():
    check_series("selic", daily([14.0, 14.25]), TODAY)


def test_dado_velho_falha_e_limite_e_inclusivo():
    # Selic: limite de 7 dias.
    check_fresh("selic", date(2026, 10, 19), TODAY)  # 7 dias: no limite, passa
    with pytest.raises(DataQualityError, match="dado velho"):
        check_fresh("selic", date(2026, 10, 18), TODAY)  # 8 dias


def test_ipca_tem_limite_maior_por_causa_da_divulgacao_mensal():
    check_fresh("ipca12m", date(2026, 7, 20), TODAY)  # 98 dias: dentro do limite de 100


def test_cdi_colado_na_selic_passa_e_descolado_falha():
    check_cdi_vs_selic(14.25, 14.15)
    with pytest.raises(DataQualityError, match="divergem"):
        check_cdi_vs_selic(14.25, 13.5)


def test_salto_pequeno_do_dolar_passa_sem_conferencia():
    check_dollar_jump(pd.Series([5.0, 5.2]), None)  # 4%: abaixo de 5%


def test_salto_grande_sem_conferencia_falha():
    with pytest.raises(DataQualityError, match="sem fonte independente"):
        check_dollar_jump(pd.Series([5.0, 5.4]), None)  # 8%


def test_salto_grande_confirmado_pela_fonte_independente_passa():
    check_dollar_jump(pd.Series([5.0, 5.4]), (TODAY, 5.41))


def test_salto_grande_divergente_da_fonte_independente_falha():
    with pytest.raises(DataQualityError, match="não confirmado"):
        check_dollar_jump(pd.Series([5.0, 5.4]), (TODAY, 5.0))


def test_salto_implausivel_falha_mesmo_com_conferencia():
    with pytest.raises(DataQualityError, match="implausível"):
        check_dollar_jump(pd.Series([5.0, 6.5]), (TODAY, 6.5))  # 30%


def test_dolar_com_uma_unica_observacao_falha():
    with pytest.raises(DataQualityError, match="menos de 2"):
        check_dollar_jump(pd.Series([5.0]), None)
