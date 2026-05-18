import { useState, useEffect } from "react";
import { getExchangeRate } from "../api/client";
import { Briefcase, Plus, Trash2, X } from "lucide-react";

const STORAGE_KEY = "pokemon_portfolio";

function loadPortfolio() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
  catch { return []; }
}
function savePortfolio(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

const PRODUCT_TYPES = ["Booster Box", "ETB", "Tin", "Blister", "Coleção", "Single Card"];

const REPRINT_RISK = {
  "prismatic evolutions": "ALTO",
  "scarlet & violet 151": "MÉDIO",
  "surging sparks": "MÉDIO",
  "journey together": "BAIXO",
  "temporal forces": "BAIXO",
  "twilight masquerade": "BAIXO",
  "stellar crown": "BAIXO",
};

const EMPTY_FORM = {
  name: "", type: "Booster Box", quantity: 1,
  cost_brl: "", current_price_brl: "",
  status: "SEALED", purchase_date: new Date().toISOString().slice(0, 10),
};

export default function Portfolio() {
  const [items, setItems] = useState(loadPortfolio);
  const [rate, setRate] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  useEffect(() => { getExchangeRate().then((r) => setRate(r.usd_brl)); }, []);

  const addItem = () => {
    if (!form.name || !form.cost_brl) return;
    const updated = [...items, {
      id: Date.now().toString(),
      ...form,
      quantity: Number(form.quantity),
      cost_brl: Number(form.cost_brl),
      current_price_brl: Number(form.current_price_brl) || Number(form.cost_brl),
    }];
    setItems(updated); savePortfolio(updated);
    setShowForm(false); setForm(EMPTY_FORM);
  };

  const removeItem = (id) => {
    const updated = items.filter((i) => i.id !== id);
    setItems(updated); savePortfolio(updated);
  };

  const updateCurrentPrice = (id, price) => {
    const updated = items.map((i) => i.id === id ? { ...i, current_price_brl: Number(price) } : i);
    setItems(updated); savePortfolio(updated);
  };

  const totalCost = items.reduce((s, i) => s + i.cost_brl * i.quantity, 0);
  const totalValue = items.reduce((s, i) => s + (i.current_price_brl || i.cost_brl) * i.quantity, 0);
  const totalPL = totalValue - totalCost;
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost) * 100 : 0;

  const repriskFor = (name) => {
    const lower = name.toLowerCase();
    return Object.entries(REPRINT_RISK).find(([k]) => lower.includes(k))?.[1] || "—";
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-white">Portfolio</h1>
          <p className="text-gray-400 text-xs md:text-sm">Rastreie sua coleção e P&amp;L</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2 text-sm">
          <Plus size={14} /> Adicionar
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-3">
        <div className="stat-card">
          <p className="text-xs text-gray-400">Custo total</p>
          <p className="text-lg font-bold text-white">R$ {totalCost.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{items.length} {items.length === 1 ? "item" : "itens"}</p>
        </div>
        <div className="stat-card">
          <p className="text-xs text-gray-400">Valor atual</p>
          <p className="text-lg font-bold text-pokemon-yellow">R$ {totalValue.toFixed(0)}</p>
        </div>
        <div className="stat-card">
          <p className="text-xs text-gray-400">P&amp;L</p>
          <p className={`text-lg font-bold ${totalPL >= 0 ? "text-green-400" : "text-red-400"}`}>
            {totalPL >= 0 ? "+" : ""}R$ {totalPL.toFixed(0)}
          </p>
        </div>
        <div className="stat-card">
          <p className="text-xs text-gray-400">Retorno</p>
          <p className={`text-lg font-bold ${totalPLPct >= 0 ? "text-green-400" : "text-red-400"}`}>
            {totalPLPct >= 0 ? "+" : ""}{totalPLPct.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Add form — full-screen modal on mobile */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/60 p-4">
          <div className="bg-pokemon-card border border-pokemon-border rounded-xl w-full max-w-md max-h-[90vh] overflow-y-auto p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-white">Novo item</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-white">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <label className="text-gray-400 text-xs block mb-1">Nome do produto *</label>
                <input
                  className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2.5 text-gray-100 focus:outline-none focus:border-blue-500"
                  placeholder="Ex: Booster Box Prismatic Evolutions"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Tipo</label>
                  <select
                    className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2.5 text-gray-100 focus:outline-none"
                    value={form.type}
                    onChange={(e) => setForm({ ...form, type: e.target.value })}
                  >
                    {PRODUCT_TYPES.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Status</label>
                  <select
                    className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2.5 text-gray-100 focus:outline-none"
                    value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                  >
                    <option value="SEALED">Selado</option>
                    <option value="OPENED">Aberto</option>
                    <option value="SOLD">Vendido</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Quantidade</label>
                  <input type="number" min={1}
                    className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2.5 text-gray-100 focus:outline-none"
                    value={form.quantity}
                    onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Data de compra</label>
                  <input type="date"
                    className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2.5 text-gray-100 focus:outline-none"
                    value={form.purchase_date}
                    onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Preço pago (R$) *</label>
                  <input type="number"
                    className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2.5 text-gray-100 focus:outline-none"
                    placeholder="0"
                    value={form.cost_brl}
                    onChange={(e) => setForm({ ...form, cost_brl: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Preço atual (R$)</label>
                  <input type="number"
                    className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2.5 text-gray-100 focus:outline-none"
                    placeholder="Igual ao pago"
                    value={form.current_price_brl}
                    onChange={(e) => setForm({ ...form, current_price_brl: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button onClick={addItem} className="btn-primary flex-1 text-sm">Salvar</button>
              <button onClick={() => setShowForm(false)} className="btn-secondary text-sm px-4">Cancelar</button>
            </div>
          </div>
        </div>
      )}

      {/* Items */}
      {items.length === 0 ? (
        <div className="card flex flex-col items-center justify-center h-36 text-gray-500 gap-2">
          <Briefcase size={28} className="opacity-30" />
          <p className="text-sm">Nenhum item. Adicione sua primeira caixa!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const current = item.current_price_brl || item.cost_brl;
            const pl = (current - item.cost_brl) * item.quantity;
            const plPct = ((current - item.cost_brl) / item.cost_brl) * 100;
            const reprisk = repriskFor(item.name);
            const riskColor = reprisk === "ALTO" ? "text-red-400" : reprisk === "MÉDIO" ? "text-yellow-400" : reprisk === "BAIXO" ? "text-green-400" : "text-gray-500";

            return (
              <div key={item.id} className="card space-y-3">
                {/* Row 1 */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-white text-sm truncate">{item.name}</p>
                    <p className="text-xs text-gray-500">{item.type} · {item.purchase_date} · Qtd: {item.quantity}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                      item.status === "SEALED" ? "bg-blue-800 text-blue-200" :
                      item.status === "OPENED" ? "bg-purple-800 text-purple-200" :
                      "bg-gray-700 text-gray-300"
                    }`}>
                      {item.status === "SEALED" ? "Selado" : item.status === "OPENED" ? "Aberto" : "Vendido"}
                    </span>
                    <button onClick={() => removeItem(item.id)} className="text-gray-600 hover:text-red-400 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Row 2 */}
                <div className="grid grid-cols-3 gap-2 text-xs text-center">
                  <div>
                    <p className="text-gray-500">Pago</p>
                    <p className="font-semibold text-gray-300">R$ {item.cost_brl?.toFixed(0)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Atual</p>
                    <input
                      type="number"
                      className="w-full bg-pokemon-dark border border-pokemon-border rounded px-1 py-1 text-xs text-center text-gray-100 focus:outline-none"
                      value={current}
                      onChange={(e) => updateCurrentPrice(item.id, e.target.value)}
                    />
                  </div>
                  <div>
                    <p className="text-gray-500">P&amp;L</p>
                    <p className={`font-bold ${pl >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {pl >= 0 ? "+" : ""}R$ {pl.toFixed(0)}
                      <span className="block font-normal text-xs">({plPct >= 0 ? "+" : ""}{plPct.toFixed(1)}%)</span>
                    </p>
                  </div>
                </div>

                <div className="flex justify-end">
                  <span className={`text-xs font-semibold ${riskColor}`}>
                    Risco reprint: {reprisk}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Legend */}
      <div className="card text-xs text-gray-400 space-y-1">
        <p className="font-semibold text-gray-300">Risco de reimpressão:</p>
        <p><span className="text-red-400 font-semibold">ALTO</span> — TPC costuma reimprimir. Selado tende a não valorizar muito.</p>
        <p><span className="text-yellow-400 font-semibold">MÉDIO</span> — Incerto. Acompanhe anúncios oficiais.</p>
        <p><span className="text-green-400 font-semibold">BAIXO</span> — Menor chance de reimpressão. Selado tende a valorizar.</p>
      </div>
    </div>
  );
}
