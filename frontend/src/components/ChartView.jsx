import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer,
  PieChart, Pie, RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts';
import '../styles/ChartView.css';

const PALETTE = [
  '#000b84', '#2644FF', '#8C94CE', '#748DFF',
  '#050A49', '#090C2D', '#D6DDFF', '#E9EFFF',
  '#B4B4B7', '#6D6D70',
];

function truncateLabel(val, max = 34) {
  const s = String(val ?? '');
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

const HORIZONTAL_LABEL_KEYS = new Set([
  'street', 'area', 'name', 'category', 'indicator', 'domain', 'metric', 'dimension', 'department', 'issue',
]);

function getKeys(chartData) {
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

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: '#fff', border: '1px solid #E4E4E7', borderRadius: 12,
      padding: '6px 12px', fontSize: 12, boxShadow: '0 8px 20px rgba(16,24,40,0.12)',
    }}>
      {label && <div style={{ fontWeight: 570, color: '#3F3F46', marginBottom: 2 }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ color: '#0E0E11', fontWeight: 790 }}>
          {p.value?.toLocaleString()}
        </div>
      ))}
    </div>
  );
};

export default function ChartView({ chartData, chartType = 'bar', hideHeader = false, beforeBody = null }) {
  if (!chartData || !chartData.data || chartData.data.length === 0) return null;

  const { title, xKey, yKey, yKey2, xLabel, yLabel, data } = chartData;
  const { nameKey, valueKey, isHorizontal } = getKeys(chartData);
  const displayData = (chartType === 'pie' || chartType === 'radar') ? data.slice(0, 8) : data;

  const renderBar = () => {
    const dataset = isHorizontal ? [...data].reverse() : data;
    const maxLabelLen = isHorizontal ? Math.max(0, ...dataset.map(d => String(d?.[yKey] ?? '').length)) : 0;
    const axisWidth = isHorizontal ? Math.min(340, Math.max(120, maxLabelLen * 6 + 16)) : undefined;

    return (
      <ResponsiveContainer width="100%" height={320}>
        <BarChart
          data={dataset}
          layout={isHorizontal ? 'vertical' : 'horizontal'}
          margin={{ top: 8, right: 16, bottom: 36, left: isHorizontal ? 0 : 12 }}
        >
          <CartesianGrid strokeDasharray="3 4" stroke="#E4E4E7" vertical={isHorizontal} horizontal={!isHorizontal} />
          {isHorizontal ? (
            <>
              <XAxis type="number" tick={{ fontSize: 11, fill: '#52525B' }} label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -8, fontSize: 11 } : undefined} />
              <YAxis type="category" dataKey={yKey} width={axisWidth} tick={{ fontSize: 11, fill: '#52525B' }} tickFormatter={v => truncateLabel(v, 44)} />
            </>
          ) : (
            <>
              <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#52525B' }} tickFormatter={v => truncateLabel(v, 18)} label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -20, fontSize: 11 } : undefined} />
              <YAxis tick={{ fontSize: 11, fill: '#52525B' }} label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 11 } : undefined} />
            </>
          )}
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey={isHorizontal ? xKey : yKey} radius={[4, 4, 4, 4]} maxBarSize={18}>
            {dataset.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
          </Bar>
          {yKey2 && !isHorizontal && (
            <Bar dataKey={yKey2} radius={[4, 4, 4, 4]} maxBarSize={18} fill={PALETTE[2]} />
          )}
        </BarChart>
      </ResponsiveContainer>
    );
  };

  const renderPie = () => {
    const pieData = displayData.map((d, i) => ({
      name: String(d?.[nameKey] ?? ''),
      value: Number(d?.[valueKey] ?? 0),
      fill: PALETTE[i % PALETTE.length],
    }));
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={pieData} cx="50%" cy="50%" innerRadius="40%" outerRadius="80%" paddingAngle={2} dataKey="value">
            {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  const renderRadar = () => {
    const radarData = displayData.map(d => ({
      subject: truncateLabel(String(d?.[nameKey] ?? ''), 28),
      value: Number(d?.[valueKey] ?? 0),
    }));
    return (
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={radarData} margin={{ top: 18, right: 18, bottom: 18, left: 18 }}>
          <PolarGrid stroke="#E4E4E7" />
          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: '#52525B' }} />
          <Radar name={xLabel || valueKey} dataKey="value" stroke={PALETTE[0]} fill={PALETTE[0]} fillOpacity={0.25} />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
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
