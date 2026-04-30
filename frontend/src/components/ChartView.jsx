import { BarChart } from '@mui/x-charts/BarChart';
import { PieChart } from '@mui/x-charts/PieChart';
import { RadarChart } from '@mui/x-charts/RadarChart';
import { chartsTooltipClasses } from '@mui/x-charts';
import '../styles/ChartView.css';

// Palette aligned with the app's blue/indigo design system
const PALETTE = [
  '#000b84', '#2644FF', '#8C94CE', '#748DFF',
  '#050A49', '#090C2D', '#D6DDFF', '#E9EFFF',
  '#B4B4B7', '#6D6D70',
];

function truncateLabel(val, max = 34) {
  const s = String(val ?? '');
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

// Derive which key is the "name" (category) and which is the "value" (numeric)
const HORIZONTAL_LABEL_KEYS = new Set([
  'street', 'area', 'name', 'category', 'indicator', 'domain', 'metric', 'dimension', 'department', 'issue',
]);
function getKeys(chartData) {
  // Horizontal when the yKey is a known label field OR when first row's yKey value is a string
  const firstRow = chartData.data && chartData.data[0];
  const yValIsString = firstRow && typeof firstRow[chartData.yKey] === 'string';
  const xValIsNumber = firstRow && typeof firstRow[chartData.xKey] === 'number';
  const isHorizontal = HORIZONTAL_LABEL_KEYS.has(chartData.yKey) || (yValIsString && xValIsNumber);
  return {
    nameKey: isHorizontal ? chartData.yKey : chartData.xKey,
    valueKey: isHorizontal ? chartData.xKey : chartData.yKey,
    isHorizontal,
  };
}

const baseTooltipSx = {
  [`& .${chartsTooltipClasses.paper}`]: {
    border: '1px solid rgba(228, 228, 231, 0.95)',
    boxShadow: '0 8px 20px rgba(16, 24, 40, 0.12)',
    background: '#FFFFFF',
    padding: '6px 10px',
    // Responsive width and safe wrapping so text never escapes the pill.
    maxWidth: 'min(320px, calc(100vw - 32px))',
    outline: 'none',
    overflow: 'hidden',
  },
  [`& .${chartsTooltipClasses.table}`]: {
    background: 'transparent',
    borderCollapse: 'collapse',
    borderSpacing: 0,
    margin: 0,
    tableLayout: 'auto',
    width: 'auto',
    maxWidth: '100%',
  },
  '& td, & th': {
    border: 'none',
    outline: 'none',
    maxWidth: '100%',
  },
  [`& .${chartsTooltipClasses.labelCell}`]: {
    background: 'transparent',
    padding: 0,
    paddingRight: 10,
    fontSize: 12,
    fontWeight: 570,
    color: '#3F3F46',
    whiteSpace: 'normal',
    overflowWrap: 'anywhere',
    wordBreak: 'break-word',
  },
  [`& .${chartsTooltipClasses.valueCell}`]: {
    background: 'transparent',
    padding: 0,
    fontSize: 12,
    fontWeight: 790,
    color: '#0E0E11',
    textAlign: 'right',
    whiteSpace: 'nowrap',
  },
  [`& .${chartsTooltipClasses.mark}`]: {
    borderRadius: 999,
    width: 8,
    height: 8,
    boxShadow: 'none',
    border: 'none',
    outline: 'none',
    stroke: 'none',
  },
};

const pillTooltipSlotProps = {
  tooltip: {
    trigger: 'item',
    placement: 'top',
    sx: {
      ...baseTooltipSx,
      [`& .${chartsTooltipClasses.paper}`]: {
        ...baseTooltipSx[`& .${chartsTooltipClasses.paper}`],
        borderRadius: 999,
      },
    },
  },
};

const squareTooltipSlotProps = {
  tooltip: {
    trigger: 'item',
    placement: 'top',
    sx: {
      ...baseTooltipSx,
      [`& .${chartsTooltipClasses.paper}`]: {
        ...baseTooltipSx[`& .${chartsTooltipClasses.paper}`],
        borderRadius: 12,
      },
    },
  },
};

export default function ChartView({ chartData, chartType = 'bar', hideHeader = false, beforeBody = null }) {
  if (!chartData || !chartData.data || chartData.data.length === 0) return null;

  const { title, xKey, yKey, yKey2, xLabel, yLabel, data } = chartData;
  const { nameKey, valueKey, isHorizontal } = getKeys(chartData);

  // For pie/radar, limit to top 8 items to keep it readable
  const displayData = (chartType === 'pie' || chartType === 'radar')
    ? data.slice(0, 8)
    : data;

  const renderBar = () => {
    const dataset = isHorizontal ? [...data].reverse() : data;
    const isSparse = dataset.length <= 2;
    const maxLabelLen = isHorizontal
      ? Math.max(0, ...dataset.map((d) => String(d?.[yKey] ?? '').length))
      : 0;
    // Rough SVG text width estimate: ~7px per char + padding, capped for layout stability.
    const axisWidth = isHorizontal ? Math.min(340, Math.max(180, maxLabelLen * 7 + 56)) : undefined;

    const barSeries = isHorizontal
      ? [
          {
            dataKey: xKey,
            label: xLabel || xKey,
            color: PALETTE[0],
          },
        ]
      : [
          {
            dataKey: yKey,
            label: yLabel || yKey,
            color: PALETTE[0],
          },
          ...(yKey2
            ? [
                {
                  dataKey: yKey2,
                  label: 'Unresolved',
                  color: PALETTE[2],
                },
              ]
            : []),
        ];

    const canColorizeByCategory = barSeries.length === 1;
    const categoryValues = isHorizontal
      ? dataset.map((d) => String(d?.[yKey] ?? ''))
      : dataset.map((d) => String(d?.[xKey] ?? ''));
    const categoryColors = categoryValues.map((_, i) => PALETTE[i % PALETTE.length]);

    return (
      <BarChart
        dataset={dataset}
        series={barSeries}
        layout={isHorizontal ? 'horizontal' : 'vertical'}
        hideLegend
        maxBarSize={isSparse ? 12 : 18}
        xAxis={
          isHorizontal
            ? [
                {
                  label: xLabel || undefined,
                  tickLabelStyle: { fontSize: 11, fill: '#52525B' },
                },
              ]
            : [
                {
                  scaleType: 'band',
                  dataKey: xKey,
                  categoryGapRatio: isSparse ? 0.85 : 0.65,
                  barGapRatio: isSparse ? 0.35 : 0.2,
                  tickLabelStyle: { fontSize: 11, fill: '#52525B' },
                  valueFormatter: (v) => truncateLabel(v, 18),
                  ...(canColorizeByCategory
                    ? {
                        colorMap: {
                          type: 'ordinal',
                          values: categoryValues,
                          colors: categoryColors,
                          unknownColor: PALETTE[0],
                        },
                      }
                    : {}),
                },
              ]
        }
        yAxis={
          isHorizontal
            ? [
                {
                  scaleType: 'band',
                  dataKey: yKey,
                  categoryGapRatio: isSparse ? 0.85 : 0.65,
                  barGapRatio: isSparse ? 0.35 : 0.2,
                  tickLabelStyle: { fontSize: 11 },
                  width: axisWidth,
                  valueFormatter: (v) => truncateLabel(v, 44),
                  ...(canColorizeByCategory
                    ? {
                        colorMap: {
                          type: 'ordinal',
                          values: categoryValues,
                          colors: categoryColors,
                          unknownColor: PALETTE[0],
                        },
                      }
                    : {}),
                },
              ]
            : [
                {
                  label: yLabel || undefined,
                  tickLabelStyle: { fontSize: 11, fill: '#52525B' },
                },
              ]
        }
        margin={{ top: 8, right: 16, bottom: 36, left: 12 }}
        borderRadius={8}
        slotProps={{
          legend: { hidden: true },
          ...pillTooltipSlotProps,
        }}
        grid={{ horizontal: !isHorizontal, vertical: isHorizontal }}
        sx={{
          // Softer grid + axes to match the rest of the UI
          '& .MuiChartsGrid-line': {
            stroke: '#E4E4E7',
            strokeDasharray: '3 4',
          },
          '& .MuiChartsAxis-line, & .MuiChartsAxis-tick': {
            stroke: '#D4D4D8',
          },
          '& .MuiChartsAxis-tickLabel': {
            fill: '#52525B',
          },
        }}
      />
    );
  };

  const renderPie = () => {
    const pieData = displayData.map((d, i) => ({
      id: `${d?.[nameKey] ?? i}`,
      value: Number(d?.[valueKey] ?? 0),
      label: String(d?.[nameKey] ?? ''),
      color: PALETTE[i % PALETTE.length],
    }));

    return (
      <PieChart
        series={[
          {
            data: pieData,
            innerRadius: '45%',
            outerRadius: '85%',
            paddingAngle: 2,
            cornerRadius: 4,
          },
        ]}
        margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
        slotProps={{
          legend: { hidden: true },
          ...pillTooltipSlotProps,
        }}
      />
    );
  };

  const renderRadar = () => {
    const values = displayData.map((d) => Number(d?.[valueKey] ?? 0));
    const max = Math.max(1, ...values) * 1.12;

    return (
      <RadarChart
        radar={{
          metrics: displayData.map((d) => ({
            name: String(d?.[nameKey] ?? ''),
            max,
            min: 0,
          })),
        }}
        series={[
          {
            label: xLabel || valueKey,
            data: values,
            color: PALETTE[0],
          },
        ]}
        height={340}
        margin={{ top: 18, right: 18, bottom: 18, left: 18 }}
        slotProps={{
          legend: { hidden: true },
          ...squareTooltipSlotProps,
        }}
      />
    );
  };

  return (
    <div className="chart-view">
      {!hideHeader && (
        <div className="chart-header">
          <span className="chart-title" title={title}>{title}</span>
        </div>
      )}
      {beforeBody}
      <div className="chart-body">
        {chartType === 'pie'   && renderPie()}
        {chartType === 'radar' && renderRadar()}
        {(chartType === 'bar' || chartType === undefined) && renderBar()}
      </div>
    </div>
  );
}
