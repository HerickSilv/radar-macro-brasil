from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from radar_etl.models import FocusItem
from radar_etl.sources import FocusRow
from radar_etl.transform import (
    build_focus_items,
    build_ipca_groups,
    build_kpis,
    clean_group_name,
    consecutive_above,
    dollar_with_bands,
    percentile_rank,
    real_rate_ex_post,
    to_points,
    to_weekly,
    value_on_or_before,
)


def ts(text: str) -> pd.Timestamp:
    return pd.Timestamp(text)


def test_to_weekly_mantem_ultima_observacao_com_data_real():
    # Semana de 5 a 11/out/2026 (segunda a domingo): fica a última observação (9/out), não a sexta-feira.
    index = pd.to_datetime(["2026-10-05", "2026-10-06", "2026-10-09", "2026-10-12"])
    series = pd.Series([14.0, 14.1, 14.2, 14.3], index=index)

    weekly = to_weekly(series)

    assert list(weekly.index) == [ts("2026-10-09"), ts("2026-10-12")]
    assert list(weekly.values) == [14.2, 14.3]


def test_to_points_arredonda_e_usa_data_da_observacao():
    series = pd.Series([1.23456], index=pd.to_datetime(["2026-01-02"]))

    points = to_points(series)

    assert len(points) == 1
    assert points[0].d == date(2026, 1, 2)
    assert points[0].v == 1.23


def test_real_rate_ex_post_usa_selic_do_fim_do_mes_e_ignora_meses_sem_selic():
    selic = pd.Series(
        [14.25, 14.50, 14.75],
        index=pd.to_datetime(["2026-01-02", "2026-01-30", "2026-02-02"]),
    )
    ipca12m = pd.Series(
        [5.0, 6.0, 6.5],
        index=pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"]),
    )

    real = real_rate_ex_post(selic, ipca12m)

    # Março não tem Selic observada: fica de fora.
    assert list(real.index) == [ts("2026-01-01"), ts("2026-02-01")]
    assert real.iloc[0] == pytest.approx(((1 + 0.145) / (1 + 0.05) - 1) * 100)
    assert real.iloc[1] == pytest.approx(((1 + 0.1475) / (1 + 0.06) - 1) * 100)


def test_dollar_with_bands_nulos_no_inicio_e_corte_por_keep_from():
    index = pd.date_range("2026-01-01", periods=100, freq="D")
    ptax = pd.Series(np.arange(100, dtype=float) + 1.0, index=index)
    keep_from = ts("2026-02-01")

    points = dollar_with_bands(ptax, keep_from, window=90)

    assert points[0].d == date(2026, 2, 1)
    assert all(p.d >= date(2026, 2, 1) for p in points)
    # Antes de 90 pregões completos não há média nem banda.
    assert points[0].ma90 is None and points[0].lo is None and points[0].hi is None

    full = next(p for p in points if p.d == date(2026, 3, 31))  # 90º pregão da série
    window = ptax.iloc[:90].to_numpy()
    assert full.ma90 == pytest.approx(window.mean(), abs=1e-4)
    sd = np.std(window, ddof=1)
    assert full.lo == pytest.approx(window.mean() - sd, abs=1e-4)
    assert full.hi == pytest.approx(window.mean() + sd, abs=1e-4)


def test_percentile_rank_conta_valores_menores_ou_iguais():
    window = pd.Series([1.0, 2.0, 3.0, 4.0])

    assert percentile_rank(window, 3.0) == 75.0
    assert percentile_rank(window, 0.0) == 0.0
    assert percentile_rank(window, 10.0) == 100.0


def test_consecutive_above_conta_so_a_sequencia_final():
    assert consecutive_above(pd.Series([1.0, 5.0, 6.0, 7.0]), 4.0) == 3
    assert consecutive_above(pd.Series([5.0, 6.0, 1.0, 7.0]), 4.0) == 1
    assert consecutive_above(pd.Series([5.0, 1.0]), 4.0) == 0


def test_value_on_or_before_pega_observacao_anterior_ou_igual():
    series = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-01-01", "2026-03-01"]))

    assert value_on_or_before(series, ts("2026-02-15")) == 1.0
    assert value_on_or_before(series, ts("2026-03-01")) == 2.0


def test_value_on_or_before_sem_observacao_anterior_levanta_erro():
    series = pd.Series([1.0], index=pd.to_datetime(["2026-01-01"]))

    with pytest.raises(ValueError, match="sem observação"):
        value_on_or_before(series, ts("2025-12-31"))


def _monthly(values: dict[str, float]) -> pd.Series:
    return pd.Series(list(values.values()), index=pd.to_datetime(list(values.keys())))


def test_build_kpis_calcula_variacao_e_rotulos():
    months = {
        "2026-01-01": 14.25,
        "2026-02-01": 14.25,
        "2026-03-01": 14.25,
        "2026-04-01": 13.0,
        "2026-05-01": 13.25,
        "2026-06-01": 13.5,
        "2026-07-01": 14.0,
        "2026-08-01": 14.5,
        "2026-09-01": 14.75,
        "2026-10-01": 15.0,
    }
    selic = _monthly(months)
    cdi = selic - 0.1
    ipca12m = _monthly({"2026-09-01": 4.5, "2026-10-01": 4.2})
    ptax_index = pd.date_range("2026-07-01", "2026-10-26", freq="D")
    ptax = pd.Series(5.0, index=ptax_index)
    ptax.iloc[-1] = 5.5

    kpis = {k.id: k for k in build_kpis(selic, cdi, ipca12m, ptax)}

    assert kpis["selic"].value == 15.0
    assert kpis["selic"].as_of == date(2026, 10, 1)
    assert kpis["selic"].delta == 2.0  # 15,00 - 13,00 (6 meses antes)
    assert kpis["selic"].up_is_good is None
    assert kpis["cdi"].delta == 2.0
    assert kpis["ipca12m"].delta == pytest.approx(-0.3)
    assert kpis["ipca12m"].up_is_good is False
    assert kpis["usd"].value == 5.5
    assert kpis["usd"].delta == pytest.approx(10.0)
    assert len(kpis["usd"].spark) == 60


def test_build_focus_items_pega_mediana_da_pesquisa_anterior_mais_proxima():
    def row(survey: date, year: int, median: float) -> FocusRow:
        return FocusRow(
            indicator="IPCA",
            reference_year=year,
            survey_date=survey,
            median=median,
            mean=median,
            minimum=median - 0.5,
            maximum=median + 0.5,
            respondents=100,
        )

    rows = {
        "IPCA": [
            row(date(2026, 10, 23), 2026, 4.5),
            row(date(2026, 10, 23), 2027, 4.0),
            row(date(2026, 10, 23), 2028, 3.8),
            row(date(2026, 9, 20), 2026, 4.4),  # 33 dias antes: dentro da janela de 28 dias
            row(date(2026, 10, 16), 2026, 4.6),  # 7 dias antes: fora da janela, não deve ser usada
        ]
    }

    items, latest = build_focus_items(rows, first_year=2026)

    assert latest == date(2026, 10, 23)
    assert [i.year for i in items] == [2026, 2027, 2028]
    assert all(isinstance(i, FocusItem) for i in items)
    assert items[0].median == 4.5
    assert items[0].previous_median == 4.4
    assert items[0].previous_date == date(2026, 9, 20)
    assert items[1].previous_median is None and items[1].previous_date is None


def test_clean_group_name_remove_numeracao():
    assert clean_group_name("1.Alimentação e bebidas") == "Alimentação e bebidas"
    assert clean_group_name("  9. Outros ") == "Outros"


def test_build_ipca_groups_monta_grade_com_slug_e_nulos():
    raw = {
        "names": {7169: "Índice geral", 7170: "1.Alimentação e bebidas", 7171: "2.Habitação"},
        "monthly": {
            7169: {"202608": 0.1, "202609": 0.3},
            7170: {"202608": 0.5, "202609": None},
            7171: {"202608": 0.2, "202609": 0.4},
        },
        "acc12m": {
            7169: {"202609": 4.5},
            7170: {"202609": 6.1},
            7171: {},  # sem acumulado: vira None
        },
    }

    groups = build_ipca_groups(raw, general_id=7169, group_ids=(7170, 7171))

    assert groups.months == ["2026-08", "2026-09"]
    assert groups.general.id == "geral"
    assert groups.general.name == "IPCA geral"
    assert groups.general.acc12m == 4.5
    alimentacao, habitacao = groups.groups
    assert alimentacao.id == "alimentacao-e-bebidas"
    assert alimentacao.name == "Alimentação e bebidas"
    assert alimentacao.monthly == [0.5, None]
    assert alimentacao.acc12m == 6.1
    assert habitacao.id == "habitacao"
    assert habitacao.acc12m is None
