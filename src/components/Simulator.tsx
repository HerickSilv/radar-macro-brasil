import { useId, useMemo, useState } from 'react';
import { EChart } from './charts/EChart';
import { simulationOption } from './charts/options';
import { formatBRL, formatNumber, formatPercent } from '../lib/format';
import { realValue, simulate, type ProductResult } from '../lib/simulate';
import { Caption, Section } from './ui';

interface Props {
  selicPct: number;
  cdiAnnualPct: number;
  ipcaPct: number;
}

interface Parsed {
  principal: number;
  months: number;
  cdiPct: number;
}

function parseForm(principal: string, months: string, cdiPct: string): Parsed | string {
  const p = Number(principal.replace(',', '.'));
  const m = Number(months);
  const c = Number(cdiPct.replace(',', '.'));
  if (!Number.isFinite(p) || p <= 0 || p > 100_000_000) return 'Informe um valor inicial entre R$ 0,01 e R$ 100 milhões.';
  if (!Number.isInteger(m) || m < 1 || m > 360) return 'O prazo precisa ser um número inteiro de 1 a 360 meses.';
  if (!Number.isFinite(c) || c <= 0 || c > 200) return 'O percentual do CDI precisa estar entre 1% e 200%.';
  return { principal: p, months: m, cdiPct: c };
}

const COLORS = { poupanca: 's3', cdb: 's1', lci: 's2' } as const;

export function Simulator({ selicPct, cdiAnnualPct, ipcaPct }: Props) {
  const [principal, setPrincipal] = useState('10000');
  const [months, setMonths] = useState('24');
  const [cdiPct, setCdiPct] = useState('100');
  const ids = { p: useId(), m: useId(), c: useId(), err: useId() };

  const parsed = useMemo(() => parseForm(principal, months, cdiPct), [principal, months, cdiPct]);
  const result = useMemo<ProductResult[] | null>(() => {
    if (typeof parsed === 'string') return null;
    return simulate({
      principal: parsed.principal,
      months: parsed.months,
      cdiPct: parsed.cdiPct,
      selicPct,
      ipcaPct,
      cdiAnnualPct,
    });
  }, [parsed, selicPct, ipcaPct, cdiAnnualPct]);

  const error = typeof parsed === 'string' ? parsed : null;
  const horizon = typeof parsed === 'string' ? 1 : parsed.months;

  return (
    <Section
      id="simulador"
      title="Simulador de renda fixa"
      lead="Compare, com as taxas do dia, quanto um valor renderia na poupança, num CDB e numa LCI ou LCA. É uma conta educativa, com premissas explícitas, e não uma recomendação."
    >
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
        <form className="flex flex-col gap-5" onSubmit={(e) => {
            e.preventDefault();
          }} noValidate aria-label="Premissas da simulação">
          <div>
            <label htmlFor={ids.p} className="block text-sm font-medium text-ink-2">
              Valor inicial (R$)
            </label>
            <input
              id={ids.p}
              inputMode="decimal"
              value={principal}
              onChange={(e) => {
                setPrincipal(e.target.value);
              }}
              aria-invalid={error !== null}
              aria-describedby={error ? ids.err : undefined}
              className="mt-1.5 w-full rounded-sm border border-rule bg-surface px-3 py-2.5 text-lg num focus-visible:outline-2"
            />
          </div>
          <div>
            <label htmlFor={ids.m} className="block text-sm font-medium text-ink-2">
              Prazo (meses)
            </label>
            <input
              id={ids.m}
              inputMode="numeric"
              value={months}
              onChange={(e) => {
                setMonths(e.target.value);
              }}
              aria-invalid={error !== null}
              className="mt-1.5 w-full rounded-sm border border-rule bg-surface px-3 py-2.5 text-lg num"
            />
          </div>
          <div>
            <label htmlFor={ids.c} className="block text-sm font-medium text-ink-2">
              CDB e LCI/LCA: % do CDI
            </label>
            <input
              id={ids.c}
              inputMode="decimal"
              value={cdiPct}
              onChange={(e) => {
                setCdiPct(e.target.value);
              }}
              aria-invalid={error !== null}
              className="mt-1.5 w-full rounded-sm border border-rule bg-surface px-3 py-2.5 text-lg num"
            />
          </div>
          {error ? (
            <p id={ids.err} role="alert" className="m-0 text-sm font-medium text-critical-ink">
              {error}
            </p>
          ) : null}
          <dl className="m-0 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 border-t border-rule pt-4 text-sm">
            <dt className="text-ink-2">Selic meta usada</dt>
            <dd className="m-0 num">{formatPercent(selicPct)} a.a.</dd>
            <dt className="text-ink-2">CDI usado</dt>
            <dd className="m-0 num">{formatPercent(cdiAnnualPct)} a.a.</dd>
            <dt className="text-ink-2">IPCA esperado (Focus)</dt>
            <dd className="m-0 num">{formatPercent(ipcaPct)} a.a.</dd>
          </dl>
          <p className="m-0 text-xs leading-relaxed text-muted">
            Poupança: com Selic acima de 8,5% a.a., rende 0,5% ao mês (TR não incluída). CDB: IR regressivo sobre o
            rendimento (22,5% até 180 dias, 20% até 360, 17,5% até 720 e 15% acima). LCI/LCA: isentas de IR para pessoa
            física. Não considera IOF, taxas, come-cotas nem inflação de cada família.
          </p>
        </form>

        <div>
          {result ? (
            <>
              <EChart
                label="Gráfico de linhas: valor líquido de poupança, CDB e LCI ou LCA ao longo do prazo escolhido."
                description={result
                  .map((r) => `${r.label}: ${formatBRL(r.finalNet)} no fim do prazo`)
                  .join('; ')}
                height={300}
                build={(p) =>
                  simulationOption(
                    p,
                    horizon,
                    result.map((r) => ({ name: r.label, values: r.monthly, color: COLORS[r.product] })),
                  )
                }
              />
              <Caption>Valores líquidos de IR, em reais, no fim de cada mês do prazo.</Caption>
              <div className="mt-6 overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                  <caption className="sr-only">
                    Resultado líquido de cada aplicação no prazo simulado
                  </caption>
                  <thead>
                    <tr className="border-b border-ink">
                      <th scope="col" className="py-2 pr-3 font-semibold">Aplicação</th>
                      <th scope="col" className="py-2 pr-3 text-right font-semibold">Valor final</th>
                      <th scope="col" className="py-2 pr-3 text-right font-semibold">IR</th>
                      <th scope="col" className="py-2 pr-3 text-right font-semibold">Valor de hoje*</th>
                      <th scope="col" className="py-2 text-right font-semibold">Ao ano</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.map((r) => (
                      <tr key={r.product} className="border-b border-rule">
                        <th scope="row" className="py-3 pr-3 text-left font-semibold">
                          {r.label}
                        </th>
                        <td className="py-3 pr-3 text-right num">{formatBRL(r.finalNet)}</td>
                        <td className="py-3 pr-3 text-right num">
                          {r.tax > 0 ? formatBRL(r.tax) : 'isento'}
                        </td>
                        <td className="py-3 pr-3 text-right num">
                          {formatBRL(realValue(r.finalNet, ipcaPct, horizon))}
                        </td>
                        <td className="py-3 text-right num">{formatNumber(r.effectiveAnnualPct, 2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Caption>
                * Valor de hoje: o valor final dividido pela inflação esperada no prazo (Focus). Alíquota de IR do CDB
                neste prazo: {formatNumber(result.find((r) => r.product === 'cdb')?.taxRatePct ?? 0, 1)}%.
              </Caption>
            </>
          ) : (
            <p className="m-0 rounded-sm border border-dashed border-rule p-6 text-ink-2">
              Ajuste as premissas ao lado para ver a simulação.
            </p>
          )}
        </div>
      </div>
    </Section>
  );
}
