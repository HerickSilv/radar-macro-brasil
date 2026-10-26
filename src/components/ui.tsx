import type { ReactNode } from 'react';
import type { Severity } from '../lib/schema';

export const SEVERITY_LABEL: Record<Severity, string> = {
  positivo: 'Calmo',
  neutro: 'Estável',
  atencao: 'Atenção',
  alerta: 'Alerta',
};

// Cor do estado (token) e cor do texto sobre a página, com contraste AA nos dois temas.
const SEVERITY_TEXT: Record<Severity, string> = {
  positivo: 'text-good-ink',
  neutro: 'text-ink-2',
  atencao: 'text-warning-ink',
  alerta: 'text-critical-ink',
};

const SEVERITY_FILL: Record<Severity, string> = {
  positivo: 'var(--good)',
  neutro: 'var(--muted)',
  atencao: 'var(--warning)',
  alerta: 'var(--critical)',
};

// Ícones desenhados (um traço só, mesma espessura): o estado nunca depende apenas de cor.
export function SeverityIcon({ severity, size = 18 }: { severity: Severity; size?: number }) {
  const stroke = 'currentColor';
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke,
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
    focusable: false,
    className: 'shrink-0',
  };
  switch (severity) {
    case 'positivo':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 12.5l2.6 2.5L16 9.5" />
        </svg>
      );
    case 'neutro':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 12h8" />
        </svg>
      );
    case 'atencao':
      return (
        <svg {...common}>
          <path d="M12 4 L21 19 H3 Z" />
          <path d="M12 10v4.5M12 17.2v.1" />
        </svg>
      );
    case 'alerta':
      return (
        <svg {...common}>
          <path d="M8.2 3h7.6L21 8.2v7.6L15.8 21H8.2L3 15.8V8.2Z" />
          <path d="M12 7.5v6M12 16.6v.1" />
        </svg>
      );
  }
}

export function SeverityTag({ severity, className = '' }: { severity: Severity; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 font-semibold ${SEVERITY_TEXT[severity]} ${className}`}>
      <SeverityIcon severity={severity} size={16} />
      <span>{SEVERITY_LABEL[severity]}</span>
    </span>
  );
}

export function severityFill(severity: Severity): string {
  return SEVERITY_FILL[severity];
}

interface SectionProps {
  id: string;
  title: string;
  lead?: string;
  children: ReactNode;
}

export function Section({ id, title, lead, children }: SectionProps) {
  return (
    <section aria-labelledby={`${id}-title`} className="border-t border-rule pt-8 pb-14 md:pt-12">
      <div className="mb-8 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] md:gap-12">
        <h2 id={`${id}-title`} className="font-display text-3xl leading-tight font-semibold tracking-tight md:text-4xl">
          {title}
        </h2>
        {lead ? <p className="max-w-prose text-base leading-relaxed text-ink-2">{lead}</p> : null}
      </div>
      {children}
    </section>
  );
}

export function Degraded({ title, reason }: { title: string; reason: string }) {
  return (
    <div role="status" className="rounded-sm border border-dashed border-rule p-5 text-sm text-ink-2">
      <p className="font-semibold text-ink">{title}</p>
      <p className="mt-1">
        Esta seção não pôde ser exibida porque o dado publicado não passou na validação ({reason}). O restante
        do painel continua disponível.
      </p>
    </div>
  );
}

export function Caption({ children }: { children: ReactNode }) {
  return <p className="mt-3 text-sm leading-relaxed text-muted">{children}</p>;
}

// Tabela alternativa aos gráficos: mesma informação, legível por leitor de tela e por quem prefere números.
export function DataDetails({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="group mt-4">
      <summary className="cursor-pointer text-sm font-medium text-ink-2 underline decoration-rule decoration-2 underline-offset-4 hover:text-ink">
        {summary}
      </summary>
      <div className="mt-3 max-h-80 overflow-auto rounded-sm border border-rule">{children}</div>
    </details>
  );
}
