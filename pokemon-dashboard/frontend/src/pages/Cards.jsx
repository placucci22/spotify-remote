import { useEffect, useState, useMemo } from "react";
import { Layers, Search, ArrowUpDown, ExternalLink, Globe } from "lucide-react";
import api, { getCardsPokeprice } from "../api/client";

// Known English sets for live pokeprice lookup
const POKEPRICE_SETS = [
  "Journey Together", "Surging Sparks", "Prismatic Evolutions",
  "Stellar Crown", "Twilight Masquerade", "Temporal Forces",
  "Paradox Rift", "151", "Obsidian Flames", "Paldea Evolved",
  "Scarlet & Violet",
];

const RARITY_COLOR = {
  "special illustration rare": "text-yellow-300 bg-yellow-900/40",
  "hyper rare": "text-purple-300 bg-purple-900/40",
  "illustration rare": "text-blue-300 bg-blue-900/40",
  "ultra rare": "text-orange-300 bg-orange-900/40",
  "double rare": "text-green-300 bg-green-900/40",
  "secret rare": "text-pink-300 bg-pink-900/40",
  "full art": "text-cyan-300 bg-cyan-900/40",
};

function rarityClass(rarity) {
  const key = (rarity || "").toLowerCase();
  for (const [k, v] of Object.entries(RARITY_COLOR)) {
    if (key.includes(k)) return v;
  }
  return "text-gray-400 bg-gray-800/40";
}

function RarityBadge({ rarity }) {
  if (!rarity) return null;
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${rarityClass(rarity)}`}>
      {rarity}
    </span>
  );
}

function SortButton({ field, current, onSort, children }) {
  const active = current.field === field;
  return (
    <button
      onClick={() => onSort(field)}
      className={`flex items-center gap-1 text-xs font-medium transition-colors ${active ? "text-pokemon-yellow" : "text-gray-400 hover:text-white"}`}
    >
      {children}
      <ArrowUpDown size={11} className={active ? "text-pokemon-yellow" : ""} />
    </button>
  );
}

export default function Cards() {
  // "liga" = local scraped data from KV; "live" = pokeprice API
  const [mode, setMode] = useState("live");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [selectedSet, setSelectedSet] = useState("Journey Together");
  const [selectedRarity, setSelectedRarity] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [sort, setSort] = useState({ field: "price_usd", asc: false });

  useEffect(() => {
    setLoading(true);
    setError(null);
    if (mode === "live") {
      getCardsPokeprice({
        set_name: selectedSet || undefined,
        search: (!selectedSet && search) ? search : undefined,
        limit: 50,
      })
        .then(r => setData({ cards: r.cards, total: r.total, exchange_rate: r.exchange_rate, available_sets: POKEPRICE_SETS }))
        .catch(() => setError("Erro ao buscar dados ao vivo. Verifique POKEPRICE_API_KEY."))
        .finally(() => setLoading(false));
    } else {
      api.get("/cards", { params: { language: "en", limit: 500 } })
        .then(r => setData(r.data))
        .catch(() => setError("Sem dados locais. Execute: python scripts/scrape_liga_cards.py"))
        .finally(() => setLoading(false));
    }
  }, [mode, selectedSet]);

  function handleSort(field) {
    setSort(s => ({ field, asc: s.field === field ? !s.asc : false }));
  }

  const priceField = mode === "live" ? "price_usd" : "price_brl";

  const filtered = useMemo(() => {
    if (!data?.cards) return [];
    let cards = data.cards;
    const setField = mode === "live" ? "set" : "set_name";
    if (search && mode !== "live") {
      const s = search.toLowerCase();
      cards = cards.filter(c => c.name?.toLowerCase().includes(s) || c[setField]?.toLowerCase().includes(s));
    }
    if (selectedSet && mode !== "live") {
      cards = cards.filter(c => c[setField] === selectedSet || c.set_abbrev === selectedSet);
    }
    if (selectedRarity) {
      const r = selectedRarity.toLowerCase();
      cards = cards.filter(c => (c.rarity || "").toLowerCase().includes(r));
    }
    if (minPrice) {
      cards = cards.filter(c => (c[priceField] || 0) >= parseFloat(minPrice));
    }
    const sf = sort.field === "price_brl" ? priceField : sort.field;
    return [...cards].sort((a, b) => {
      const va = a[sf] ?? 0;
      const vb = b[sf] ?? 0;
      const cmp = typeof va === "number" ? va - vb : String(va).localeCompare(String(vb));
      return sort.asc ? cmp : -cmp;
    });
  }, [data, search, selectedSet, selectedRarity, minPrice, sort, mode, priceField]);

  if (loading) return (
    <div className="flex items-center justify-center h-full text-gray-400">
      <div className="animate-spin mr-2 border-2 border-gray-600 border-t-pokemon-yellow rounded-full w-5 h-5" />
      Carregando cartas...
    </div>
  );

  if (error || !data?.cards?.length) return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
      <Layers size={40} className="text-gray-600" />
      <p className="text-gray-300 font-semibold">{error || "Nenhuma carta encontrada"}</p>
      <div className="card max-w-lg text-left text-sm text-gray-400 space-y-2">
        <p className="text-white font-medium">Para popular os dados:</p>
        <p>1. Configure as variáveis de ambiente KV no seu <code className="text-pokemon-yellow">.env</code></p>
        <p>2. Execute o scraper local:</p>
        <code className="block bg-pokemon-bg px-3 py-2 rounded text-xs text-green-300">
          python scripts/scrape_liga_cards.py --min-price 30
        </code>
        <p className="text-xs text-gray-500">Isso buscará cartas inglesas (ING) das edições conhecidas e salvará no Redis.</p>
      </div>
    </div>
  );

  const sets = data.available_sets || POKEPRICE_SETS;
  const rarities = data.available_rarities || [];
  const rate = data.exchange_rate;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
            <Layers size={22} className="text-pokemon-yellow" />
            Cartas Singles — Inglês (ING)
          </h1>
          <p className="text-gray-400 text-xs md:text-sm mt-0.5">
            {filtered.length} cartas · apenas inglês · PT-BR excluído
          </p>
        </div>
        {/* Mode tabs */}
        <div className="flex gap-1 bg-pokemon-card border border-pokemon-border rounded-lg p-1 flex-shrink-0">
          <button
            onClick={() => setMode("live")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${mode === "live" ? "bg-pokemon-red text-white" : "text-gray-400 hover:text-white"}`}
          >
            <Globe size={12} /> Ao vivo
          </button>
          <button
            onClick={() => setMode("liga")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${mode === "liga" ? "bg-pokemon-red text-white" : "text-gray-400 hover:text-white"}`}
          >
            <Layers size={12} /> Liga BR
          </button>
        </div>
      </div>

      {mode === "live" && (
        <div className="text-xs text-blue-300 bg-blue-950/40 border border-blue-800 rounded-lg px-3 py-2">
          <Globe size={12} className="inline mr-1" />
          Preços ao vivo do <strong>PokemonPriceTracker</strong> (TCGPlayer market price em USD).
          Selecione um set abaixo. Cada consulta usa créditos da API (100/dia no plano gratuito).
        </div>
      )}

      {/* Filters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {mode !== "live" && (
          <div className="col-span-2 md:col-span-1 relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Buscar carta..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-pokemon-card border border-pokemon-border rounded-lg pl-8 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-pokemon-yellow"
            />
          </div>
        )}
        <select
          value={selectedSet}
          onChange={e => setSelectedSet(e.target.value)}
          className="bg-pokemon-card border border-pokemon-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pokemon-yellow"
        >
          {mode === "live" ? null : <option value="">Todos os sets</option>}
          {sets.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={selectedRarity}
          onChange={e => setSelectedRarity(e.target.value)}
          className="bg-pokemon-card border border-pokemon-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pokemon-yellow"
        >
          <option value="">Todas raridades</option>
          {rarities.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <input
          type="number"
          placeholder="Preço mín. (R$)"
          value={minPrice}
          onChange={e => setMinPrice(e.target.value)}
          className="bg-pokemon-card border border-pokemon-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-pokemon-yellow"
        />
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-2">
        {filtered.slice(0, 100).map((card, i) => (
          <div key={card.id ?? i} className="card flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white text-sm font-semibold truncate">{card.name}</span>
                <RarityBadge rarity={card.rarity} />
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                {card.set_name || card.set_abbrev}
                {card.card_number && <span className="ml-1">· #{card.card_number}</span>}
              </p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-pokemon-yellow font-bold text-sm">
                {card.price_brl != null ? `R$ ${card.price_brl.toFixed(0)}` : "—"}
              </p>
              {card.url && (
                <a href={card.url} target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-white">
                  <ExternalLink size={12} />
                </a>
              )}
            </div>
          </div>
        ))}
        {filtered.length > 100 && (
          <p className="text-center text-gray-500 text-xs py-2">
            Mostrando 100 de {filtered.length}. Use os filtros para refinar.
          </p>
        )}
      </div>

      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 text-xs border-b border-pokemon-border">
              <th className="text-left pb-2 pr-4">
                <SortButton field="name" current={sort} onSort={handleSort}>Carta</SortButton>
              </th>
              <th className="text-left pb-2 pr-4">
                <SortButton field={mode === "live" ? "set" : "set_name"} current={sort} onSort={handleSort}>Set</SortButton>
              </th>
              <th className="text-left pb-2 pr-4">
                <SortButton field="rarity" current={sort} onSort={handleSort}>Raridade</SortButton>
              </th>
              <th className="text-center pb-2 pr-4">Nº</th>
              {mode === "live" ? (
                <>
                  <th className="text-right pb-2 pr-3">
                    <SortButton field="price_usd" current={sort} onSort={handleSort}>USD</SortButton>
                  </th>
                  <th className="text-right pb-2">BRL</th>
                </>
              ) : (
                <th className="text-right pb-2">
                  <SortButton field="price_brl" current={sort} onSort={handleSort}>Preço BR</SortButton>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 300).map((card, i) => (
              <tr key={card.id ?? i} className="border-b border-pokemon-border/40 hover:bg-pokemon-card/50 group">
                <td className="py-2 pr-4 font-medium text-white max-w-xs">
                  <div className="flex items-center gap-2">
                    {card.url ? (
                      <a href={card.url} target="_blank" rel="noopener noreferrer"
                        className="hover:text-pokemon-yellow transition-colors truncate">
                        {card.name}
                      </a>
                    ) : (
                      <span className="truncate">{card.name}</span>
                    )}
                    <ExternalLink size={11} className="text-gray-600 group-hover:text-gray-400 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </td>
                <td className="py-2 pr-4 text-gray-300 text-xs">
                  {card.set || card.set_name || card.set_abbrev}
                </td>
                <td className="py-2 pr-4">
                  <RarityBadge rarity={card.rarity} />
                </td>
                <td className="py-2 pr-4 text-center text-gray-500 text-xs">
                  {card.number || card.card_number || "—"}
                </td>
                {mode === "live" ? (
                  <>
                    <td className="py-2 pr-3 text-right">
                      {card.price_usd != null ? (
                        <span className="text-green-400 font-bold">${card.price_usd.toFixed(2)}</span>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="py-2 text-right text-gray-400 text-xs">
                      {card.price_brl != null ? `R$ ${card.price_brl.toFixed(0)}` : "—"}
                    </td>
                  </>
                ) : (
                  <td className="py-2 text-right">
                    {card.price_brl != null ? (
                      <span className="text-pokemon-yellow font-bold">R$ {card.price_brl.toFixed(0)}</span>
                    ) : <span className="text-gray-600">—</span>}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 300 && (
          <p className="text-center text-gray-500 text-xs py-3">
            Mostrando 300 de {filtered.length}. Use os filtros para refinar.
          </p>
        )}
      </div>

      <p className="text-xs text-gray-600 pb-2">
        {mode === "live"
          ? "Preços via PokemonPriceTracker (TCGPlayer market price). BRL calculado pelo câmbio atual."
          : "Preços de ligapokemon.com.br — apenas cartas inglesas. PT-BR excluído (preços não comparáveis)."
        }
      </p>
    </div>
  );
}
