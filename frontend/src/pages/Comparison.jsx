import { useEffect, useState } from "react";
import { getComparisons, getExchangeRate } from "../api/client";
import { Loader, DollarSign, Info } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, Cell,
} from "recharts";

const CATEGORY_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "booster_box", label: "Box" },
  { value: "etb", label: "ETB" },
  { value: "tin", label: "Tin" },
];

const REC_COLORS = {
  "ÓTIMO NEGÓCIO": "bg-green-600",
  "BOM NEGÓCIO": "bg-emerald-700",
  "PREÇO JUSTO": "bg-yellow-700",
  "LIGEIRAMENTE CARO": "bg-orange-700",
  "CARO": "bg-red-700",
  "Sem dados EUA": "bg-gray-700",
};

function CompMobileCard({ c }) {
  const savingsColor = (c.savings_pct ?? 0) > 5
    ? "text-green-400" : (c.savings_pct ?? 0) > -5
    ? "text-yellow-400" : "text-red-400";

  return (
    <div className="card space-y-2">
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold text-white text-sm leading-tight flex-1">{c.name}</p>
        <span className={`text-xs font-bold px-2 py-1 rounded-full flex-shrink-0 text-white ${REC_COLORS[c.recommendation] || "bg-gray-700"}`}>
          {c.recommendation}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div>
          <p className="text-gray-400">Liga BR</p>
          <p className="font-bold text-pokemon-yellow">R$ {c.price_brl?.toFixed(0)}</p>
        </div>
        <div>
          <p className="text-gray-400">TCGPlayer</p>
          <p className="font-bold text-gray-200">{c.tcgplayer_usd ? `$${c.tcgplayer_usd?.toFixed(0)}` : "—"}</p>
        </div>
        <div>
          <p className="text-gray-400">Economia</p>
          <p className={`font-bold ${savingsColor}`}>
            {c.savings_pct != null ? `${c.savings_pct > 0 ? "+" : ""}${c.savings_pct?.toFixed(1)}%` : "—"}
          </p>
        </div>
      </div>
      {c.import_cost_brl && (
        <p className="text-xs text-gray-500">Custo importar (c/ 60% imposto): R$ {c.import_cost_brl?.toFixed(0)}</p>
      )}
    </div>
  );
}

export default function Comparison() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [rate, setRate] = useState(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([getComparisons({ category, limit: 30 }), getExchangeRate()])
      .then(([cmp, exr]) => { setData(cmp); setRate(exr.usd_brl); })
      .finally(() => setLoading(false));
  }, [category]);

  const comparisons = data?.comparisons || [];
  const chartData = comparisons
    .filter((c) => c.savings_pct != null)
    .slice(0, 10)
    .map((c) => ({
      name: c.name.split(" ").slice(1, 4).join(" "),
      savings: c.savings_pct,
    }));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-white">Brasil vs EUA</h1>
        <p className="text-gray-400 text-xs md:text-sm">
          Preços do Liga vs TCGPlayer com imposto de importação (~60%)
        </p>
      </div>

      {rate && (
        <div className="card flex items-center gap-3 bg-green-950/30 border-green-800">
          <DollarSign size={18} className="text-green-400 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-semibold text-green-300">Câmbio: R$ {rate?.toFixed(2)} / USD</p>
            <p className="text-xs text-gray-400">Importar = USD × {rate?.toFixed(2)} × 1.60</p>
          </div>
        </div>
      )}

      <div className="card bg-blue-950/40 border-blue-800 flex gap-2 text-xs md:text-sm">
        <Info size={14} className="text-blue-400 flex-shrink-0 mt-0.5" />
        <p className="text-gray-300">
          <span className="text-blue-300 font-semibold">Economia positiva</span> = comprar no BR é mais barato
          que importar do EUA (incluindo imposto de 60%).
        </p>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        {CATEGORY_OPTIONS.map((c) => (
          <button
            key={c.value}
            onClick={() => setCategory(c.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              category === c.value
                ? "bg-pokemon-red text-white"
                : "bg-pokemon-border/50 text-gray-400 hover:text-white"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 text-gray-400">
          <Loader className="animate-spin mr-2" size={18} /> Buscando preços...
        </div>
      ) : (
        <>
          {/* Chart */}
          {chartData.length > 0 && (
            <div className="card">
              <h2 className="text-xs md:text-sm font-semibold text-gray-300 mb-3">
                Economia vs importar (%) — verde = mais barato no BR
              </h2>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData} margin={{ top: 0, right: 0, bottom: 30, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" />
                  <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 9 }} tickLine={false} angle={-35} textAnchor="end" />
                  <YAxis tick={{ fill: "#9ca3af", fontSize: 9 }} tickLine={false} tickFormatter={(v) => `${v}%`} />
                  <Tooltip
                    formatter={(v) => [`${v?.toFixed(1)}%`, "Economia"]}
                    contentStyle={{ background: "#16213e", border: "1px solid #0f3460", borderRadius: 8, fontSize: 11 }}
                  />
                  <Bar dataKey="savings" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={entry.savings >= 5 ? "#22c55e" : entry.savings >= -5 ? "#eab308" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {comparisons.map((c) => <CompMobileCard key={c.id} c={c} />)}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-pokemon-border">
                <tr className="text-gray-400 text-xs">
                  <th className="text-left px-4 py-3">Produto</th>
                  <th className="text-right px-4 py-3">Liga BR</th>
                  <th className="text-right px-4 py-3">TCGPlayer USD</th>
                  <th className="text-right px-4 py-3">Custo importar</th>
                  <th className="text-right px-4 py-3">Economia</th>
                  <th className="text-center px-4 py-3">Avaliação</th>
                </tr>
              </thead>
              <tbody>
                {comparisons.map((c) => (
                  <tr key={c.id} className="border-b border-pokemon-border/40 hover:bg-pokemon-border/20">
                    <td className="px-4 py-3 font-medium text-white max-w-[220px] truncate">{c.name}</td>
                    <td className="px-4 py-3 text-right text-pokemon-yellow font-bold">R$ {c.price_brl?.toFixed(0)}</td>
                    <td className="px-4 py-3 text-right text-gray-300">
                      {c.tcgplayer_usd ? `$ ${c.tcgplayer_usd?.toFixed(0)}` : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-400 text-xs">
                      {c.import_cost_brl ? `R$ ${c.import_cost_brl?.toFixed(0)}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {c.savings_pct != null ? (
                        <span className={(c.savings_pct > 5) ? "text-green-400 font-bold" : (c.savings_pct > -5) ? "text-yellow-400" : "text-red-400"}>
                          {c.savings_pct > 0 ? "+" : ""}{c.savings_pct?.toFixed(1)}%
                        </span>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs font-bold px-2 py-1 rounded-full text-white ${REC_COLORS[c.recommendation] || "bg-gray-700"}`}>
                        {c.recommendation}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
