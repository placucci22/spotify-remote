import { useEffect, useState } from "react";
import { getEVAnalysis, getKnownSetsEV } from "../api/client";
import EVCard from "../components/EVCard";
import { Calculator, Loader, Info } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    const val = payload[0].value;
    return (
      <div className="bg-pokemon-card border border-pokemon-border rounded p-2 text-xs">
        <p className="text-gray-300 font-semibold">{label}</p>
        <p className={val >= 0 ? "text-green-400" : "text-red-400"}>
          {val >= 0 ? "+" : ""}R$ {val?.toFixed(0)} ({payload[0].payload.pct?.toFixed(1)}%)
        </p>
      </div>
    );
  }
  return null;
};

export default function BoxAnalysis() {
  const [evData, setEvData] = useState([]);
  const [knownSets, setKnownSets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("products"); // "products" | "sets"

  useEffect(() => {
    Promise.all([
      getEVAnalysis(),
      getKnownSetsEV(),
    ]).then(([ev, sets]) => {
      setEvData(ev.ev_analyses || []);
      setKnownSets(sets.sets || []);
    }).finally(() => setLoading(false));
  }, []);

  const chartData = evData.map((e) => ({
    name: (e.set_name || e.product_name)?.split(" ").slice(0, 3).join(" "),
    value: e.expected_profit_loss_brl,
    pct: e.expected_profit_loss_pct,
    rec: e.recommendation,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Análise de EV</h1>
        <p className="text-gray-400 text-sm">
          Expected Value: vale mais a pena abrir ou guardar selado?
        </p>
      </div>

      {/* Info box */}
      <div className="card bg-blue-950/40 border-blue-800 flex gap-3 text-sm">
        <Info size={16} className="text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-gray-300">
          <span className="font-semibold text-blue-300">Como funciona o EV:</span>{" "}
          Calculamos a soma ponderada do valor de cada carta possível de puxar,
          multiplicada pela taxa de pull rate. Se o EV é maior que o preço da caixa,
          abrí-la tem expectativa de lucro. Se for negativo, guardar selado geralmente é melhor.
        </div>
      </div>

      {/* Chart */}
      {!loading && chartData.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">
            Lucro/Prejuízo esperado por caixa (R$)
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 0, right: 0, bottom: 30, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" />
              <XAxis
                dataKey="name"
                tick={{ fill: "#9ca3af", fontSize: 10 }}
                tickLine={false}
                angle={-35}
                textAnchor="end"
              />
              <YAxis
                tick={{ fill: "#9ca3af", fontSize: 10 }}
                tickLine={false}
                tickFormatter={(v) => `R$${v}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="4 2" />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={entry.value >= 0 ? "#22c55e" : entry.value >= -200 ? "#f97316" : "#ef4444"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setTab("products")}
          className={tab === "products" ? "btn-primary text-sm" : "btn-secondary text-sm"}
        >
          Produtos no Liga
        </button>
        <button
          onClick={() => setTab("sets")}
          className={tab === "sets" ? "btn-primary text-sm" : "btn-secondary text-sm"}
        >
          Sets conhecidos (EV base)
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 text-gray-400">
          <Loader className="animate-spin mr-2" size={18} /> Calculando EV...
        </div>
      ) : tab === "products" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {evData.map((ev, i) => (
            <EVCard key={ev.product_id ?? i} ev={ev} />
          ))}
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-pokemon-border">
              <tr className="text-gray-400 text-xs">
                <th className="text-left px-4 py-3">Set</th>
                <th className="text-right px-4 py-3">EV (USD)</th>
                <th className="text-right px-4 py-3">EV (BRL)</th>
                <th className="text-left px-4 py-3">Top hit</th>
              </tr>
            </thead>
            <tbody>
              {knownSets.map((s, i) => (
                <tr key={i} className="border-b border-pokemon-border/40 hover:bg-pokemon-border/20">
                  <td className="px-4 py-3 font-medium text-white">{s.set_name}</td>
                  <td className="px-4 py-3 text-right text-gray-300">$ {s.ev_per_box_usd?.toFixed(0)}</td>
                  <td className="px-4 py-3 text-right text-pokemon-yellow font-bold">
                    R$ {s.ev_per_box_brl?.toFixed(0)}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {s.top_hits?.[0]?.name}{" "}
                    {s.top_hits?.[0]?.price_usd && (
                      <span className="text-green-400">${s.top_hits[0].price_usd}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
