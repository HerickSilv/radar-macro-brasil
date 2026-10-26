import type { ReactNode } from 'react';
import { EChart } from './charts/EChart';
import { focusOption, fxOption, groupsOption, inflationOption, ratesOption } from './charts/options';
import type { Focus, IpcaGroups, Series, Targets } from '../lib/schema';
import type { Section as Result } from '../lib/load';
import { formatDate, formatMonth, formatNumber } from '../lib/format';
import { Caption, Degraded, DataDetails, Section } from './ui';

function Table({ caption, head, rows }: { caption: string; head: string[]; rows: ReactNode[][] }) {
  return (
    <table className="w-full border-collapse text-left text-sm">
      <caption className="sr-only">{caption}</caption>
      <thead className="sticky top-0 bg-surface">
        <tr>
          {head.map((h) => (
            <th key={h} scope="col" className="border-b border-rule px-3 py-2 font-semibold text-ink-2">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((cells, i) => (
          <tr key={i} className="border-b border-grid last:border-b-0">
            {cells.map((c, j) => (
              <td key={j} className="px-3 py-1.5 num">
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Seção que degrada sozinha: se o dado dela for inválido, mostra o motivo e o resto da página segue.
function Guarded<T>({
  id,
  title,
  lead,
  result,
  children,
}: {
  id: string;
  title: string;
  lead: string;
  result: Result<T>;
  children: (data: T) => ReactNode;
}) {
  return (
    <Section id={id} title={title} lead={lead}>
      {result.ok ? children(result.data) : <Degraded title={`${title}: dados indisponíveis`} reason={result.reason} />}
    </Section>
  );
}

export function RatesSection({ result }: { result: Result<Series> }) {
  return (
    <Guarded
      id="juros"
      title="Juros"
      lead="A Selic é a taxa básica que o Banco Central usa para conter a inflação. O juro real desconta a inflação esperada: ele mostra quanto a taxa rende acima dos preços."
      result={result}
    >
      {(s) => (
        <>
          <EChart
            label="Gráfico de linhas: Selic meta, CDI e juro real ao longo de cinco anos, em % ao ano."
            description={`Selic meta: ${formatNumber(s.selic.at(-1)?.v ?? 0, 2)}% a.a. no último ponto. Juro real: ${formatNumber(s.realRate.at(-1)?.v ?? 0, 2)}% a.a. no último mês.`}
            height={340}
            build={(p) => ratesOption(p, s.selic, s.cdi, s.realRate)}
          />
          <Caption>
            Juro real é ex-post: usa a Selic do fim de cada mês e o IPCA acumulado em 12 meses. Fonte: BCB (SGS).
          </Caption>
          <DataDetails summary="Ver os dados em tabela">
            <Table
              caption="Juro real mensal, em % ao ano"
              head={['Mês', 'Juro real (% a.a.)']}
              rows={s.realRate.map((x) => [
                formatMonth(x.d),
                formatNumber(x.v, 2),
              ])}
            />
          </DataDetails>
        </>
      )}
    </Guarded>
  );
}

export function InflationSection({
  result,
  focus,
  targets,
}: {
  result: Result<Series>;
  focus: Result<Focus>;
  targets: Result<Targets>;
}) {
  return (
    <Guarded
      id="inflacao"
      title="Inflação"
      lead="O IPCA mede a variação de preços para as famílias. A meta contínua é de 3% ao ano, com tolerância de 1,5 p.p. para cima ou para baixo. As barras mostram cada mês; a linha, o acumulado em 12 meses."
      result={result}
    >
      {(s) => (
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <div>
            {targets.ok ? (
              <EChart
                label="Gráfico de barras e linha: IPCA mensal e IPCA acumulado em 12 meses, com a faixa da meta destacada."
                description={`IPCA em 12 meses: ${formatNumber(s.ipca12m.at(-1)?.v ?? 0, 2)}% no último ponto.`}
                height={340}
                build={(p) => inflationOption(p, s.ipca12m, s.ipcaMonthly, targets.data)}
              />
            ) : (
              <Degraded title="Meta de inflação indisponível" reason={targets.reason} />
            )}
            <DataDetails summary="Ver IPCA em tabela">
              <Table
                caption="IPCA mensal e acumulado em 12 meses"
                head={['Mês', 'IPCA no mês (%)', 'IPCA 12 meses (%)']}
                rows={s.ipcaMonthly.map((m) => [
                  formatMonth(m.d),
                  formatNumber(m.v, 2),
                  (() => {
                    const acc = s.ipca12m.find((x) => x.d === m.d);
                    return acc ? formatNumber(acc.v, 2) : "—";
                  })(),
                ])}
              />
            </DataDetails>
          </div>
          <FocusBlock focus={focus} targets={targets} />
        </div>
      )}
    </Guarded>
  );
}

function FocusBlock({ focus, targets }: { focus: Result<Focus>; targets: Result<Targets> }) {
  if (!focus.ok) return <Degraded title="Expectativas (Focus) indisponíveis" reason={focus.reason} />;
  const f = focus.data;
  const ipca = f.items.filter((i) => i.indicator === 'IPCA');
  return (
    <div>
      <h3 className="font-display text-xl font-semibold">Expectativas do mercado (Boletim Focus)</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink-2">
        Mediana das projeções de IPCA por ano. A faixa vai da menor à maior projeção coletada.
      </p>
      {targets.ok ? (
        <EChart
          label="Gráfico de faixa e mediana: projeção de IPCA para 2026, 2027 e 2028 com a meta de 3%."
          description={ipca.map((i) => String(i.year) + ": mediana " + formatNumber(i.median, 2) + "%").join('; ')}
          height={260}
          build={(p) => focusOption(p, f, targets.data)}
        />
      ) : null}
      <Caption>
        Atualizado em {formatDate(f.asOf)} · {ipca[0]?.respondents ?? 0} instituições em 2026. Fonte: BCB (Olinda, Expectativas).
      </Caption>
      <DataDetails summary="Ver projeções em tabela">
        <Table
          caption="Projeções de IPCA do Focus por ano"
          head={['Ano', 'Mediana', 'Mínima', 'Máxima']}
          rows={ipca.map((i) => [
            String(i.year),
            `${formatNumber(i.median, 2)}%`,
            `${formatNumber(i.minimum, 2)}%`,
            `${formatNumber(i.maximum, 2)}%`,
          ])}
        />
      </DataDetails>
    </div>
  );
}

export function FxSection({ result }: { result: Result<Series> }) {
  return (
    <Guarded
      id="cambio"
      title="Câmbio"
      lead="Dólar PTAX de venda, a taxa de referência divulgada pelo Banco Central. A faixa mostra um desvio-padrão para cima e para baixo da média dos últimos 90 pregões."
      result={result}
    >
      {(s) => {
        const last = s.usd.at(-1);
        return (
          <>
            <EChart
              label="Gráfico de linhas: dólar PTAX de venda, média móvel de 90 pregões e faixa de ±1 desvio-padrão, em reais."
              description={last ? `PTAX em ${formatDate(last.d)}: R$ ${formatNumber(last.v, 4)}.` : 'Sem pontos.'}
              height={320}
              build={(p) => fxOption(p, s.usd)}
            />
            <DataDetails summary="Ver PTAX em tabela (últimos 60 pregões)">
              <Table
                caption="Dólar PTAX de venda, últimos pregões"
                head={['Data', 'PTAX venda (R$)', 'Média 90 pregões (R$)']}
                rows={s.usd.slice(-60).reverse().map((x) => [
                  formatDate(x.d),
                  formatNumber(x.v, 4),
                  x.ma90 === null ? '—' : formatNumber(x.ma90, 4),
                ])}
              />
            </DataDetails>
          </>
        );
      }}
    </Guarded>
  );
}

export function GroupsSection({ result }: { result: Result<IpcaGroups> }) {
  return (
    <Guarded
      id="grupos"
      title="Onde a inflação pesa"
      lead="O IPCA é uma média. Cada grupo pesa diferente no orçamento de cada família. A linha tracejada marca o índice geral."
      result={result}
    >
      {(g) => (
        <>
          <EChart
            label="Gráfico de barras horizontais: IPCA acumulado em 12 meses por grupo de produtos e serviços."
            description={g.groups
              .map((x) => `${x.name}: ${x.acc12m === null ? 'sem dado' : `${formatNumber(x.acc12m, 2)}%`}`)
              .join('; ')}
            height={340}
            build={(p) => groupsOption(p, g)}
          />
          <Caption>
            Referência: IPCA de {formatMonth(`${g.months.at(-1) ?? '1970-01'}-01`)} · fonte: IBGE, agregado 7060.
          </Caption>
        </>
      )}
    </Guarded>
  );
}
