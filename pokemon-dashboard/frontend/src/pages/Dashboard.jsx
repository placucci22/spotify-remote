import { useEffect, useState } from "react";
import { getDashboard, refreshProducts } from "../api/client";
import StatCard from "../components/StatCard";
import EVCard from "../components/EVCard";
import { DollarSign, Package, RefreshCw, Loader, Star } from "lucide-react";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

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
        <p className="text-gray-400 text-sm max-w-sm">
          Inicie o backend:<br />
          <code className="bg-pokemon-card px-2 py-1 rounded text-pokemon-yellow text-xs break-all">
            cd pokemon-dashboard/backend && uvicorn main:app --reload
          </code>
        </p>
        <button onClick={load} className="btn-primary text-sm">Tentar novamente</button>
      </div>
    );
  }

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
          title="Bons negócios"
          value={data?.best_deals?.length ?? 0}
          sub="mais baratos que importar"
          icon={Star}
          color="text-pokemon-yellow"
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

      {/* Best Deals */}
      {data?.best_deals?.length > 0 && (
        <section>
          <h2 className="text-base md:text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Star size={16} className="text-green-400" />
            Melhores negócios vs EUA
          </h2>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {data.best_deals.map((p) => (
              <div key={p.id} className="card flex justify-between items-center gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-semibold truncate">{p.name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Liga: <span className="text-pokemon-yellow font-bold">R$ {p.price_brl?.toFixed(0)}</span>
                    {p.tcgplayer_usd && <> · TCG: ${p.tcgplayer_usd?.toFixed(0)}</>}
                  </p>
                </div>
                {p.savings_pct != null && (
                  <span className={`text-sm font-bold flex-shrink-0 ${p.savings_pct > 0 ? "text-green-400" : "text-red-400"}`}>
                    {p.savings_pct > 0 ? "+" : ""}{p.savings_pct?.toFixed(1)}%
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Desktop table */}
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
                {data.best_deals.map((p) => (
                  <tr key={p.id} className="border-b border-pokemon-border/50 hover:bg-pokemon-card/50">
                    <td className="py-2 pr-4 font-medium text-white max-w-xs truncate">{p.name}</td>
                    <td className="py-2 pr-4 text-right text-pokemon-yellow font-bold">R$ {p.price_brl?.toFixed(0)}</td>
                    <td className="py-2 pr-4 text-right text-gray-300">
                      {p.tcgplayer_usd ? `$ ${p.tcgplayer_usd?.toFixed(0)}` : "—"}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-400">
                      {p.tcgplayer_brl ? `R$ ${p.tcgplayer_brl?.toFixed(0)}` : "—"}
                    </td>
                    <td className="py-2 text-right">
                      {p.savings_pct != null ? (
                        <span className={p.savings_pct > 0 ? "text-green-400 font-bold" : "text-red-400"}>
                          {p.savings_pct > 0 ? "+" : ""}{p.savings_pct?.toFixed(1)}%
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Best EV Boxes */}
      {data?.best_ev_boxes?.length > 0 && (
        <section>
          <h2 className="text-base md:text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Package size={16} className="text-pokemon-yellow" />
            Análise de EV — melhores caixas
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.best_ev_boxes.map((ev, i) => (
              <EVCard key={ev.product_id ?? i} ev={ev} />
            ))}
          </div>
        </section>
      )}

      {/* Exchange rate info */}
      <div className="card bg-blue-950/40 border-blue-800 text-xs md:text-sm text-gray-300">
        <p className="font-semibold text-blue-300 mb-1">ℹ️ Comparação de preços</p>
        <p>
          Comparamos o preço do Liga com o preço do TCGPlayer convertido pelo câmbio atual.
          Positivo = mais barato no BR. Negativo = mais caro no BR.
        </p>
        <p className="mt-1 text-gray-500 text-xs">
          Câmbio: R$ {data?.exchange_rate?.toFixed(2)} / USD
        </p>
      </div>
    </div>
  );
}
