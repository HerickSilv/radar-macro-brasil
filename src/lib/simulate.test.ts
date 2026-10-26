import { describe, expect, it } from 'vitest';
import { cdbIncomeTaxRate, poupancaMonthlyRate, realValue, simulate, type SimInput } from './simulate';

const base: SimInput = {
  principal: 10_000,
  months: 12,
  cdiPct: 100,
  selicPct: 13.75,
  ipcaPct: 4.5,
  cdiAnnualPct: 13.65,
};

describe('tabela regressiva do IR (CDB)', () => {
  it.each([
    [1, 0.225],
    [180, 0.225],
    [181, 0.2],
    [360, 0.2],
    [361, 0.175],
    [720, 0.175],
    [721, 0.15],
  ])('%i dias -> alíquota %s', (days, rate) => {
    expect(cdbIncomeTaxRate(days)).toBe(rate);
  });
});

describe('poupança', () => {
  it('acima de 8,5% de Selic rende 0,5% ao mês', () => {
    expect(poupancaMonthlyRate(13.75)).toBeCloseTo(0.005, 10);
  });
  it('abaixo de 8,5% rende 70% da Selic, em base mensal', () => {
    expect(poupancaMonthlyRate(8)).toBeCloseTo((0.7 * 8) / 100 / 12, 10);
  });
});

describe('simulate', () => {
  const [poup, cdb, lci] = simulate(base);

  it('devolve as três aplicações na ordem esperada', () => {
    expect([poup?.product, cdb?.product, lci?.product]).toEqual(['poupanca', 'cdb', 'lci']);
  });

  it('cada série começa no valor aplicado e tem prazo+1 pontos', () => {
    for (const r of [poup, cdb, lci]) {
      expect(r?.monthly).toHaveLength(13);
      expect(r?.monthly[0]).toBeCloseTo(10_000, 6);
    }
  });

  it('LCI/LCA não cobra IR e o CDB cobra a alíquota do prazo', () => {
    expect(lci?.tax).toBeCloseTo(0, 6);
    expect(cdb?.taxRatePct).toBeCloseTo(17.5, 6); // 365 dias cai na faixa de 361 a 720
    expect(cdb?.tax ?? 0).toBeGreaterThan(0);
  });

  it('CDB líquido fica abaixo da LCI de mesma taxa bruta', () => {
    expect(cdb?.finalNet ?? 0).toBeLessThan(lci?.finalNet ?? 0);
  });

  it('a taxa efetiva anual é coerente com o valor final', () => {
    const f = (cdb?.finalNet ?? 1) / 10_000;
    expect(cdb?.effectiveAnnualPct).toBeCloseTo((f - 1) * 100, 4);
  });

  it('rejeita valor e prazo inválidos', () => {
    expect(() => simulate({ ...base, principal: 0 })).toThrow(RangeError);
    expect(() => simulate({ ...base, months: 0 })).toThrow(RangeError);
    expect(() => simulate({ ...base, months: 361 })).toThrow(RangeError);
  });
});

describe('valor de hoje', () => {
  it('deflaciona pelo prazo em anos', () => {
    expect(realValue(10_450, 4.5, 12)).toBeCloseTo(10_000, 6);
  });
});
