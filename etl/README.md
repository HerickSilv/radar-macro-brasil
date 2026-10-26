# radar-etl

ETL do Radar Macro Brasil. Coleta séries públicas (BCB e IBGE), valida, calcula os insights por regras e escreve
`public/data/macro.json` (contrato definido em `src/radar_etl/models.py`, exportado para `schema/macro.schema.json`).

```bash
uv sync                       # instala dependências (Python >= 3.12)
uv run radar-etl run          # gera ../public/data/macro.json
uv run radar-etl schema       # reexporta ../schema/macro.schema.json
uv run pytest && uv run ruff check
```
