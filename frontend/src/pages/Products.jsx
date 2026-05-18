import { useEffect, useState } from "react";
import { getProducts, refreshProducts } from "../api/client";
import { Search, RefreshCw, Loader, ChevronRight } from "lucide-react";

const CATEGORIES = [
  { value: "", label: "Todos" },
  { value: "booster_box", label: "Box" },
  { value: "etb", label: "ETB" },
  { value: "tin", label: "Tin" },
  { value: "blister", label: "Blister" },
  { value: "collection", label: "Coleção" },
];

function ProductMobileCard({ p }) {
  return (
    <div className="card flex items-center justify-between gap-3">
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-white text-sm truncate">{p.name}</p>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className="text-xs bg-pokemon-border/50 px-2 py-0.5 rounded text-gray-400 capitalize">
            {p.category?.replace("_", " ")}
          </span>
          {p.in_stock ? (
            <span className="text-green-400 text-xs">Em estoque</span>
          ) : (
            <span className="text-red-400 text-xs">Esgotado</span>
          )}
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <p className="font-bold text-pokemon-yellow text-base">R$ {p.price_brl?.toFixed(0)}</p>
        <p className="text-xs text-gray-500">{p.seller}</p>
      </div>
    </div>
  );
}

export default function Products() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [inStockOnly, setInStockOnly] = useState(false);
  const [sortBy, setSortBy] = useState("price_asc");

  const load = () => {
    setLoading(true);
    getProducts({ search, category, in_stock_only: inStockOnly })
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-white">Produtos</h1>
          <p className="text-gray-400 text-xs md:text-sm">{data?.total ?? "—"} produtos · Liga Pokémon</p>
        </div>
        <button
          onClick={() => refreshProducts().then(() => setTimeout(load, 4000))}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={14} />
          <span className="hidden sm:inline">Atualizar</span>
        </button>
      </div>

      {/* Filters */}
      <div className="card space-y-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="w-full bg-pokemon-dark border border-pokemon-border rounded-lg pl-8 pr-3 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
            placeholder="Buscar produto..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
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

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={inStockOnly}
              onChange={(e) => setInStockOnly(e.target.checked)}
              className="rounded border-pokemon-border"
            />
            Em estoque
          </label>

          <select
            className="bg-pokemon-dark border border-pokemon-border rounded-lg px-3 py-1.5 text-xs text-gray-100 focus:outline-none"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="price_asc">↑ Menor preço</option>
            <option value="price_desc">↓ Maior preço</option>
            <option value="name">A-Z</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 text-gray-400">
          <Loader className="animate-spin mr-2" size={18} /> Carregando...
        </div>
      ) : sorted.length === 0 ? (
        <div className="card text-center text-gray-500 py-10">Nenhum produto encontrado</div>
      ) : (
        <>
          {/* Mobile: card list */}
          <div className="md:hidden space-y-3">
            {sorted.map((p) => <ProductMobileCard key={p.id} p={p} />)}
          </div>

          {/* Desktop: table */}
          <div className="hidden md:block card p-0 overflow-hidden">
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
                {sorted.map((p) => (
                  <tr key={p.id} className="border-b border-pokemon-border/40 hover:bg-pokemon-border/20">
                    <td className="px-4 py-3">
                      <p className="font-medium text-white max-w-xs">{p.name}</p>
                      {p.set_name && <p className="text-xs text-gray-500">{p.set_name}</p>}
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
                      {p.in_stock
                        ? <span className="text-green-400 text-xs font-semibold">✓ Sim</span>
                        : <span className="text-red-400 text-xs">✗ Esgotado</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{p.seller}</td>
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
