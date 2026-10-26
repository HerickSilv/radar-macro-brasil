"""Motor de insights por regras explicáveis.

Sem IA generativa de propósito: cada insight é uma função determinística de números públicos, mostra a evidência
usada e a regra aplicada. Os textos são educativos — descrevem o cenário e como ele costuma afetar decisões, mas
nunca dizem "compre" ou "venda" nem fazem recomendação individual de investimento.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import SEVERITY_ORDER, Evidence, Insight, Lane, Macro, Severity

# ---- Limiares (documentados também em docs/design.md) -------------------------------------------------------
REAL_RATE_LOW = 3.0  # juro real ex-ante abaixo disso: baixo
REAL_RATE_HIGH = 6.0  # acima disso: alto
DOLLAR_DAILY_ATTENTION = 3.0  # |variação diária| (%) a partir da qual há atenção
DOLLAR_DAILY_ALERT = 5.0  # ... e alerta
DOLLAR_PERCENTILE_HIGH = 90.0
GROUP_PRESSURE_ATTENTION = 6.0  # IPCA 12m de um grupo acima disso (%): atenção
ANCHOR_TIGHT = 0.5  # |expectativa - centro da meta| (p.p.) até aqui: ancorada


def pt(value: float, digits: int = 2) -> str:
    """Número no formato brasileiro: 1.234,56 (e '−' tipográfico para negativos)."""
    text = f"{abs(value):,.{digits}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"−{text}" if value < 0 and float(text.replace(".", "").replace(",", ".")) != 0 else text


def pct(value: float, digits: int = 2) -> str:
    return f"{pt(value, digits)}%"


def signed(value: float, digits: int = 2) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{pt(value, digits)}"


MONTHS_PT = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def month_label(ym: str) -> str:
    """'2026-09' -> 'set/2026'."""
    return f"{MONTHS_PT[int(ym[5:7]) - 1]}/{ym[:4]}"


def worst(severities: list[Severity]) -> Severity:
    return max(severities, key=SEVERITY_ORDER.index)


@dataclass(frozen=True)
class DollarStats:
    last: float
    previous: float
    ma90: float
    sd90: float
    percentile_12m: float
    is_largest_move_12m: bool
    cross_check: tuple[date, float] | None  # (data, R$ por US$) de uma fonte independente

    @property
    def day_change_pct(self) -> float:
        return (self.last / self.previous - 1) * 100

    @property
    def pct_vs_ma(self) -> float:
        return (self.last / self.ma90 - 1) * 100


@dataclass(frozen=True)
class InsightInputs:
    selic: float
    selic_6m_ago: float
    ipca12m: float
    ipca12m_ref_month: str  # "2026-09"
    months_above_ceiling: int
    target_center: float
    target_tolerance: float
    focus_ipca_12m_ahead: float
    focus_year: int
    focus_selic_year_end: float
    focus_selic_next_year: float
    focus_ipca_far_year: int
    focus_ipca_far: float
    usd: DollarStats
    groups_acc12m: list[tuple[str, float]]  # (nome do grupo, IPCA 12m %)

    @property
    def ceiling(self) -> float:
        return self.target_center + self.target_tolerance

    @property
    def floor(self) -> float:
        return self.target_center - self.target_tolerance


# ---- Regras ---------------------------------------------------------------------------------------------------


def real_rate_insight(x: InsightInputs) -> Insight:
    real = ((1 + x.selic / 100) / (1 + x.focus_ipca_12m_ahead / 100) - 1) * 100
    if real < REAL_RATE_LOW:
        severity: Severity = "positivo"
        band = "baixo"
        meaning = (
            f"Com a Selic em {pct(x.selic)} a.a. e inflação esperada de {pct(x.focus_ipca_12m_ahead)} em 12 meses, "
            f"o juro real é de cerca de {pct(real, 1)} a.a.: relativamente baixo, o que costuma tornar o crédito "
            "mais acessível e reduzir o prêmio de quem aplica em renda fixa pós-fixada."
        )
    elif real <= REAL_RATE_HIGH:
        severity = "neutro"
        band = "moderado"
        meaning = (
            f"Com a Selic em {pct(x.selic)} a.a. e inflação esperada de {pct(x.focus_ipca_12m_ahead)} em 12 meses, "
            f"o juro real é de cerca de {pct(real, 1)} a.a.: numa faixa intermediária, que freia a demanda sem "
            "apertar tanto o crédito."
        )
    else:
        severity = "atencao"
        band = "alto"
        meaning = (
            f"A Selic de {pct(x.selic)} a.a. está bem acima da inflação esperada para os próximos 12 meses "
            f"({pct(x.focus_ipca_12m_ahead)}). Descontada a inflação, o juro real fica em cerca de {pct(real, 1)} "
            "a.a.: a renda fixa pós-fixada rende muito acima dos preços, e o crédito e o investimento ficam caros."
        )
    tip = (
        "Para comparar aplicações, olhe o rendimento acima da inflação esperada, não só a taxa nominal. "
        "Em juros reais altos, dívidas com juros variáveis pesam mais no orçamento."
        if severity == "atencao"
        else "Ao comparar aplicações e financiamentos, olhe o rendimento ou o custo acima da inflação esperada, "
        "não só a taxa nominal."
    )
    return Insight(
        id="juro-real",
        lane="juros",
        severity=severity,
        headline=f"Juro real {pct(real, 1)} a.a. · {band}",
        title="Juro real",
        meaning=meaning,
        tip=tip,
        evidence=[
            Evidence(label="Selic meta", value=f"{pct(x.selic)} a.a."),
            Evidence(label="IPCA esperado em 12 meses (Focus)", value=pct(x.focus_ipca_12m_ahead)),
            Evidence(label="Juro real ex-ante", value=f"{pct(real, 1)} a.a."),
        ],
        rule=(
            "Juro real ex-ante = (1 + Selic meta) ÷ (1 + IPCA esperado em 12 meses, mediana suavizada do Focus) − 1. "
            f"Faixas: abaixo de {pt(REAL_RATE_LOW, 0)}% baixo (positivo); de {pt(REAL_RATE_LOW, 0)}% a "
            f"{pt(REAL_RATE_HIGH, 0)}% moderado (neutro); acima de {pt(REAL_RATE_HIGH, 0)}% alto (atenção)."
        ),
    )


def inflation_target_insight(x: InsightInputs) -> Insight:
    gap = x.ipca12m - x.ceiling
    if x.ipca12m > x.ceiling + x.target_tolerance:
        severity: Severity = "alerta"
        status = "bem acima do teto"
    elif x.ipca12m > x.ceiling:
        severity = "atencao"
        status = "acima do teto"
    elif x.ipca12m < x.floor:
        severity = "atencao"
        status = "abaixo do piso"
    elif x.ipca12m <= x.target_center + 0.5:
        severity = "positivo"
        status = "perto da meta"
    else:
        severity = "neutro"
        status = "dentro da banda"
    band = f"{pt(x.floor, 1)}% a {pt(x.ceiling, 1)}%"
    if x.ipca12m > x.ceiling:
        n = x.months_above_ceiling
        streak = "é 1 mês" if n == 1 else f"são {n} meses"
        meaning = (
            f"O IPCA acumulado em 12 meses ({pct(x.ipca12m)}) está {pt(abs(gap))} p.p. acima do teto da meta "
            f"({pct(x.ceiling)}). No regime de meta contínua, o descumprimento só é formalizado se a inflação "
            f"ficar fora da banda por seis meses seguidos; até aqui {streak} consecutivo{'' if n == 1 else 's'}."
        )
        tip = (
            "Inflação perto ou acima do teto costuma deixar o Banco Central cauteloso com cortes de juros. "
            "Contratos e reajustes indexados ao IPCA acompanham esse número."
        )
    elif x.ipca12m < x.floor:
        meaning = (
            f"O IPCA em 12 meses ({pct(x.ipca12m)}) está abaixo do piso da meta ({pct(x.floor)}). Inflação muito "
            "baixa também é um desvio: pode indicar demanda fraca."
        )
        tip = "Inflação baixa dá mais espaço para queda de juros, o que muda o retorno de aplicações pós-fixadas."
    else:
        meaning = (
            f"O IPCA em 12 meses ({pct(x.ipca12m)}) está dentro da banda da meta ({band}), "
            f"{'perto do centro de ' + pct(x.target_center, 1) if severity == 'positivo' else 'na metade superior'}."
        )
        tip = "Inflação dentro da banda dá previsibilidade para reajustes e para o planejamento do orçamento."
    return Insight(
        id="ipca-meta",
        lane="inflacao",
        severity=severity,
        headline=f"IPCA 12m {pct(x.ipca12m)} · {status}",
        title="Inflação vs. meta",
        meaning=meaning,
        tip=tip,
        evidence=[
            Evidence(
                label=f"IPCA 12 meses ({month_label(x.ipca12m_ref_month)})", value=pct(x.ipca12m)
            ),
            Evidence(
                label="Meta contínua",
                value=f"{pct(x.target_center, 1)} ± {pt(x.target_tolerance, 1)} p.p. (banda {band})",
            ),
            Evidence(label="Meses seguidos acima do teto", value=str(x.months_above_ceiling)),
        ],
        rule=(
            f"Compara o IPCA acumulado em 12 meses com a meta de {pct(x.target_center, 1)} e tolerância de "
            f"±{pt(x.target_tolerance, 1)} p.p. Até {pct(x.target_center + 0.5, 1)}: perto da meta (positivo); "
            f"dentro da banda: neutro; fora da banda: atenção; mais de {pt(x.target_tolerance, 1)} p.p. além do "
            "teto: alerta."
        ),
    )


def selic_direction_insight(x: InsightInputs) -> Insight:
    gap = x.focus_selic_year_end - x.selic
    change_6m = x.selic - x.selic_6m_ago
    if gap < -0.1:
        trend = (
            f"O mercado (Boletim Focus) espera cortes: Selic em {pct(x.focus_selic_year_end)} ao fim de "
            f"{x.focus_year} ({signed(gap)} p.p. sobre hoje) e {pct(x.focus_selic_next_year)} em {x.focus_year + 1}."
        )
        headline = f"Selic {pct(x.selic)} · Focus {pct(x.focus_selic_year_end)} em {x.focus_year}"
    elif gap > 0.1:
        trend = (
            f"O mercado (Boletim Focus) espera alta: Selic em {pct(x.focus_selic_year_end)} ao fim de "
            f"{x.focus_year} ({signed(gap)} p.p. sobre hoje) e {pct(x.focus_selic_next_year)} em {x.focus_year + 1}."
        )
        headline = f"Selic {pct(x.selic)} · Focus {pct(x.focus_selic_year_end)} em {x.focus_year}"
    else:
        trend = (
            f"O mercado (Boletim Focus) espera estabilidade: Selic em {pct(x.focus_selic_year_end)} ao fim de "
            f"{x.focus_year} e {pct(x.focus_selic_next_year)} em {x.focus_year + 1}."
        )
        headline = f"Selic {pct(x.selic)} · Focus estável em {x.focus_year}"
    recent = (
        f" Nos últimos 6 meses a meta variou {signed(change_6m)} p.p."
        if abs(change_6m) >= 0.005
        else " A meta ficou inalterada nos últimos 6 meses."
    )
    return Insight(
        id="selic-direcao",
        lane="juros",
        severity="neutro",
        headline=headline,
        title="Para onde vai a Selic",
        meaning=trend + recent,
        tip=(
            "A Selic é a referência do custo do dinheiro: quando cai, o crédito tende a ficar mais barato e as "
            "aplicações pós-fixadas rendem menos; quando sobe, o contrário. As projeções mudam toda semana."
        ),
        evidence=[
            Evidence(label="Selic meta hoje", value=f"{pct(x.selic)} a.a."),
            Evidence(
                label=f"Focus: Selic fim de {x.focus_year}",
                value=f"{pct(x.focus_selic_year_end)} a.a.",
            ),
            Evidence(
                label=f"Focus: Selic fim de {x.focus_year + 1}",
                value=f"{pct(x.focus_selic_next_year)} a.a.",
            ),
            Evidence(label="Variação em 6 meses", value=f"{signed(change_6m)} p.p."),
        ],
        rule=(
            "Compara a mediana do Focus para a Selic de fim de ano com a meta atual: diferença abaixo de −0,10 p.p. "
            "indica expectativa de cortes; acima de +0,10 p.p., de alta; entre os dois, estabilidade. "
            "É informativo (neutro): não classifica a direção como boa ou ruim."
        ),
    )


def dollar_insight(x: InsightInputs) -> Insight:
    d = x.usd
    day = d.day_change_pct
    abs_day = abs(day)
    if abs_day >= DOLLAR_DAILY_ALERT:
        severity: Severity = "alerta"
    elif (
        abs_day >= DOLLAR_DAILY_ATTENTION
        or d.pct_vs_ma > 100 * d.sd90 / d.ma90
        or (d.percentile_12m >= DOLLAR_PERCENTILE_HIGH)
    ):
        severity = "atencao"
    elif d.pct_vs_ma < -100 * d.sd90 / d.ma90:
        severity = "neutro"
    else:
        severity = "positivo"

    if abs_day >= DOLLAR_DAILY_ATTENTION:
        headline = f"Dólar R$ {pt(d.last)} · {signed(day, 1)}% no dia"
    elif severity == "positivo":
        headline = f"Dólar R$ {pt(d.last)} · estável vs. média 90d"
    else:
        headline = f"Dólar R$ {pt(d.last)} · {signed(d.pct_vs_ma, 1)}% vs. média 90d"

    move_word = "alta" if day > 0 else "queda"
    parts = [
        f"A PTAX de venda fechou em R$ {pt(d.last)}, {move_word} de {pt(abs_day, 1)}% sobre o dia anterior."
    ]
    if abs_day >= DOLLAR_DAILY_ATTENTION and d.is_largest_move_12m:
        parts.append("É a maior variação diária dos últimos 12 meses.")
    parts.append(
        f"O valor está {pt(abs(d.pct_vs_ma), 1)}% {'acima' if d.pct_vs_ma >= 0 else 'abaixo'} da média de 90 dias "
        f"(R$ {pt(d.ma90)}) e no percentil {pt(d.percentile_12m, 0)} dos últimos 12 meses."
    )
    evidence = [
        Evidence(label="PTAX venda", value=f"R$ {pt(d.last, 4)}"),
        Evidence(label="Variação no dia", value=f"{signed(day)}%"),
        Evidence(label="Média móvel de 90 pregões", value=f"R$ {pt(d.ma90, 4)}"),
        Evidence(label="Percentil em 12 meses", value=pt(d.percentile_12m, 0)),
    ]
    if d.cross_check is not None:
        ref_date, ref_value = d.cross_check
        evidence.append(
            Evidence(
                label=f"Conferência independente (BCE, {ref_date:%d/%m})",
                value=f"R$ {pt(ref_value, 4)}",
            )
        )
    return Insight(
        id="dolar",
        lane="cambio",
        severity=severity,
        headline=headline,
        title="Dólar vs. média recente",
        meaning=" ".join(parts),
        tip=(
            "Dólar mais alto encarece importações, viagens e insumos cotados em dólar, com repasse gradual aos "
            "preços. Quem tem contas em dólar costuma olhar a média de algumas semanas, e não um único dia."
        ),
        evidence=evidence,
        rule=(
            f"Alerta se a variação diária da PTAX passa de {pt(DOLLAR_DAILY_ALERT, 0)}% (em módulo); atenção se passa de "
            f"{pt(DOLLAR_DAILY_ATTENTION, 0)}%, se o dólar está mais de 1 desvio-padrão acima da média de 90 pregões "
            f"ou no percentil {pt(DOLLAR_PERCENTILE_HIGH, 0)} ou mais de 12 meses; neutro se está abaixo da banda; "
            "positivo se está dentro da banda de ±1 desvio-padrão."
        ),
    )


def groups_insight(x: InsightInputs) -> Insight:
    ranked = sorted(x.groups_acc12m, key=lambda g: g[1], reverse=True)[:3]
    top_name, top_value = ranked[0]
    severity: Severity = "atencao" if top_value > GROUP_PRESSURE_ATTENTION else "neutro"
    listing = "; ".join(f"{name} ({pct(value)})" for name, value in ranked)
    return Insight(
        id="ipca-grupos",
        lane="inflacao",
        severity=severity,
        headline=f"Maior pressão: {top_name} ({pct(top_value)})",
        title="Onde a inflação pesa mais",
        meaning=(
            f"Os grupos que mais pressionam o IPCA acumulado em 12 meses são: {listing}. "
            f"O índice geral está em {pct(x.ipca12m)}."
        ),
        tip=(
            "O IPCA é uma média: cada grupo pesa de forma diferente no orçamento, e a inflação sentida por uma "
            "família depende do que ela mais consome."
        ),
        evidence=[
            Evidence(label=name, value=f"{pct(value)} em 12 meses") for name, value in ranked
        ],
        rule=(
            "Ordena os 9 grupos do IPCA (IBGE) pela variação acumulada em 12 meses e destaca os 3 maiores. "
            f"Atenção se o maior passa de {pt(GROUP_PRESSURE_ATTENTION, 0)}%; caso contrário, neutro."
        ),
    )


def anchoring_insight(x: InsightInputs) -> Insight:
    gap = x.focus_ipca_far - x.target_center
    if abs(gap) <= ANCHOR_TIGHT:
        severity: Severity = "positivo"
        status = "ancoradas"
        read = "perto do centro da meta, sinal de credibilidade da política monetária"
    elif abs(gap) <= x.target_tolerance:
        severity = "neutro"
        status = "dentro da banda"
        read = (
            "dentro da banda, mas acima do centro"
            if gap > 0
            else "dentro da banda, mas abaixo do centro"
        )
    else:
        severity = "atencao"
        status = "desancoradas"
        read = "fora da banda da meta, sinal de que o mercado duvida da convergência"
    return Insight(
        id="expectativas",
        lane="inflacao",
        severity=severity,
        headline=f"Focus {x.focus_ipca_far_year}: IPCA {pct(x.focus_ipca_far)} · {status}",
        title="Expectativas de longo prazo",
        meaning=(
            f"O mercado projeta IPCA de {pct(x.focus_ipca_far)} para {x.focus_ipca_far_year}, "
            f"{pt(abs(gap))} p.p. {'acima' if gap >= 0 else 'abaixo'} do centro da meta ({pct(x.target_center, 1)}): {read}."
        ),
        tip=(
            "Expectativas ancoradas facilitam cortes de juros sem reacender a inflação; se elas se afastam da meta, "
            "o Banco Central tende a manter os juros altos por mais tempo."
        ),
        evidence=[
            Evidence(
                label=f"Focus IPCA {x.focus_ipca_far_year} (mediana)", value=pct(x.focus_ipca_far)
            ),
            Evidence(label="Centro da meta", value=pct(x.target_center, 1)),
            Evidence(label="Distância ao centro", value=f"{signed(gap)} p.p."),
        ],
        rule=(
            f"Distância entre a mediana do Focus para o IPCA de {x.focus_ipca_far_year} e o centro da meta: até "
            f"{pt(ANCHOR_TIGHT, 1)} p.p. ancorada (positivo); até {pt(x.target_tolerance, 1)} p.p. dentro da banda "
            "(neutro); além disso, desancorada (atenção)."
        ),
    )


# ---- Semáforo macro -----------------------------------------------------------------------------------------

LANE_LABELS: dict[str, str] = {"juros": "Juros", "inflacao": "Inflação", "cambio": "Câmbio"}
MACRO_LABELS: dict[Severity, str] = {
    "positivo": "Cenário calmo",
    "neutro": "Cenário estável",
    "atencao": "Cenário em atenção",
    "alerta": "Cenário em alerta",
}
MACRO_RULE = (
    "Cada frente (juros, inflação, câmbio) herda o pior estado entre os seus insights, e o semáforo geral mostra o "
    "pior estado entre as três frentes. Escala: calmo (positivo) < estável (neutro) < atenção < alerta."
)


def build_macro(insights: list[Insight]) -> Macro:
    lanes: list[Lane] = []
    for lane_id in ("juros", "inflacao", "cambio"):
        members = [i for i in insights if i.lane == lane_id]
        severity = worst([i.severity for i in members])
        lead = max(members, key=lambda i: SEVERITY_ORDER.index(i.severity))
        lanes.append(
            Lane(id=lane_id, label=LANE_LABELS[lane_id], severity=severity, headline=lead.headline)
        )  # type: ignore[arg-type]
    overall = worst([lane.severity for lane in lanes])
    flagged = [lane.label for lane in lanes if lane.severity in ("atencao", "alerta")]
    if flagged:
        summary = f"{len(flagged)} de 3 frentes pedem atenção: {', '.join(flagged).lower()}."
    else:
        summary = "Nenhuma das três frentes pede atenção no momento."
    return Macro(
        severity=overall,
        label=MACRO_LABELS[overall],
        summary=summary,
        lanes=lanes,
        rule=MACRO_RULE,
    )


def build_insights(x: InsightInputs) -> list[Insight]:
    insights = [
        real_rate_insight(x),
        inflation_target_insight(x),
        selic_direction_insight(x),
        dollar_insight(x),
        groups_insight(x),
        anchoring_insight(x),
    ]
    # Mais grave primeiro; empates mantêm a ordem acima (sort é estável).
    return sorted(insights, key=lambda i: SEVERITY_ORDER.index(i.severity), reverse=True)
