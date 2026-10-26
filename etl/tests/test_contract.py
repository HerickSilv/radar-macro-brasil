"""Consistência entre o código, o JSON Schema publicado e o snapshot publicado (lê arquivos reais, sem rede)."""

from __future__ import annotations

import json
from pathlib import Path

from radar_etl.models import MacroSnapshot, json_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schema" / "macro.schema.json"
SNAPSHOT_PATH = REPO_ROOT / "public" / "data" / "macro.json"


def test_schema_publicado_e_igual_ao_gerado_pelo_codigo():
    published = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert published == json_schema(), (
        "schema/macro.schema.json está defasado: rode `uv run radar-etl schema` em etl/"
    )


def test_snapshot_publicado_valida_pelo_contrato():
    raw = SNAPSHOT_PATH.read_text(encoding="utf-8")

    snapshot = MacroSnapshot.model_validate_json(raw)

    assert snapshot.meta.schema_version == 1
    assert snapshot.insights, "o snapshot publicado deveria ter insights"
