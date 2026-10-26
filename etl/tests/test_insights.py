from __future__ import annotations

from radar_etl.insights import (
    DollarStats,
    InsightInputs,
    anchoring_insight,
    build_insights,
    build_macro,
    dollar_insight,
    groups_insight,
    inflation_target_insight,
    month_label,
    pct,
    pt,
    real_rate_insight,
    selic_direction_insight,
    signed,
)
from radar_etl.models import SEVERITY_ORDER, Insight, Severity


def dollar(
    last: float = 5.5,
    previous: float = 5.5,
    ma90: float = 5.5,
    sd90: float = 0.1,
    percentile: float = 50.0,
    largest: bool = False,
    cross: tuple | None = None,
) -> DollarStats:
    return DollarStats(
        last=last,
        previous=previous,
        ma90=ma90,
        sd90=sd90,
        percentile_12m=percentile,
        is_largest_move_12m=largest,
        cross_check=cross,
    )


def make_inputs(**overrides) -> InsightInputs:
    base = {
        "selic": 14.25,
        "selic_6m_ago": 15.0,
        "ipca12m": 4.0,
        "ipca12m_ref_month": "2026-09",
        "months_above_ceiling": 0,
        "target_center": 3.0,
        "target_tolerance": 1.5,
        "focus_ipca_12m_ahead": 4.0,
        "focus_year": 2026,
        "focus_selic_year_end": 14.25,
        "focus_selic_next_year": 12.0,
        "focus_ipca_far_year": 2028,
        "focus_ipca_far": 3.0,
        "usd": dollar(),
        "groups_acc12m": [
            ("Alimentação", 4.0),
            ("Habitação", 7.0),
            ("Saúde", 2.0),
            ("Educação", 1.0),
        ],
    }
    base.update(overrides)
    return InsightInputs(**base)


def make_insight(lane: str, severity: Severity, headline: str = "h") -> Insight:
    return Insight(
        id=f"{lane}-{severity}",
        lane=lane,  # type: ignore[arg-type]
        severity=severity,
        headline=headline,
        title="t",
        meaning="m",
        tip="t",
        evidence=[],
        rule="r",
    )


# ---- Formatação -----------------------------------------------------------------------------------------------


def test_formatacao_brasileira_de_numeros():
    assert pt(1234.5) == "1.234,50"
    assert pt(-3.14159) == "−3,14"
    assert pt(0.0) == "0,00"
    assert pt(-0.001) == "0,00"  # negativo que arredonda para zero não ganha sinal
    assert pct(4.5) == "4,50%"
    assert signed(2.0) == "+2,00"
    assert signed(-1.0) == "−1,00"
    assert month_label("2026-09") == "set/2026"


# ---- Juro real ------------------------------------------------------------------------------------------------


def test_juro_real_alto_e_atencao():
    insight = real_rate_insight(make_inputs(selic=15.0, focus_ipca_12m_ahead=4.0))

    assert insight.severity == "atencao"
    assert insight.lane == "juros"
    assert "alto" in insight.headline


def test_juro_real_intermediario_e_neutro():
    insight = real_rate_insight(make_inputs(selic=10.0, focus_ipca_12m_ahead=4.0))

    assert insight.severity == "neutro"


def test_juro_real_baixo_e_positivo():
    insight = real_rate_insight(make_inputs(selic=10.0, focus_ipca_12m_ahead=9.0))

    assert insight.severity == "positivo"
    assert "baixo" in insight.headline


# ---- Meta de inflação -----------------------------------------------------------------------------------------


def test_ipca_acima_do_teto_e_atencao():
    # Teto = 3,0 + 1,5 = 4,5; piso = 1,5; "bem acima" começa em 6,0.
    insight = inflation_target_insight(make_inputs(ipca12m=5.5))

    assert insight.severity == "atencao"
    assert "acima do teto" in insight.headline


def test_ipca_bem_acima_do_teto_e_alerta_e_conta_meses():
    insight = inflation_target_insight(make_inputs(ipca12m=7.0, months_above_ceiling=3))

    assert insight.severity == "alerta"
    assert "são 3 meses" in insight.meaning


def test_ipca_abaixo_do_piso_e_atencao():
    insight = inflation_target_insight(make_inputs(ipca12m=1.0))

    assert insight.severity == "atencao"
    assert "abaixo do piso" in insight.headline


def test_ipca_perto_do_centro_e_positivo():
    insight = inflation_target_insight(make_inputs(ipca12m=3.2))

    assert insight.severity == "positivo"


def test_ipca_dentro_da_banda_longe_do_centro_e_neutro():
    insight = inflation_target_insight(make_inputs(ipca12m=4.0))

    assert insight.severity == "neutro"


# ---- Focus: Selic --------------------------------------------------------------------------------------------


def test_selic_direcao_espera_cortes_e_e_sempre_neutra():
    insight = selic_direction_insight(make_inputs(selic=14.25, focus_selic_year_end=12.0))

    assert insight.severity == "neutro"
    assert "espera cortes" in insight.meaning


def test_selic_direcao_espera_alta():
    insight = selic_direction_insight(make_inputs(selic=14.25, focus_selic_year_end=16.0))

    assert insight.severity == "neutro"
    assert "espera alta" in insight.meaning


def test_selic_direcao_estabilidade_dentro_de_10_centesimos():
    insight = selic_direction_insight(make_inputs(selic=14.25, focus_selic_year_end=14.30))

    assert "espera estabilidade" in insight.meaning


# ---- Câmbio ---------------------------------------------------------------------------------------------------


def test_dolar_variacao_diaria_acima_de_5_por_cento_e_alerta():
    insight = dollar_insight(make_inputs(usd=dollar(last=5.5, previous=5.0)))

    assert insight.severity == "alerta"
    assert "no dia" in insight.headline


def test_dolar_variacao_diaria_entre_3_e_5_por_cento_e_atencao():
    insight = dollar_insight(make_inputs(usd=dollar(last=5.175, previous=5.0)))

    assert insight.severity == "atencao"


def test_dolar_percentil_alto_sem_salto_e_atencao():
    insight = dollar_insight(make_inputs(usd=dollar(percentile=95.0)))

    assert insight.severity == "atencao"


def test_dolar_dentro_da_banda_e_positivo():
    insight = dollar_insight(make_inputs(usd=dollar(last=5.5, ma90=5.5, sd90=0.1)))

    assert insight.severity == "positivo"
    assert "estável" in insight.headline


def test_dolar_abaixo_da_banda_e_neutro():
    insight = dollar_insight(make_inputs(usd=dollar(last=5.0, previous=5.0, ma90=5.5, sd90=0.1)))

    assert insight.severity == "neutro"


def test_dolar_mostra_conferencia_independente_quando_existe():
    import datetime as dt

    with_cross = dollar_insight(make_inputs(usd=dollar(cross=(dt.date(2026, 10, 23), 5.4321))))
    without = dollar_insight(make_inputs(usd=dollar(cross=None)))

    assert any("BCE" in e.label for e in with_cross.evidence)
    assert not any("BCE" in e.label for e in without.evidence)


# ---- Grupos e expectativas ------------------------------------------------------------------------------------


def test_grupo_com_maior_pressao_acima_de_6_por_cento_e_atencao():
    insight = groups_insight(make_inputs())

    assert insight.severity == "atencao"
    assert insight.headline == "Maior pressão: Habitação (7,00%)"
    assert [e.label for e in insight.evidence] == ["Habitação", "Alimentação", "Saúde"]


def test_grupos_sem_pressao_alta_sao_neutros():
    insight = groups_insight(
        make_inputs(groups_acc12m=[("A", 4.0), ("B", 5.0)]),
    )

    assert insight.severity == "neutro"


def test_expectativas_ancoradas_perto_do_centro_sao_positivas():
    insight = anchoring_insight(make_inputs(focus_ipca_far=3.1))

    assert insight.severity == "positivo"
    assert "ancoradas" in insight.headline


def test_expectativas_dentro_da_banda_longe_do_centro_sao_neutras():
    insight = anchoring_insight(make_inputs(focus_ipca_far=3.8))

    assert insight.severity == "neutro"


def test_expectativas_fora_da_banda_sao_desancoradas_e_atencao():
    insight = anchoring_insight(make_inputs(focus_ipca_far=5.0))

    assert insight.severity == "atencao"
    assert "desancoradas" in insight.headline


# ---- Semáforo e ordenação -------------------------------------------------------------------------------------


def test_semaforo_geral_e_pior_estado_entre_as_frentes():
    insights = [
        make_insight("juros", "neutro"),
        make_insight("inflacao", "atencao", headline="IPCA em atenção"),
        make_insight("inflacao", "positivo"),
        make_insight("cambio", "positivo"),
    ]

    macro = build_macro(insights)

    assert macro.severity == "atencao"
    assert macro.label == "Cenário em atenção"
    assert macro.summary == "1 de 3 frentes pedem atenção: inflação."
    lanes = {lane.id: lane for lane in macro.lanes}
    assert lanes["inflacao"].severity == "atencao"
    assert lanes["inflacao"].headline == "IPCA em atenção"
    assert lanes["cambio"].severity == "positivo"


def test_semaforo_com_alerta_em_uma_frente_vira_alerta():
    macro = build_macro(
        [
            make_insight("juros", "positivo"),
            make_insight("inflacao", "neutro"),
            make_insight("cambio", "alerta"),
        ]
    )

    assert macro.severity == "alerta"
    assert macro.label == "Cenário em alerta"


def test_semaforo_sem_frentes_em_atencao_fica_calmo_ou_estavel():
    macro = build_macro(
        [
            make_insight("juros", "positivo"),
            make_insight("inflacao", "neutro"),
            make_insight("cambio", "positivo"),
        ]
    )

    assert macro.severity == "neutro"
    assert macro.summary == "Nenhuma das três frentes pede atenção no momento."


def test_build_insights_ordena_do_mais_grave_para_o_menos_grave():
    insights = build_insights(make_inputs(ipca12m=7.0, months_above_ceiling=2))

    ranks = [SEVERITY_ORDER.index(i.severity) for i in insights]
    assert ranks == sorted(ranks, reverse=True)
    assert insights[0].severity == "alerta"
    assert {i.id for i in insights} == {
        "juro-real",
        "ipca-meta",
        "selic-direcao",
        "dolar",
        "ipca-grupos",
        "expectativas",
    }
