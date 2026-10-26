// Formatação pt-BR via Intl. Recebe valores já em unidade humana (ex.: 13.75 = 13,75%).
const numberFmt = (digits: number) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function formatNumber(value: number, digits = 2): string {
  return numberFmt(digits).format(value);
}

export function formatPercent(value: number, digits = 2): string {
  return `${formatNumber(value, digits)}%`;
}

export function formatSigned(value: number, digits = 2, suffix = ''): string {
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  return `${sign}${formatNumber(Math.abs(value), digits)}${suffix}`;
}

export function formatBRL(value: number, digits = 2): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

// Datas ISO (YYYY-MM-DD) são lidas como data civil, sem deslocamento de fuso.
export function parseCivilDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1));
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: 'UTC', dateStyle: 'medium' }).format(
    parseCivilDate(iso),
  );
}

export function formatMonth(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: 'UTC', month: 'short', year: '2-digit' })
    .format(parseCivilDate(iso))
    .replace('.', '');
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(iso));
}
