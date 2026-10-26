// Cores dos gráficos vêm dos mesmos tokens CSS da página (index.css), para que claro/escuro
// valham nos dois lugares. Slots categóricos seguem a paleta validada do skill dataviz.
export interface Palette {
  page: string;
  surface: string;
  ink: string;
  ink2: string;
  muted: string;
  rule: string;
  grid: string;
  axis: string;
  s1: string;
  s2: string;
  s3: string;
  band: string;
  good: string;
  warning: string;
  serious: string;
  critical: string;
}

const TOKENS: Record<keyof Palette, string> = {
  page: '--page',
  surface: '--surface',
  ink: '--ink',
  ink2: '--ink-2',
  muted: '--muted',
  rule: '--rule',
  grid: '--grid',
  axis: '--axis',
  s1: '--s1',
  s2: '--s2',
  s3: '--s3',
  band: '--band',
  good: '--good',
  warning: '--warning',
  serious: '--serious',
  critical: '--critical',
};

export function readPalette(): Palette {
  const styles = getComputedStyle(document.documentElement);
  const out = {} as Record<keyof Palette, string>;
  for (const key of Object.keys(TOKENS) as (keyof Palette)[]) {
    out[key] = styles.getPropertyValue(TOKENS[key]).trim();
  }
  return out;
}

export const SEVERITY_VAR = {
  positivo: 'good',
  neutro: 'muted',
  atencao: 'warning',
  alerta: 'critical',
} as const;
