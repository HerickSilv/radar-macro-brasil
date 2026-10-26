// Espelho Zod do contrato Python (etl/src/radar_etl/models.py). Mantido à mão e travado por teste
// contra public/data/macro.json; o schema JSON publicado fica em schema/macro.schema.json.
import { z } from 'zod';

const isoDate = z.iso.date();
const num = z.number();

const point = z.strictObject({ d: isoDate, v: num });

const dollarPoint = z.strictObject({
  d: isoDate,
  v: num,
  ma90: num.nullable(),
  lo: num.nullable(),
  hi: num.nullable(),
});

const severity = z.enum(['positivo', 'neutro', 'atencao', 'alerta']);
const laneId = z.enum(['juros', 'inflacao', 'cambio']);

export const SEVERITY_ORDER = ['positivo', 'neutro', 'atencao', 'alerta'] as const;
export type Severity = z.infer<typeof severity>;
export type LaneId = z.infer<typeof laneId>;

const source = z.strictObject({
  id: z.string(),
  name: z.string(),
  url: z.url(),
  lastObservation: isoDate,
});

export const MetaSchema = z.strictObject({
  schemaVersion: z.literal(1),
  generatedAt: z.iso.datetime({ offset: true, local: true }),
  asOf: isoDate,
  sources: z.array(source),
});

const kpi = z.strictObject({
  id: z.enum(['selic', 'cdi', 'ipca12m', 'usd']),
  label: z.string(),
  value: num,
  unit: z.enum(['% a.a.', 'R$']),
  asOf: isoDate,
  delta: num,
  deltaUnit: z.enum(['p.p.', '%']),
  deltaLabel: z.string(),
  upIsGood: z.boolean().nullable(),
  spark: z.array(num),
  sparkLabel: z.string(),
});

const series = z.strictObject({
  selic: z.array(point),
  cdi: z.array(point),
  ipca12m: z.array(point),
  ipcaMonthly: z.array(point),
  realRate: z.array(point),
  usd: z.array(dollarPoint),
});

const focusItem = z.strictObject({
  indicator: z.enum(['IPCA', 'Selic', 'Câmbio', 'PIB Total']),
  year: z.number().int(),
  median: num,
  mean: num,
  minimum: num,
  maximum: num,
  respondents: z.number().int().nonnegative(),
  previousMedian: num.nullable(),
  previousDate: isoDate.nullable(),
});

const focus = z.strictObject({
  asOf: isoDate,
  items: z.array(focusItem),
  ipca12mAhead: num,
});

const ipcaGroup = z.strictObject({
  id: z.string(),
  name: z.string(),
  monthly: z.array(num.nullable()),
  acc12m: num.nullable(),
});

const ipcaGroups = z.strictObject({
  months: z.array(z.string().regex(/^\d{4}-\d{2}$/)),
  general: ipcaGroup,
  groups: z.array(ipcaGroup),
});

const insight = z.strictObject({
  id: z.string(),
  lane: laneId,
  severity,
  headline: z.string(),
  title: z.string(),
  meaning: z.string(),
  tip: z.string(),
  evidence: z.array(z.strictObject({ label: z.string(), value: z.string() })),
  rule: z.string(),
});

const lane = z.strictObject({ id: laneId, label: z.string(), severity, headline: z.string() });

const macro = z.strictObject({
  severity,
  label: z.string(),
  summary: z.string(),
  lanes: z.array(lane),
  rule: z.string(),
});

const targets = z.strictObject({ inflationCenter: num, inflationTolerance: num });

export const SECTION_SCHEMAS = {
  kpis: z.array(kpi),
  series,
  focus,
  ipcaGroups,
  targets,
  macro,
  insights: z.array(insight),
} as const;

export const SnapshotSchema = z.strictObject({
  meta: MetaSchema,
  ...SECTION_SCHEMAS,
});

export type Meta = z.infer<typeof MetaSchema>;
export type Kpi = z.infer<typeof kpi>;
export type Point = z.infer<typeof point>;
export type DollarPoint = z.infer<typeof dollarPoint>;
export type Series = z.infer<typeof series>;
export type FocusItem = z.infer<typeof focusItem>;
export type Focus = z.infer<typeof focus>;
export type IpcaGroup = z.infer<typeof ipcaGroup>;
export type IpcaGroups = z.infer<typeof ipcaGroups>;
export type Insight = z.infer<typeof insight>;
export type Macro = z.infer<typeof macro>;
export type Targets = z.infer<typeof targets>;
export type Snapshot = z.infer<typeof SnapshotSchema>;
