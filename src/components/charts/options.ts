// Construtores puros de opções ECharts. Recebem dados já validados e a paleta do tema.
import type { EChartsCoreOption } from '../../lib/echarts';
import { formatNumber, parseCivilDate } from '../../lib/format';
import type { Palette } from '../../lib/palette';
import type { DollarPoint, Focus, IpcaGroups, Point, Targets } from '../../lib/schema';

const ts = (iso: string) => parseCivilDate(iso).getTime();

function baseOption(p: Palette, extra: Record<string, unknown> = {}): EChartsCoreOption {
  return {
    backgroundColor: 'transparent',
    textStyle: { color: p.ink2, fontFamily: 'Inter Variable, system-ui, sans-serif' },
    tooltip: {
      trigger: 'axis',
      backgroundColor: p.surface,
      borderColor: p.rule,
      textStyle: { color: p.ink, fontSize: 13 },
      confine: true,
    },
    legend: {
      top: 0,
      left: 0,
      icon: 'roundRect',
      itemWidth: 14,
      itemHeight: 3,
      textStyle: { color: p.ink2, fontSize: 12 },
    },
    grid: { left: 44, right: 14, top: 40, bottom: 28 },
    ...extra,
  };
}

const timeAxis = (p: Palette) => ({
  type: 'time' as const,
  axisLine: { lineStyle: { color: p.axis } },
  axisLabel: { color: p.muted, fontSize: 12, hideOverlap: true },
  splitLine: { show: false },
});

const valueAxis = (p: Palette, unit: string, min?: number | 'dataMin') => ({
  type: 'value' as const,
  min,
  axisLine: { show: false },
  axisLabel: {
    color: p.muted,
    fontSize: 12,
    formatter: (v: number) => `${formatNumber(v, 1)}${unit}`,
  },
  splitLine: { lineStyle: { color: p.grid } },
});

const pctTooltip = (suffix: string) => (v: unknown) =>
  typeof v === 'number' ? `${formatNumber(v, 2)}${suffix}` : '—';

export function ratesOption(p: Palette, selic: Point[], cdi: Point[], realRate: Point[]): EChartsCoreOption {
  return baseOption(p, {
    tooltip: {
      trigger: 'axis',
      backgroundColor: p.surface,
      borderColor: p.rule,
      textStyle: { color: p.ink, fontSize: 13 },
      valueFormatter: pctTooltip('% a.a.'),
    },
    xAxis: timeAxis(p),
    yAxis: valueAxis(p, '%'),
    series: [
      {
        name: 'Selic meta',
        type: 'line',
        showSymbol: false,
        lineStyle: { width: 2.5, color: p.s1 },
        itemStyle: { color: p.s1 },
        data: selic.map((x) => [ts(x.d), x.v]),
      },
      {
        name: 'CDI',
        type: 'line',
        showSymbol: false,
        lineStyle: { width: 1.5, type: 'dashed', color: p.ink2 },
        itemStyle: { color: p.ink2 },
        data: cdi.map((x) => [ts(x.d), x.v]),
      },
      {
        name: 'Juro real',
        type: 'line',
        showSymbol: true,
        symbolSize: 5,
        lineStyle: { width: 2, color: p.s2 },
        itemStyle: { color: p.s2 },
        data: realRate.map((x) => [ts(x.d), x.v]),
      },
    ],
  });
}

export function inflationOption(
  p: Palette,
  ipca12m: Point[],
  monthly: Point[],
  targets: Targets,
): EChartsCoreOption {
  const low = targets.inflationCenter - targets.inflationTolerance;
  const high = targets.inflationCenter + targets.inflationTolerance;
  return baseOption(p, {
    tooltip: {
      trigger: 'axis',
      backgroundColor: p.surface,
      borderColor: p.rule,
      textStyle: { color: p.ink, fontSize: 13 },
      valueFormatter: pctTooltip('%'),
    },
    xAxis: timeAxis(p),
    yAxis: valueAxis(p, '%'),
    series: [
      {
        name: 'IPCA no mês',
        type: 'bar',
        barMaxWidth: 14,
        itemStyle: { color: p.axis, borderRadius: [3, 3, 0, 0] },
        data: monthly.map((x) => [ts(x.d), x.v]),
        markArea: {
          silent: true,
          itemStyle: { color: p.band },
          data: [[{ yAxis: low }, { yAxis: high }]],
        },
      },
      {
        name: 'IPCA em 12 meses',
        type: 'line',
        showSymbol: false,
        lineStyle: { width: 2.5, color: p.s2 },
        itemStyle: { color: p.s2 },
        data: ipca12m.map((x) => [ts(x.d), x.v]),
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: p.ink2, type: 'dashed', width: 1 },
          label: {
            formatter: `centro da meta ${formatNumber(targets.inflationCenter, 1)}%`,
            color: p.ink2,
            fontSize: 11,
          },
          data: [{ yAxis: targets.inflationCenter }],
        },
      },
    ],
  });
}

export function focusOption(p: Palette, focus: Focus, targets: Targets): EChartsCoreOption {
  const ipca = focus.items.filter((i) => i.indicator === 'IPCA');
  return baseOption(p, {
    legend: { show: false },
    tooltip: {
      trigger: 'axis',
      backgroundColor: p.surface,
      borderColor: p.rule,
      textStyle: { color: p.ink, fontSize: 13 },
    },
    grid: { left: 44, right: 16, top: 16, bottom: 30 },
    xAxis: {
      type: 'category',
      data: ipca.map((i) => String(i.year)),
      axisLine: { lineStyle: { color: p.axis } },
      axisLabel: { color: p.ink2, fontSize: 13 },
      axisTick: { show: false },
    },
    yAxis: valueAxis(p, '%', 0),
    series: [
      {
        name: 'mínimo',
        type: 'bar',
        stack: 'faixa',
        silent: true,
        itemStyle: { color: 'transparent' },
        data: ipca.map((i) => i.minimum),
      },
      {
        name: 'faixa das projeções',
        type: 'bar',
        stack: 'faixa',
        barWidth: 26,
        itemStyle: { color: p.band, borderRadius: 4 },
        data: ipca.map((i) => i.maximum - i.minimum),
      },
      {
        name: 'mediana',
        type: 'line',
        symbol: 'circle',
        symbolSize: 11,
        lineStyle: { color: p.s2, width: 0 },
        itemStyle: { color: p.s2 },
        label: {
          show: true,
          position: 'right',
          color: p.ink,
          fontSize: 13,
          fontWeight: 600,
          formatter: (params: { value: unknown }) => `${formatNumber(Number(params.value), 2)}%`,
        },
        data: ipca.map((i) => i.median),
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: p.ink2, type: 'dashed', width: 1 },
          label: { show: false },
          data: [{ yAxis: targets.inflationCenter }],
        },
      },
    ],
  });
}

export function fxOption(p: Palette, usd: DollarPoint[]): EChartsCoreOption {
  const band = usd.map((x) => [ts(x.d), x.lo === null || x.hi === null ? null : x.hi - x.lo]);
  return baseOption(p, {
    tooltip: {
      trigger: 'axis',
      backgroundColor: p.surface,
      borderColor: p.rule,
      textStyle: { color: p.ink, fontSize: 13 },
      valueFormatter: (v: unknown) => (typeof v === 'number' ? `R$ ${formatNumber(v, 4)}` : '—'),
    },
    xAxis: timeAxis(p),
    yAxis: valueAxis(p, '', 'dataMin'),
    series: [
      {
        name: 'base da banda',
        type: 'line',
        stack: 'banda',
        silent: true,
        showSymbol: false,
        lineStyle: { opacity: 0 },
        itemStyle: { color: 'transparent' },
        data: usd.map((x) => [ts(x.d), x.lo]),
      },
      {
        name: 'banda ±1 desvio',
        type: 'line',
        stack: 'banda',
        silent: true,
        showSymbol: false,
        lineStyle: { opacity: 0 },
        areaStyle: { color: p.band },
        itemStyle: { color: 'transparent' },
        data: band,
      },
      {
        name: 'PTAX venda',
        type: 'line',
        showSymbol: false,
        lineStyle: { width: 2.25, color: p.s1 },
        itemStyle: { color: p.s1 },
        data: usd.map((x) => [ts(x.d), x.v]),
      },
      {
        name: 'média de 90 pregões',
        type: 'line',
        showSymbol: false,
        lineStyle: { width: 1.5, type: 'dashed', color: p.ink2 },
        itemStyle: { color: p.ink2 },
        data: usd.map((x) => [ts(x.d), x.ma90]),
      },
    ],
  });
}

export function groupsOption(p: Palette, groups: IpcaGroups): EChartsCoreOption {
  const sorted = groups.groups
    .flatMap((g) => (g.acc12m === null ? [] : [{ name: g.name, value: g.acc12m }]))
    .sort((a, b) => a.value - b.value);
  const general = groups.general.acc12m ?? 0;
  return baseOption(p, {
    legend: { show: false },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: p.surface,
      borderColor: p.rule,
      textStyle: { color: p.ink, fontSize: 13 },
      valueFormatter: pctTooltip('% em 12 meses'),
    },
    grid: { left: 150, right: 56, top: 12, bottom: 24 },
    xAxis: valueAxis(p, '%', 0),
    yAxis: {
      type: 'category',
      data: sorted.map((g) => g.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: p.ink2, fontSize: 13, width: 140, overflow: 'truncate' },
    },
    series: [
      {
        name: 'IPCA em 12 meses',
        type: 'bar',
        barMaxWidth: 18,
        itemStyle: { color: p.s2, borderRadius: [0, 4, 4, 0] },
        label: {
          show: true,
          position: 'right',
          color: p.ink,
          fontSize: 12,
          formatter: (params: { value: unknown }) => `${formatNumber(Number(params.value), 2)}%`,
        },
        data: sorted.map((g) => g.value),
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: p.ink2, type: 'dashed', width: 1 },
          label: { formatter: `geral ${formatNumber(general, 2)}%`, color: p.ink2, fontSize: 11 },
          data: [{ xAxis: general }],
        },
      },
    ],
  });
}

export function simulationOption(
  p: Palette,
  months: number,
  series: { name: string; values: number[]; color: 's1' | 's2' | 's3' }[],
): EChartsCoreOption {
  return baseOption(p, {
    tooltip: {
      trigger: 'axis',
      backgroundColor: p.surface,
      borderColor: p.rule,
      textStyle: { color: p.ink, fontSize: 13 },
      valueFormatter: (v: unknown) => (typeof v === 'number' ? `R$ ${formatNumber(v, 2)}` : '—'),
    },
    xAxis: {
      type: 'category',
      data: Array.from({ length: months + 1 }, (_, m) => (m % 12 === 0 ? String(m / 12) + " a" : '')),
      axisLine: { lineStyle: { color: p.axis } },
      axisLabel: { color: p.muted, fontSize: 12, hideOverlap: true },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: p.muted, fontSize: 12, formatter: (v: number) => formatNumber(v, 0) },
      splitLine: { lineStyle: { color: p.grid } },
    },
    series: series.map((s) => ({
      name: s.name,
      type: 'line' as const,
      showSymbol: false,
      lineStyle: { width: 2.25, color: p[s.color] },
      itemStyle: { color: p[s.color] },
      data: s.values,
    })),
  });
}
