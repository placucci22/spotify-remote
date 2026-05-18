import { useEffect, useState } from "react";
import { getDashboard, refreshProducts } from "../api/client";
import StatCard from "../components/StatCard";
import EVCard from "../components/EVCard";
import { DollarSign, Package, RefreshCw, Loader, Star, TrendingUp } from "lucide-react";

function DiffBadge({ pct }) {
  if (pct == null) return <span className="text-gray-600 text-xs">—</span>;
  const pos = pct > 0;
  return (
    <span className={`text-xs font-bold ${pos ? "text-green-400" : "text-red-400"}`}>
      {pos ? "+" : ""}{pct.toFixed(1)}%
    </span>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [showAllComparisons, setShowAllComparisons] = useState(false);

  const load = () => {
    setLoading(true);
    getDashboard()
      .then(setData)
      .catch(() => setError("Erro ao carregar. Backend rodando?"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refreshProducts();
    setTimeout(() => { load(); setRefreshing(false); }, 5000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <Loader className="animate-spin mr-2" size={20} /> Carregando...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
        <p className="text-red-400 font-semibold">{error}</p>
        <button onClick={load} className="btn-primary text-sm">Tentar novamente</button>
      </div>
    );
  }

  const comparisons = data?.all_comparisons ?? data?.best_deals ?? [];
  const visibleComparisons = showAllComparisons ? comparisons : comparisons.slice(0, 10);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 text-xs md:text-sm">Liga Pokémon · Análise de preços TCG</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary flex items-center gap-2 text-sm flex-shrink-0"
        >
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          <span className="hidden sm:inline">{refreshing ? "Atualizando..." : "Atualizar"}</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          title="Câmbio USD/BRL"
          value={`R$ ${data?.exchange_rate?.toFixed(2)}`}
          sub="Banco Central"
          icon={DollarSign}
          color="text-green-400"
        />
        <StatCard
          title="Produtos"
          value={data?.total_products ?? "—"}
          sub={`${data?.total_sealed ?? 0} selados`}
          icon={Package}
          color="text-pokemon-yellow"
        />
        <StatCard
          title="Mais baratos que EUA"
          value={data?.best_deals?.filter(p => (p.savings_pct ?? 0) > 0).length ?? 0}
          sub="vs TCGPlayer convertido"
          icon={TrendingUp}
          color="text-green-400"
        />
        <StatCard
          title="Atualizado"
          value={data?.last_updated
            ? new Date(data.last_updated).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
            : "—"}
          sub={data?.last_updated ? new Date(data.last_updated).toLocaleDateString("pt-BR") : ""}
          icon={RefreshCw}
          color="text-blue-400"
        />
      </div>

      {/* BR vs EUA comparison table */}
      {comparisons.length > 0 && (
        <section>
          <h2 className="text-base md:text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Star size={16} className="text-green-400" />
            BR vs EUA — todos os produtos selados
          </h2>

          {/* Mobile */}
          <div className="md:hidden space-y-2">
            {visibleComparisons.map((p) => (
              <div key={p.id} className="card flex justify-between items-center gap-2 py-2">
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-semibold truncate">{p.name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    <span className="text-pokemon-yellow font-bold">R$ {p.price_brl?.toFixed(0)}</span>
                    {p.tcgplayer_usd && <> · TCG ${p.tcgplayer_usd?.toFixed(0)} = R$ {p.tcgplayer_brl?.toFixed(0)}</>}
                  </p>
                </div>
                <DiffBadge pct={p.savings_pct} />
              </div>
            ))}
          </div>

          {/* Desktop */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-xs border-b border-pokemon-border">
                  <th className="text-left pb-2 pr-4">Produto</th>
                  <th className="text-right pb-2 pr-4">Liga BR</th>
                  <th className="text-right pb-2 pr-4">TCGPlayer USD</th>
                  <th className="text-right pb-2 pr-4">TCGPlayer em BRL</th>
                  <th className="text-right pb-2">Diferença</th>
                </tr>
              </thead>
              <tbody>
                {visibleComparisons.map((p) => (
                  <tr key={p.id} className="border-b border-pokemon-border/50 hover:bg-pokemon-card/50">
                    <td className="py-2 pr-4 font-medium text-white max-w-xs truncate">{p.name}</td>
                    <td className="py-2 pr-4 text-right text-pokemon-yellow font-bold">R$ {p.price_brl?.toFixed(0)}</td>
                    <td className="py-2 pr-4 text-right text-gray-300">
                      {p.tcgplayer_usd ? `$ ${p.tcgplayer_usd?.toFixed(2)}` : "—"}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-400">
                      {p.tcgplayer_brl ? `R$ ${p.tcgplayer_brl?.toFixed(0)}` : "—"}
                    </td>
                    <td className="py-2 text-right">
                      <DiffBadge pct={p.savings_pct} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {comparisons.length > 10 && (
            <button
              onClick={() => setShowAllComparisons(v => !v)}
              className="mt-3 text-xs text-gray-400 hover:text-white underline"
            >
              {showAllComparisons ? "Mostrar menos" : `Ver todos os ${comparisons.length} produtos`}
            </button>
          )}
        </section>
      )}

      {/* Best EV Boxes */}
      {data?.best_ev_boxes?.length > 0 && (
        <section>
          <h2 className="text-base md:text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Package size={16} className="text-pokemon-yellow" />
            Análise de EV — melhores caixas para abrir
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.best_ev_boxes.map((ev, i) => (
              <EVCard key={ev.product_id ?? i} ev={ev} />
            ))}
          </div>
        </section>
      )}

      {/* Info */}
      <div className="card bg-blue-950/40 border-blue-800 text-xs md:text-sm text-gray-300">
        <p className="font-semibold text-blue-300 mb-1">ℹ️ Como interpretar</p>
        <p>
          <span className="text-green-400 font-semibold">Diferença positiva</span> = mais barato no BR que importar do TCGPlayer pelo câmbio atual.{" "}
          <span className="text-red-400 font-semibold">Negativa</span> = mais caro aqui. Produtos JAP/CHN não têm dados TCGPlayer.
        </p>
        <p className="mt-1 text-gray-500">Câmbio: R$ {data?.exchange_rate?.toFixed(2)} / USD · EV = valor esperado ao abrir a caixa</p>
      </div>
    </div>
  );
}
