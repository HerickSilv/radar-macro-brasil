from __future__ import annotations

import copy
import json
from typing import Any

import pytest
from pydantic import ValidationError

from radar_etl.models import MacroSnapshot, Point


def test_aceita_payload_valido(snapshot_payload: dict[str, Any]):
    snapshot = MacroSnapshot.model_validate(snapshot_payload)

    assert snapshot.meta.schema_version == 1
    assert snapshot.kpis[0].delta_unit == "p.p."
    assert snapshot.series.ipca12m[0].v == 4.5
    assert snapshot.focus.ipca_12m_ahead == 4.2


def test_json_sai_em_camel_case(snapshot_payload: dict[str, Any]):
    snapshot = MacroSnapshot.model_validate(snapshot_payload)

    data = json.loads(snapshot.model_dump_json(by_alias=True))

    assert "schemaVersion" in data["meta"]
    assert "deltaUnit" in data["kpis"][0]
    assert "upIsGood" in data["kpis"][0]
    assert "ipcaMonthly" in data["series"]
    assert "realRate" in data["series"]
    assert "ipca12m" in data["series"]  # alias explícito, não "ipca12M"
    assert "ipca12mAhead" in data["focus"]
    assert "acc12m" in data["ipcaGroups"]["general"]
    assert "lastObservation" in data["meta"]["sources"][0]
    assert "schema_version" not in data["meta"]
    assert "ipca_monthly" not in data["series"]


def test_json_valido_volta_ao_mesmo_conteudo(snapshot_payload: dict[str, Any]):
    snapshot = MacroSnapshot.model_validate(snapshot_payload)

    again = MacroSnapshot.model_validate_json(snapshot.model_dump_json(by_alias=True))

    assert again == snapshot


def test_rejeita_campo_extra_no_topo(snapshot_payload: dict[str, Any]):
    payload = copy.deepcopy(snapshot_payload)
    payload["extra"] = 1

    with pytest.raises(ValidationError):
        MacroSnapshot.model_validate(payload)


def test_rejeita_campo_extra_aninhado(snapshot_payload: dict[str, Any]):
    payload = copy.deepcopy(snapshot_payload)
    payload["meta"]["comentario"] = "sobrando"

    with pytest.raises(ValidationError):
        MacroSnapshot.model_validate(payload)


def test_rejeita_tipo_errado(snapshot_payload: dict[str, Any]):
    payload = copy.deepcopy(snapshot_payload)
    payload["series"]["selic"][0]["v"] = "quinze"

    with pytest.raises(ValidationError):
        MacroSnapshot.model_validate(payload)


def test_rejeita_data_mal_formada(snapshot_payload: dict[str, Any]):
    payload = copy.deepcopy(snapshot_payload)
    payload["series"]["selic"][0]["d"] = "01/10/2026"

    with pytest.raises(ValidationError):
        MacroSnapshot.model_validate(payload)


def test_rejeita_versao_de_schema_diferente(snapshot_payload: dict[str, Any]):
    payload = copy.deepcopy(snapshot_payload)
    payload["meta"]["schemaVersion"] = 2

    with pytest.raises(ValidationError):
        MacroSnapshot.model_validate(payload)


def test_rejeita_severidade_fora_do_vocabulario(snapshot_payload: dict[str, Any]):
    payload = copy.deepcopy(snapshot_payload)
    payload["insights"][0]["severity"] = "grave"

    with pytest.raises(ValidationError):
        MacroSnapshot.model_validate(payload)


def test_dolar_aceita_banda_nula_no_inicio_da_janela():
    # ma90/lo/hi são obrigatórios na chave, mas podem ser null.
    ok = {"d": "2026-01-02", "v": 5.1, "ma90": None, "lo": None, "hi": None}
    from radar_etl.models import DollarPoint

    assert DollarPoint.model_validate(ok).ma90 is None
    with pytest.raises(ValidationError):
        DollarPoint.model_validate({"d": "2026-01-02", "v": 5.1})


def test_point_nao_aceita_campo_extra():
    with pytest.raises(ValidationError):
        Point.model_validate({"d": "2026-01-02", "v": 5.1, "x": 0})
