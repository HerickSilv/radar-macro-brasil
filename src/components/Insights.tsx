import type { Insight } from '../lib/schema';
import { Section, SeverityTag } from './ui';

const LANE_LABEL: Record<Insight['lane'], string> = {
  juros: 'Juros',
  inflacao: 'Inflação',
  cambio: 'Câmbio',
};

function InsightCard({ insight }: { insight: Insight }) {
  return (
    <article className="flex flex-col gap-4 border-t border-rule pt-6">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <span className="font-medium text-ink-2">{LANE_LABEL[insight.lane]}</span>
        <SeverityTag severity={insight.severity} />
      </div>
      <h3 className="font-display text-2xl leading-snug font-semibold text-balance">{insight.title}</h3>
      <p className="num text-base font-medium text-ink">{insight.headline}</p>
      <p className="text-base leading-relaxed text-ink-2">{insight.meaning}</p>
      <p className="text-sm leading-relaxed text-ink-2">
        <span className="font-semibold text-ink">Na prática: </span>
        {insight.tip}
      </p>
      <dl className="m-0 grid grid-cols-[1fr_auto] gap-x-6 gap-y-2 text-sm">
        {insight.evidence.map((e) => (
          <div key={e.label} className="contents">
            <dt className="text-ink-2">{e.label}</dt>
            <dd className="m-0 text-right font-semibold num">{e.value}</dd>
          </div>
        ))}
      </dl>
      <details className="text-sm text-muted">
        <summary className="cursor-pointer font-medium text-ink-2 underline decoration-rule decoration-2 underline-offset-4 hover:text-ink">
          Como essa leitura é calculada
        </summary>
        <p className="mt-2 leading-relaxed">{insight.rule}</p>
      </details>
    </article>
  );
}

export function InsightsSection({ insights }: { insights: Insight[] }) {
  return (
    <Section
      id="leituras"
      title="O que isso significa"
      lead="Cada leitura mostra a evidência e a regra usada. São orientações educativas e gerais: não são recomendação de investimento."
    >
      {insights.length === 0 ? (
        <p className="text-ink-2">Nenhuma leitura disponível neste momento.</p>
      ) : (
        <div className="grid grid-cols-1 gap-x-12 gap-y-4 md:grid-cols-2">
          {insights.map((i) => (
            <InsightCard key={i.id} insight={i} />
          ))}
        </div>
      )}
    </Section>
  );
}
