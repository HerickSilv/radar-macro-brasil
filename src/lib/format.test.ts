import { describe, expect, it } from 'vitest';
import { formatBRL, formatDate, formatNumber, formatSigned } from './format';

describe('formatação pt-BR', () => {
  it('usa vírgula decimal e separador de milhar', () => {
    expect(formatNumber(13.75, 2)).toBe('13,75');
    expect(formatNumber(1234.5, 1)).toBe('1.234,5');
  });

  it('moeda em reais', () => {
    expect(formatBRL(10000)).toMatch(/^R\$\s10\.000,00$/);
  });

  it('data ISO civil não desloca o dia pelo fuso', () => {
    expect(formatDate('2026-10-26')).toBe('26 de out. de 2026');
  });

  it('sinal com menos tipográfico', () => {
    expect(formatSigned(-1, 2, ' p.p.')).toBe('−1,00 p.p.');
    expect(formatSigned(9.19, 2, '%')).toBe('+9,19%');
  });
});
