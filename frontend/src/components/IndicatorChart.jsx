import '../styles/IndicatorChart.css';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

export default function IndicatorChart({ data, indicatorKey }) {
  const chartData = data.map(d => ({ name: d.areaName, value: d[indicatorKey] }));
  return (
    <div className="chart-wrapper" id="indicators">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="value" fill="#8884d8" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
