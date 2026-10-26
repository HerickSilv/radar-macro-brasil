"""Contrato de dados do Radar Macro Brasil.

Estes modelos Pydantic são a **fonte única** do formato de `macro.json`. Deles saem:
  * a validação do snapshot antes de publicar (o ETL falha se algo estiver fora do contrato);
  * `schema/macro.schema.json` (JSON Schema), do qual o front gera o schema Zod.

Convenções: chaves em camelCase no JSON; datas ISO (`YYYY-MM-DD`); séries mensais usam o dia 1 do mês de referência.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = 1

Severity = Literal["positivo", "neutro", "atencao", "alerta"]
LaneId = Literal["juros", "inflacao", "cambio"]
KpiId = Literal["selic", "cdi", "ipca12m", "usd"]
FocusIndicator = Literal["IPCA", "Selic", "Câmbio", "PIB Total"]

# Ordem crescente de gravidade: usada para "pior estado" nas frentes e no semáforo.
SEVERITY_ORDER: tuple[Severity, ...] = ("positivo", "neutro", "atencao", "alerta")


class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Point(Model):
    d: date
    v: float


class DollarPoint(Model):
    """PTAX de venda com média móvel de 90 dias e banda de ±1 desvio-padrão (nulos no início da janela)."""

    d: date
    v: float
    ma90: float | None
    lo: float | None
    hi: float | None


class Source(Model):
    id: str
    name: str
    url: str
    last_observation: date


class Kpi(Model):
    id: KpiId
    label: str
    value: float
    unit: Literal["% a.a.", "R$"]
    as_of: date
    delta: float
    delta_unit: Literal["p.p.", "%"]
    delta_label: str
    # True/False quando "subir" é bom/ruim para o leitor; None quando é neutro (ex.: Selic).
    up_is_good: bool | None
    spark: list[float]
    spark_label: str


class Series(Model):
    selic: list[Point]
    cdi: list[Point]
    # alias explícito: o gerador camelCase do Pydantic transformaria "ipca12m" em "ipca12M"
    ipca12m: list[Point] = Field(alias="ipca12m")
    ipca_monthly: list[Point]
    # Juro real ex-post: (1 + Selic no fim do mês) / (1 + IPCA 12m) - 1
    real_rate: list[Point]
    usd: list[DollarPoint]


class FocusItem(Model):
    indicator: FocusIndicator
    year: int
    median: float
    mean: float
    minimum: float
    maximum: float
    respondents: int
    previous_median: float | None
    previous_date: date | None


class Focus(Model):
    as_of: date
    items: list[FocusItem]
    # Mediana suavizada da expectativa de IPCA para os próximos 12 meses
    ipca_12m_ahead: float = Field(alias="ipca12mAhead")


class IpcaGroup(Model):
    id: str
    name: str
    monthly: list[float | None]
    acc12m: float | None = Field(alias="acc12m")


class IpcaGroups(Model):
    months: list[str]  # "YYYY-MM"
    general: IpcaGroup
    groups: list[IpcaGroup]


class Evidence(Model):
    label: str
    value: str


class Insight(Model):
    id: str
    lane: LaneId
    severity: Severity
    headline: str
    title: str
    meaning: str
    tip: str
    evidence: list[Evidence]
    rule: str


class Lane(Model):
    id: LaneId
    label: str
    severity: Severity
    headline: str


class Macro(Model):
    severity: Severity
    label: str
    summary: str
    lanes: list[Lane]
    rule: str


class Targets(Model):
    inflation_center: float
    inflation_tolerance: float


class Meta(Model):
    schema_version: Literal[1]
    generated_at: datetime
    as_of: date
    sources: list[Source]


class MacroSnapshot(Model):
    meta: Meta
    kpis: list[Kpi]
    series: Series
    focus: Focus
    ipca_groups: IpcaGroups
    targets: Targets
    macro: Macro
    insights: list[Insight]


def json_schema() -> dict:
    """JSON Schema do contrato (como serializado: camelCase)."""
    return MacroSnapshot.model_json_schema(by_alias=True, mode="serialization")
