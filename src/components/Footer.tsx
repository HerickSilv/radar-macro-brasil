import type { Meta } from '../lib/schema';
import { formatDate } from '../lib/format';

export function Footer({ meta }: { meta: Meta }) {
  return (
    <footer className="border-t border-ink pt-8 pb-16 text-sm text-ink-2">
      <div className="grid grid-cols-1 gap-10 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div className="flex flex-col gap-3">
          <p className="m-0 max-w-prose leading-relaxed">
            Conteúdo educativo com dados públicos. Nada aqui é recomendação de investimento, de compra ou de venda.
            Antes de decidir, consulte um profissional habilitado.
          </p>
          <p className="m-0 text-muted">Projeto de portfólio de Herick Silva. Licença MIT.</p>
        </div>
        <div>
          <h2 className="m-0 mb-3 text-sm font-semibold text-ink">Fontes</h2>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {meta.sources.map((s) => (
              <li key={s.id} className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-ink underline decoration-rule decoration-2 underline-offset-4 hover:decoration-ink"
                >
                  {s.name}
                </a>
                <span className="text-muted num">última observação em {formatDate(s.lastObservation)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}
