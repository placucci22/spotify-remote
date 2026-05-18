import { useState, useEffect } from "react";
import { getExchangeRate, getKnownSetsEV } from "../api/client";
import RecommendationBadge from "../components/RecommendationBadge";
import { Briefcase, Plus, Trash2, TrendingUp, TrendingDown } from "lucide-react";

const STORAGE_KEY = "pokemon_portfolio";

function loadPortfolio() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
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
};

export default function Portfolio() {
  const [items, setItems] = useState(loadPortfolio);
  const [rate, setRate] = useState(null);
  const [knownSets, setKnownSets] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    type: "Booster Box",
    set_name: "",
    quantity: 1,
    cost_brl: "",
    current_price_brl: "",
    status: "SEALED",
    purchase_date: new Date().toISOString().slice(0, 10),
  });

  useEffect(() => {
    getExchangeRate().then((r) => setRate(r.usd_brl));
    getKnownSetsEV().then((d) => setKnownSets(d.sets || []));
  }, []);

  const addItem = () => {
    if (!form.name || !form.cost_brl) return;
    const newItem = {
      id: Date.now().toString(),
      ...form,
      quantity: Number(form.quantity),
      cost_brl: Number(form.cost_brl),
      current_price_brl: Number(form.current_price_brl) || Number(form.cost_brl),
    };
    const updated = [...items, newItem];
    setItems(updated);
    savePortfolio(updated);
    setShowForm(false);
    setForm({ name: "", type: "Booster Box", set_name: "", quantity: 1, cost_brl: "", current_price_brl: "", status: "SEALED", purchase_date: new Date().toISOString().slice(0, 10) });
  };

  const removeItem = (id) => {
    const updated = items.filter((i) => i.id !== id);
    setItems(updated);
    savePortfolio(updated);
  };

  const updateCurrentPrice = (id, price) => {
    const updated = items.map((i) => i.id === id ? { ...i, current_price_brl: Number(price) } : i);
    setItems(updated);
    savePortfolio(updated);
  };

  const totalCost = items.reduce((s, i) => s + i.cost_brl * i.quantity, 0);
  const totalValue = items.reduce((s, i) => s + (i.current_price_brl || i.cost_brl) * i.quantity, 0);
  const totalPL = totalValue - totalCost;
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost) * 100 : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Portfolio</h1>
          <p className="text-gray-400 text-sm">Rastreie sua coleção e P&amp;L</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2 text-sm">
          <Plus size={14} /> Adicionar
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <p className="text-xs text-gray-400">Custo total</p>
          <p className="text-xl font-bold text-white">R$ {totalCost.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{items.length} itens</p>
        </div>
        <div className="stat-card">
          <p className="text-xs text-gray-400">Valor atual</p>
          <p className="text-xl font-bold text-pokemon-yellow">R$ {totalValue.toFixed(0)}</p>
        </div>
        <div className="stat-card">
          <p className="text-xs text-gray-400">P&amp;L</p>
          <p className={`text-xl font-bold ${totalPL >= 0 ? "text-green-400" : "text-red-400"}`}>
            {totalPL >= 0 ? "+" : ""}R$ {totalPL.toFixed(0)}
          </p>
        </div>
        <div className="stat-card">
          <p className="text-xs text-gray-400">Retorno</p>
          <p className={`text-xl font-bold ${totalPLPct >= 0 ? "text-green-400" : "text-red-400"}`}>
            {totalPLPct >= 0 ? "+" : ""}{totalPLPct.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="card border-pokemon-yellow/30 space-y-4">
          <h2 className="font-semibold text-white">Novo item</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="col-span-2">
              <label className="text-gray-400 text-xs block mb-1">Nome do produto</label>
              <input
                className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                placeholder="Ex: Booster Box Scarlet & Violet 151"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs block mb-1">Tipo</label>
              <select
                className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-gray-100 focus:outline-none"
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
              >
                {PRODUCT_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-gray-400 text-xs block mb-1">Status</label>
              <select
                className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-gray-100 focus:outline-none"
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
              <input
                type="number" min={1}
                className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-gray-100 focus:outline-none"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs block mb-1">Data de compra</label>
              <input
                type="date"
                className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-gray-100 focus:outline-none"
                value={form.purchase_date}
                onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs block mb-1">Preço pago (R$)</label>
              <input
                type="number"
                className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-gray-100 focus:outline-none"
                placeholder="0.00"
                value={form.cost_brl}
                onChange={(e) => setForm({ ...form, cost_brl: e.target.value })}
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs block mb-1">Preço atual (R$)</label>
              <input
                type="number"
                className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-gray-100 focus:outline-none"
                placeholder="Deixe vazio = igual ao pago"
                value={form.current_price_brl}
                onChange={(e) => setForm({ ...form, current_price_brl: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={addItem} className="btn-primary text-sm">Salvar</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancelar</button>
          </div>
        </div>
      )}

      {/* Portfolio table */}
      {items.length === 0 ? (
        <div className="card flex flex-col items-center justify-center h-40 text-gray-500 gap-2">
          <Briefcase size={30} className="opacity-30" />
          <p className="text-sm">Nenhum item no portfolio. Adicione sua primeira caixa!</p>
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-pokemon-border">
              <tr className="text-gray-400 text-xs">
                <th className="text-left px-4 py-3">Produto</th>
                <th className="text-center px-4 py-3">Qtd</th>
                <th className="text-center px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Custo unit.</th>
                <th className="text-right px-4 py-3">Preço atual</th>
                <th className="text-right px-4 py-3">P&amp;L</th>
                <th className="text-center px-4 py-3">Risco reprint</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const current = item.current_price_brl || item.cost_brl;
                const pl = (current - item.cost_brl) * item.quantity;
                const plPct = ((current - item.cost_brl) / item.cost_brl) * 100;
                const setKey = item.name.toLowerCase();
                const reprisk = Object.entries(REPRINT_RISK).find(([k]) => setKey.includes(k))?.[1] || "DESCONHECIDO";
                return (
                  <tr key={item.id} className="border-b border-pokemon-border/40 hover:bg-pokemon-border/20">
                    <td className="px-4 py-3">
                      <p className="font-medium text-white max-w-[180px] truncate">{item.name}</p>
                      <p className="text-xs text-gray-500">{item.type} · {item.purchase_date}</p>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-300">{item.quantity}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                        item.status === "SEALED" ? "bg-blue-800 text-blue-200" :
                        item.status === "OPENED" ? "bg-purple-800 text-purple-200" :
                        "bg-gray-700 text-gray-300"
                      }`}>
                        {item.status === "SEALED" ? "Selado" : item.status === "OPENED" ? "Aberto" : "Vendido"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">
                      R$ {item.cost_brl?.toFixed(0)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <input
                        type="number"
                        className="w-24 bg-pokemon-dark border border-pokemon-border rounded px-2 py-1 text-xs text-right text-gray-100 focus:outline-none"
                        value={current}
                        onChange={(e) => updateCurrentPrice(item.id, e.target.value)}
                      />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <p className={`font-bold text-sm ${pl >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {pl >= 0 ? "+" : ""}R$ {pl.toFixed(0)}
                      </p>
                      <p className={`text-xs ${pl >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {plPct >= 0 ? "+" : ""}{plPct.toFixed(1)}%
                      </p>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs font-semibold ${
                        reprisk === "ALTO" ? "text-red-400" :
                        reprisk === "MÉDIO" ? "text-yellow-400" :
                        reprisk === "BAIXO" ? "text-green-400" : "text-gray-500"
                      }`}>
                        {reprisk}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => removeItem(item.id)}
                        className="text-gray-600 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Reprint risk legend */}
      <div className="card text-xs text-gray-400 space-y-1">
        <p className="font-semibold text-gray-300">Sobre o risco de reimpressão:</p>
        <p><span className="text-red-400 font-semibold">ALTO</span> — A Pokémon Company costuma reimprimir sets populares (ex: Eevee Heroes, Charizard sets). Selado tende a não valorizar.</p>
        <p><span className="text-yellow-400 font-semibold">MÉDIO</span> — Pode ou não ser reimpresso. Acompanhe anúncios oficiais.</p>
        <p><span className="text-green-400 font-semibold">BAIXO</span> — Menos provável de reimpressão. Selado tende a valorizar com tempo.</p>
      </div>
    </div>
  );
}
