import type { Kpi, Macro, Meta } from '../lib/schema';
import { formatDate, formatDateTime, formatNumber, formatSigned } from '../lib/format';
import { SeverityTag } from './ui';

export function Masthead({ meta }: { meta: Meta }) {
  return (
    <header className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 border-b border-ink pb-4">
      <p className="font-display text-xl font-semibold tracking-tight">Radar Macro Brasil</p>
      <p className="text-sm text-ink-2">
        Atualizado em <time dateTime={meta.generatedAt}>{formatDateTime(meta.generatedAt)}</time>
        <span className="mx-2 text-rule" aria-hidden="true">|</span>
        Dados até {formatDate(meta.asOf)}
      </p>
    </header>
  );
}

export function Verdict({ macro }: { macro: Macro }) {
  return (
    <section aria-labelledby="verdict-title" className="grid grid-cols-1 gap-8 py-10 md:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] md:py-16">
      <div>
        <h1 id="verdict-title" className="font-display text-5xl leading-[0.95] font-semibold tracking-tight text-balance md:text-7xl">
          {macro.label}
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-relaxed text-ink-2">{macro.summary}</p>
        <p className="mt-4 max-w-xl text-sm leading-relaxed text-muted">{macro.rule}</p>
      </div>
      <ul className="m-0 self-end divide-y divide-rule border-y border-rule p-0 list-none">
        {macro.lanes.map((lane) => (
          <li key={lane.id} className="grid grid-cols-[auto_1fr] items-baseline gap-x-4 gap-y-1 py-4">
            <SeverityTag severity={lane.severity} className="col-span-2 text-sm" />
            <span className="font-display text-2xl font-semibold">{lane.label}</span>
            <span className="text-sm text-ink-2 num">{lane.headline}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Sparkline({ values, label }: { values: number[]; label: string }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 120;
  const h = 36;
  const points = values
    .map((v, i) => `${((i / (values.length - 1)) * w).toFixed(1)},${(h - ((v - min) / span) * (h - 4) - 2).toFixed(1)}`)
    .join(' ');
  return (
    <svg viewBox={"0 0 " + String(w) + " " + String(h)} className="h-9 w-full overflow-visible text-s1" role="img" aria-label={label}>
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function kpiValue(k: Kpi): string {
  if (k.unit === 'R$') return `R$ ${formatNumber(k.value, 4)}`;
  return formatNumber(k.value, 2);
}

function deltaTone(k: Kpi): string {
  if (k.upIsGood === null || k.delta === 0) return 'text-ink-2';
  const up = k.delta > 0;
  const good = up === k.upIsGood;
  return good ? 'text-good-ink' : 'text-critical-ink';
}

export function KpiBand({ kpis }: { kpis: Kpi[] }) {
  return (
    <section aria-labelledby="kpi-title" className="border-y border-ink">
      <h2 id="kpi-title" className="sr-only">Indicadores principais</h2>
      <ul className="m-0 grid list-none grid-cols-1 p-0 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k, i) => (
          <li
            key={k.id}
            className={`flex flex-col gap-3 py-6 sm:px-6 ${i > 0 ? 'lg:border-l lg:border-rule' : ''} ${i % 2 === 1 ? 'sm:border-l sm:border-rule' : ''} ${i >= 2 ? 'sm:border-t sm:border-rule lg:border-t-0' : ''} ${i > 0 ? 'border-t border-rule sm:border-t-0' : ''}`}
          >
            <p className="m-0 text-sm font-medium text-ink-2">{k.label}</p>
            <p className="m-0 flex items-baseline gap-2 font-display text-5xl font-semibold tracking-tight num">
              <span>{kpiValue(k)}</span>
              {k.unit === '% a.a.' ? <span className="text-lg font-normal text-muted">a.a.</span> : null}
            </p>
            <p className={`m-0 text-sm num ${deltaTone(k)}`}>
              {k.deltaUnit === 'p.p.'
                ? formatSigned(k.delta, 2, ' p.p.')
                : formatSigned(k.delta, 2, '%')}{' '}
              <span className="text-muted">{k.deltaLabel}</span>
            </p>
            <Sparkline values={k.spark} label={`${k.label}: ${k.sparkLabel}`} />
            <p className="m-0 text-xs text-muted">
              {k.sparkLabel} · referência {formatDate(k.asOf)}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
