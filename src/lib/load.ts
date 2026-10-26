// Carrega o snapshot estático. Cada seção é validada à parte: se uma falhar, só ela degrada.
// Só o meta é obrigatório; sem ele não há como dizer "atualizado em" nem a fonte, então a página
// mostra o estado de erro em vez de publicar dado sem data.
import { type ZodType, z } from 'zod';
import { MetaSchema, SECTION_SCHEMAS, type Meta, type Snapshot } from './schema';

export type Section<T> = { ok: true; data: T } | { ok: false; reason: string };

export type SectionKey = keyof typeof SECTION_SCHEMAS;

export type Loaded =
  | { status: 'error'; message: string }
  | { status: 'ready'; meta: Meta; sections: { [K in SectionKey]: Section<Snapshot[K]> } };

export const DATA_PATH = 'data/macro.json';

function describe(error: z.ZodError): string {
  const first = error.issues[0];
  if (!first) return 'formato inesperado';
  const where = first.path.length > 0 ? first.path.join('.') : 'raiz';
  return `${where}: ${first.message}`;
}

function pick<T>(schema: ZodType<T>, raw: unknown): Section<T> {
  const parsed = schema.safeParse(raw);
  return parsed.success ? { ok: true, data: parsed.data } : { ok: false, reason: describe(parsed.error) };
}

export function parseSnapshot(raw: unknown): Loaded {
  const top = z.looseObject({ meta: z.unknown() }).safeParse(raw);
  if (!top.success) return { status: 'error', message: 'o arquivo não é um objeto JSON' };
  const meta = MetaSchema.safeParse(top.data.meta);
  if (!meta.success) return { status: 'error', message: `metadados inválidos (${describe(meta.error)})` };

  const obj = raw as Record<string, unknown>;
  const sections = {
    kpis: pick(SECTION_SCHEMAS.kpis, obj["kpis"]),
    series: pick(SECTION_SCHEMAS.series, obj["series"]),
    focus: pick(SECTION_SCHEMAS.focus, obj["focus"]),
    ipcaGroups: pick(SECTION_SCHEMAS.ipcaGroups, obj["ipcaGroups"]),
    targets: pick(SECTION_SCHEMAS.targets, obj["targets"]),
    macro: pick(SECTION_SCHEMAS.macro, obj["macro"]),
    insights: pick(SECTION_SCHEMAS.insights, obj["insights"]),
  };

  return { status: 'ready', meta: meta.data, sections };
}

export async function loadSnapshot(signal?: AbortSignal): Promise<Loaded> {
  const url = `${import.meta.env.BASE_URL}${DATA_PATH}`;
  try {
    const res = await fetch(url, { signal: signal ?? null, cache: 'no-cache' });
    if (!res.ok) return { status: 'error', message: "HTTP " + String(res.status) + " ao buscar os dados" };
    const raw: unknown = await res.json();
    return parseSnapshot(raw);
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    return { status: 'error', message: 'não foi possível ler o arquivo de dados' };
  }
}
