import { useEffect, useRef, useState } from 'react';
import type { EChartsCoreOption } from '../../lib/echarts';
import { echarts } from '../../lib/echarts';
import { type Palette, readPalette } from '../../lib/palette';

interface Props {
  label: string;
  description: string;
  height: number;
  build: (p: Palette) => EChartsCoreOption;
}

// Re-desenha quando o tema do sistema muda (cores são lidas do CSS e passadas ao canvas).
function useThemeVersion(): number {
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      setVersion((v) => v + 1);
    };
    mql.addEventListener('change', onChange);
    return () => {
      mql.removeEventListener('change', onChange);
    };
  }, []);
  return version;
}

export function EChart({ label, description, height, build }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const version = useThemeVersion();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart = echarts.init(el, undefined, { renderer: 'canvas' });
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const option = build(readPalette());
    chart.setOption({ animation: !reduce, ...option }, true);
    const ro = new ResizeObserver(() => {
      chart.resize();
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
    // build muda a cada render; o gráfico é recriado só quando o tema muda.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version]);

  return (
    <figure className="m-0">
      <div
        ref={ref}
        role="img"
        aria-label={label}
        style={{ height }}
        className="w-full"
        data-testid="echart"
      />
      <figcaption className="sr-only">{description}</figcaption>
    </figure>
  );
}
