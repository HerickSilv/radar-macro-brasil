"""Linha de comando: `radar-etl run` gera o snapshot; `radar-etl schema` reexporta o JSON Schema do contrato."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .build import build_snapshot
from .checks import DataQualityError
from .http import Fetcher, FetchError
from .models import MacroSnapshot, json_schema

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO_ROOT / "public" / "data" / "macro.json"
DEFAULT_SCHEMA = REPO_ROOT / "schema" / "macro.schema.json"


def write_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_snapshot(snapshot: MacroSnapshot, path: Path) -> None:
    # Reabre pelo contrato: garante que o que vai para o disco é exatamente o que o modelo aceita.
    payload = snapshot.model_dump_json(by_alias=True)
    MacroSnapshot.model_validate_json(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar-etl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="coleta as fontes e escreve o snapshot JSON")
    run.add_argument("--out", type=Path, default=DEFAULT_OUT)
    run.add_argument(
        "--schema", type=Path, default=DEFAULT_SCHEMA, help="onde reexportar o JSON Schema"
    )
    run.add_argument(
        "--today",
        type=date.fromisoformat,
        help="data de referência (padrão: hoje em America/Sao_Paulo)",
    )

    schema = sub.add_parser("schema", help="exporta apenas o JSON Schema do contrato")
    schema.add_argument("--out", type=Path, default=DEFAULT_SCHEMA)

    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8"
        )  # consoles Windows (cp1252) não quebram com acentos
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.command == "schema":
        write_schema(args.out)
        print(f"schema escrito em {args.out}")
        return 0

    today = args.today or datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    fetcher = Fetcher()
    try:
        snapshot = build_snapshot(fetcher, today)
        write_snapshot(snapshot, args.out)
        write_schema(args.schema)
    except (FetchError, DataQualityError, ValueError) as exc:
        logging.getLogger("radar_etl").error("ETL falhou, nada foi publicado: %s", exc)
        return 1
    finally:
        fetcher.close()
    size_kb = args.out.stat().st_size / 1024
    print(f"snapshot escrito em {args.out} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
