import {
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid,
  Tooltip, Legend,
  ResponsiveContainer
} from 'recharts';
import '../styles/ChartView.css';

// Palette aligned with the app's blue/indigo design system
const PALETTE = [
  '#2644FF', '#000B84', '#8C94CE', '#748DFF',
  '#050A49', '#090C2D', '#D6DDFF', '#E9EFFF',
  '#B4B4B7', '#6D6D70',
];

const TOOLTIP_STYLE = {
  borderRadius: 8,
  border: '1px solid #E4E4E7',
  fontSize: 13,
  fontFamily: "'Saans TRIAL', sans-serif",
};

// Derive which key is the "name" (category) and which is the "value" (numeric)
function getKeys(chartData) {
  const isHorizontal = chartData.yKey === 'street' || chartData.yKey === 'area';
  return {
    nameKey: isHorizontal ? chartData.yKey : chartData.xKey,
    valueKey: isHorizontal ? chartData.xKey : chartData.yKey,
    isHorizontal,
  };
}

// Custom legend renderer used by pie and radar
function ColorLegend({ items }) {
  return (
    <div className="chart-legend">
      {items.map((item, i) => (
        <div key={i} className="chart-legend-item">
          <span className="chart-legend-dot" style={{ background: item.color }} />
          <span className="chart-legend-label">{item.name}</span>
        </div>
      ))}
    </div>
  );
}

export default function ChartView({ chartData, chartType = 'bar' }) {
  if (!chartData || !chartData.data || chartData.data.length === 0) return null;

  const { type, title, xKey, yKey, yKey2, xLabel, yLabel, data } = chartData;
  const { nameKey, valueKey, isHorizontal } = getKeys(chartData);

  // For pie/radar, limit to top 8 items to keep it readable
  const displayData = (chartType === 'pie' || chartType === 'radar')
    ? data.slice(0, 8)
    : data;

  const renderBar = () => {
    // If original data was a line chart, respect that when in 'bar' mode
    if (type === 'line') {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 24, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: '#6D6D70' }}
              label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -32, fontSize: 12, fill: '#9D9DA0' } : undefined} />
            <YAxis tick={{ fontSize: 12, fill: '#6D6D70' }}
              label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 12, fill: '#9D9DA0' } : undefined} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }}
              formatter={(val) => <span style={{ color: '#555558' }}>{val}</span>} />
            <Line type="monotone" dataKey={yKey} name={yLabel || yKey}
              stroke={PALETTE[0]} strokeWidth={2}
              dot={{ r: 4, fill: PALETTE[0] }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      );
    }

    if (isHorizontal) {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart layout="vertical" data={[...data].reverse()}
            margin={{ top: 10, right: 32, left: 8, bottom: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: '#6D6D70' }}
              label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -8, fontSize: 12, fill: '#9D9DA0' } : undefined} />
            <YAxis type="category" dataKey={yKey} width={160} tick={{ fontSize: 11, fill: '#555558' }} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }}
              formatter={(val) => <span style={{ color: '#555558' }}>{val}</span>} />
            <Bar dataKey={xKey} name={xLabel || xKey} fill={PALETTE[0]} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      );
    }

    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 24, left: 0, bottom: 48 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: '#6D6D70' }}
            label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -32, fontSize: 12, fill: '#9D9DA0' } : undefined} />
          <YAxis tick={{ fontSize: 12, fill: '#6D6D70' }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }}
            formatter={(val) => <span style={{ color: '#555558' }}>{val}</span>} />
          <Bar dataKey={yKey} name="Total" fill={PALETTE[0]} radius={[4, 4, 0, 0]} />
          {yKey2 && <Bar dataKey={yKey2} name="Unresolved" fill={PALETTE[2]} radius={[4, 4, 0, 0]} />}
        </BarChart>
      </ResponsiveContainer>
    );
  };

  const renderPie = () => {
    const legendItems = displayData.map((d, i) => ({
      name: d[nameKey],
      color: PALETTE[i % PALETTE.length],
    }));

    return (
      <div className="chart-pie-wrapper">
        <ResponsiveContainer width="100%" height="75%">
          <PieChart>
            <Pie
              data={displayData}
              dataKey={valueKey}
              nameKey={nameKey}
              cx="50%"
              cy="50%"
              outerRadius="75%"
              innerRadius="35%"
              paddingAngle={2}
            >
              {displayData.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE}
              formatter={(val, name) => [val.toLocaleString(), name]} />
          </PieChart>
        </ResponsiveContainer>
        <ColorLegend items={legendItems} />
      </div>
    );
  };

  const renderRadar = () => {
    const legendItems = [{ name: valueKey === 'score' ? 'Deterioration Score' : xLabel || valueKey, color: PALETTE[0] }];

    return (
      <div className="chart-radar-wrapper">
        <ResponsiveContainer width="100%" height="85%">
          <RadarChart data={displayData} cx="50%" cy="50%" outerRadius="70%">
            <PolarGrid stroke="#E4E4E7" />
            <PolarAngleAxis dataKey={nameKey} tick={{ fontSize: 11, fill: '#555558' }} />
            <PolarRadiusAxis tick={{ fontSize: 10, fill: '#9D9DA0' }} />
            <Radar
              name={xLabel || valueKey}
              dataKey={valueKey}
              stroke={PALETTE[0]}
              fill={PALETTE[0]}
              fillOpacity={0.25}
              strokeWidth={2}
            />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
          </RadarChart>
        </ResponsiveContainer>
        <ColorLegend items={legendItems} />
      </div>
    );
  };

  return (
    <div className="chart-view">
      <div className="chart-header">
        <span className="chart-title">{title}</span>
      </div>
      <div className="chart-body">
        {chartType === 'pie'   && renderPie()}
        {chartType === 'radar' && renderRadar()}
        {(chartType === 'bar' || chartType === undefined) && renderBar()}
      </div>
    </div>
  );
}
