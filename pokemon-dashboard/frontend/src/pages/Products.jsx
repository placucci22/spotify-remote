import { useEffect, useState } from "react";
import { getProducts, refreshProducts } from "../api/client";
import RecommendationBadge from "../components/RecommendationBadge";
import { Search, RefreshCw, Filter, Package, Loader } from "lucide-react";

const CATEGORIES = [
  { value: "", label: "Todos" },
  { value: "booster_box", label: "Booster Box" },
  { value: "etb", label: "ETB" },
  { value: "tin", label: "Tin" },
  { value: "blister", label: "Blister" },
  { value: "collection", label: "Coleção" },
];

export default function Products() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [inStockOnly, setInStockOnly] = useState(false);
  const [sortBy, setSortBy] = useState("price_asc");

  const load = (params = {}) => {
    setLoading(true);
    getProducts({ search, category, in_stock_only: inStockOnly, ...params })
      .then(setData)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [search, category, inStockOnly]);

  const sorted = (data?.products || []).slice().sort((a, b) => {
    if (sortBy === "price_asc") return a.price_brl - b.price_brl;
    if (sortBy === "price_desc") return b.price_brl - a.price_brl;
    if (sortBy === "name") return a.name.localeCompare(b.name);
    return 0;
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Produtos</h1>
          <p className="text-gray-400 text-sm">
            {data?.total ?? "—"} produtos · Liga Pokémon
          </p>
        </div>
        <button
          onClick={() => refreshProducts().then(() => setTimeout(load, 4000))}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={14} />
          Atualizar
        </button>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg pl-8 pr-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
            placeholder="Buscar produto..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>

        <select
          className="bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="price_asc">Menor preço</option>
          <option value="price_desc">Maior preço</option>
          <option value="name">Nome A-Z</option>
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={inStockOnly}
            onChange={(e) => setInStockOnly(e.target.checked)}
            className="rounded border-pokemon-border"
          />
          Em estoque
        </label>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-40 text-gray-400">
          <Loader className="animate-spin mr-2" size={18} /> Carregando...
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-pokemon-border">
              <tr className="text-gray-400 text-xs">
                <th className="text-left px-4 py-3">Produto</th>
                <th className="text-left px-4 py-3">Categoria</th>
                <th className="text-right px-4 py-3">Preço</th>
                <th className="text-center px-4 py-3">Estoque</th>
                <th className="text-left px-4 py-3">Vendedor</th>
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-10 text-gray-500">
                    Nenhum produto encontrado
                  </td>
                </tr>
              ) : (
                sorted.map((p) => (
                  <tr
                    key={p.id}
                    className="border-b border-pokemon-border/40 hover:bg-pokemon-border/20 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium text-white max-w-xs">{p.name}</p>
                      {p.set_name && (
                        <p className="text-xs text-gray-500">{p.set_name}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs bg-pokemon-border/50 px-2 py-1 rounded text-gray-300 capitalize">
                        {p.category?.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-pokemon-yellow">
                      R$ {p.price_brl?.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {p.in_stock ? (
                        <span className="text-green-400 text-xs font-semibold">✓ Sim</span>
                      ) : (
                        <span className="text-red-400 text-xs">✗ Esgotado</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{p.seller}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
