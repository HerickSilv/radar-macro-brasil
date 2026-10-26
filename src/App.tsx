import { useEffect, useState } from 'react';
import { loadSnapshot, type Loaded } from './lib/load';
import { Degraded, Section } from './components/ui';
import { Masthead, KpiBand, Verdict } from './components/Overview';
import { FxSection, GroupsSection, InflationSection, RatesSection } from './components/Trends';
import { InsightsSection } from './components/Insights';
import { Simulator } from './components/Simulator';
import { Footer } from './components/Footer';

export function App() {
  const [state, setState] = useState<Loaded | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    loadSnapshot(ctrl.signal)
      .then((result) => {
        setState(result);
      })
      .catch((err: unknown) => {
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          setState({ status: 'error', message: 'falha inesperada ao carregar o painel' });
        }
      });
    return () => {
      ctrl.abort();
    };
  }, [attempt]);

  if (state === null) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-24 sm:px-6">
        <p role="status" className="font-display text-3xl text-ink-2">
          Carregando os dados do painel…
        </p>
      </main>
    );
  }

  if (state.status === 'error') {
    return (
      <main className="mx-auto max-w-2xl px-4 py-24 sm:px-6">
        <h1 className="font-display text-4xl font-semibold">Não foi possível carregar o painel</h1>
        <p className="mt-4 text-lg text-ink-2" role="alert">
          {state.message}. Os dados são publicados por um processo automático; tente de novo em instantes.
        </p>
        <button
          type="button"
          onClick={() => {
            setState(null);
            setAttempt((n) => n + 1);
          }}
          className="mt-8 rounded-sm bg-ink px-5 py-3 font-semibold text-page hover:opacity-90"
        >
          Tentar novamente
        </button>
      </main>
    );
  }

  const { meta, sections } = state;
  const kpis = sections.kpis;
  const series = sections.series;
  const macro = sections.macro;

  const selicKpi = kpis.ok ? kpis.data.find((k) => k.id === 'selic') : undefined;
  const cdiKpi = kpis.ok ? kpis.data.find((k) => k.id === 'cdi') : undefined;
  const ipcaAhead = sections.focus.ok ? sections.focus.data.ipca12mAhead : undefined;
  const simulatorReady = selicKpi !== undefined && cdiKpi !== undefined && ipcaAhead !== undefined;

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10">
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-10 focus:rounded-sm focus:bg-ink focus:px-3 focus:py-2 focus:text-page"
      >
        Pular para o conteúdo
      </a>
      <Masthead meta={meta} />
      <main id="conteudo">
        {macro.ok ? (
          <Verdict macro={macro.data} />
        ) : (
          <Section id="cenario" title="Cenário">
            <Degraded title="Semáforo indisponível" reason={macro.reason} />
          </Section>
        )}
        {kpis.ok ? (
          <KpiBand kpis={kpis.data} />
        ) : (
          <Degraded title="Indicadores indisponíveis" reason={kpis.reason} />
        )}
        <div className="mt-6">
          <RatesSection result={series} />
          <InflationSection result={series} focus={sections.focus} targets={sections.targets} />
          <FxSection result={series} />
          <GroupsSection result={sections.ipcaGroups} />
          {sections.insights.ok ? (
            <InsightsSection insights={sections.insights.data} />
          ) : (
            <Section id="leituras" title="O que isso significa">
              <Degraded title="Leituras indisponíveis" reason={sections.insights.reason} />
            </Section>
          )}
          {simulatorReady ? (
            <Simulator selicPct={selicKpi.value} cdiAnnualPct={cdiKpi.value} ipcaPct={ipcaAhead} />
          ) : (
            <Section id="simulador" title="Simulador de renda fixa">
              <Degraded title="Simulador indisponível" reason="depende dos indicadores e do Focus, que não passaram na validação" />
            </Section>
          )}
        </div>
      </main>
      <Footer meta={meta} />
    </div>
  );
}
