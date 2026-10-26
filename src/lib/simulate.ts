// Simulador educativo de renda fixa. Premissas explícitas, sem recomendação de investimento.
// Não modela IOF, taxas de corretagem, come-cotas de fundos nem TR (não coletada pelo ETL).

export type Product = 'poupanca' | 'cdb' | 'lci';

export interface SimInput {
  principal: number; // R$
  months: number; // 1..360
  cdiPct: number; // % a.a. do CDI (ex.: 100 = 100% do CDI), usado por CDB e LCI/LCA
  selicPct: number; // Selic meta % a.a., usada na regra da poupança
  ipcaPct: number; // inflação esperada % a.a. para deflacionar o valor final
  cdiAnnualPct: number; // CDI % a.a. de referência (dado real do painel)
}

export interface ProductResult {
  product: Product;
  label: string;
  monthly: number[]; // valor bruto líquido de IR no mês m (índice 0 = aplicação)
  finalNet: number;
  grossGain: number;
  tax: number;
  taxRatePct: number;
  effectiveAnnualPct: number; // rentabilidade líquida anual equivalente
}

const POUPANCA_SELIC_THRESHOLD = 8.5;
const DAYS_PER_MONTH = 365 / 12;

// Tabela regressiva do IR sobre rendimento de CDB (dias corridos desde a aplicação).
export function cdbIncomeTaxRate(days: number): number {
  if (days <= 180) return 0.225;
  if (days <= 360) return 0.2;
  if (days <= 720) return 0.175;
  return 0.15;
}

// Poupança: com Selic acima de 8,5% a.a., rende 0,5% a.m. (+ TR, aqui assumida zero);
// abaixo disso, 70% da Selic. Isenta de IR para pessoa física.
export function poupancaMonthlyRate(selicPct: number): number {
  if (selicPct > POUPANCA_SELIC_THRESHOLD) return 0.005;
  return (0.7 * selicPct) / 100 / 12;
}

function compound(principal: number, monthlyRate: number, months: number): number[] {
  return Array.from({ length: months + 1 }, (_, m) => principal * (1 + monthlyRate) ** m);
}

// Taxa efetiva mensal a partir de % a.a. (base 252 dias úteis não é usada; juros compostos anuais).
function monthlyFromAnnual(annualPct: number): number {
  return (1 + annualPct / 100) ** (1 / 12) - 1;
}

export function simulate(input: SimInput): ProductResult[] {
  const { principal, months, cdiPct, selicPct, cdiAnnualPct } = input;
  if (!Number.isFinite(principal) || principal <= 0) throw new RangeError('valor inicial inválido');
  if (!Number.isInteger(months) || months < 1 || months > 360) throw new RangeError('prazo inválido');

  const annualCdi = cdiAnnualPct * (cdiPct / 100);

  const poup = compound(principal, poupancaMonthlyRate(selicPct), months);
  const cdbGross = compound(principal, monthlyFromAnnual(annualCdi), months);
  const lciGross = cdbGross; // mesma taxa bruta; a diferença é só o IR

  const cdbMonthly = cdbGross.map((gross, m) => {
    if (m === 0) return gross;
    const gain = gross - principal;
    const rate = cdbIncomeTaxRate(Math.round(m * DAYS_PER_MONTH));
    return principal + gain * (1 - rate);
  });
  const cdbRate = cdbIncomeTaxRate(Math.round(months * DAYS_PER_MONTH));

  const annualize = (finalNet: number) => ((finalNet / principal) ** (12 / months) - 1) * 100;

  const make = (product: Product, label: string, monthly: number[], taxRatePct: number): ProductResult => {
    const finalNet = monthly[months] ?? principal;
    const grossFinal = (product === 'cdb' ? cdbGross : product === 'lci' ? lciGross : poup)[months] ?? principal;
    return {
      product,
      label,
      monthly,
      finalNet,
      grossGain: grossFinal - principal,
      tax: (grossFinal - principal) - (finalNet - principal),
      taxRatePct,
      effectiveAnnualPct: annualize(finalNet),
    };
  };

  return [
    make('poupanca', 'Poupança', poup, 0),
    make('cdb', 'CDB pós-fixado', cdbMonthly, cdbRate * 100),
    make('lci', 'LCI / LCA', lciGross, 0),
  ];
}

// Valor de hoje: deflaciona o montante final pela inflação esperada no período.
export function realValue(nominal: number, ipcaPct: number, months: number): number {
  return nominal / (1 + ipcaPct / 100) ** (months / 12);
}
