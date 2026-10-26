import { describe, expect, it } from 'vitest';
import macroJson from '../../public/data/macro.json';
import { parseSnapshot } from './load';
import { SnapshotSchema } from './schema';

// Fixture: o próprio snapshot publicado pelo ETL (dado real, não inventado).
const real = structuredClone(macroJson) as unknown;

describe('contrato do macro.json', () => {
  it('aceita o snapshot real publicado pelo ETL', () => {
    const r = SnapshotSchema.safeParse(real);
    expect(r.success, r.success ? '' : JSON.stringify(r.error.issues.slice(0, 3))).toBe(true);
  });

  it('rejeita campo desconhecido no nível de topo (extra=forbid do ETL)', () => {
    const bad = { ...(real as object), surprise: 1 };
    expect(SnapshotSchema.safeParse(bad).success).toBe(false);
  });

  it('rejeita tipo errado dentro de uma série', () => {
    const bad = structuredClone(real) as { series: { selic: { v: unknown }[] } };
    const first = bad.series.selic[0];
    if (first) first.v = 'treze';
    expect(SnapshotSchema.safeParse(bad).success).toBe(false);
  });
});

describe('parseSnapshot: degradação por seção', () => {
  it('uma seção inválida não derruba as demais', () => {
    const bad = structuredClone(real) as Record<string, unknown>;
    bad['insights'] = [{ id: 'x' }];
    const loaded = parseSnapshot(bad);
    expect(loaded.status).toBe('ready');
    if (loaded.status !== 'ready') return;
    expect(loaded.sections.insights.ok).toBe(false);
    expect(loaded.sections.kpis.ok).toBe(true);
    expect(loaded.sections.series.ok).toBe(true);
  });

  it('sem metadados não há como mostrar data nem fonte, então é erro total', () => {
    const bad = structuredClone(real) as Record<string, unknown>;
    delete bad['meta'];
    expect(parseSnapshot(bad).status).toBe('error');
  });

  it('não é objeto JSON: erro com mensagem', () => {
    const loaded = parseSnapshot([1, 2]);
    expect(loaded.status).toBe('error');
  });
});
