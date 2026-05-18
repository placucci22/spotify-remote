import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div className="bg-pokemon-card border border-pokemon-border rounded p-2 text-xs">
        <p className="text-gray-400">{label}</p>
        <p className="text-pokemon-yellow font-bold">
          USD ${payload[0].value?.toFixed(2)}
        </p>
      </div>
    );
  }
  return null;
};

export default function TrendChart({ data = [], title }) {
  if (!data.length) {
    return (
      <div className="card flex items-center justify-center h-40 text-gray-500 text-sm">
        Sem dados históricos disponíveis
      </div>
    );
  }

  return (
    <div className="card">
      {title && <h3 className="text-sm font-semibold text-gray-300 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#9ca3af", fontSize: 10 }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#9ca3af", fontSize: 10 }}
            tickLine={false}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="price_usd"
            stroke="#FFCB05"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#FFCB05" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
