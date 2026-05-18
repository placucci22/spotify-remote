import { useEffect, useState } from "react";
import { getDashboard, refreshProducts } from "../api/client";
import StatCard from "../components/StatCard";
import EVCard from "../components/EVCard";
import RecommendationBadge from "../components/RecommendationBadge";
import {
  DollarSign,
  Package,
  TrendingUp,
  RefreshCw,
  Loader,
  Star,
} from "lucide-react";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    getDashboard()
      .then(setData)
      .catch(() => setError("Erro ao carregar dashboard. Backend rodando?"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refreshProducts();
    setTimeout(() => {
      load();
      setRefreshing(false);
    }, 5000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <Loader className="animate-spin mr-2" size={20} />
        Carregando dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
        <p className="text-red-400 font-semibold">{error}</p>
        <p className="text-gray-400 text-sm max-w-md">
          Certifique-se de que o backend está rodando:<br />
          <code className="bg-pokemon-card px-2 py-1 rounded text-pokemon-yellow text-xs">
            cd pokemon-dashboard/backend && uvicorn main:app --reload
          </code>
        </p>
        <button onClick={load} className="btn-primary text-sm">
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 text-sm">
            Análise de preços Pokémon TCG · Liga Pokémon vs EUA
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
          {refreshing ? "Atualizando..." : "Atualizar preços"}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Câmbio USD/BRL"
          value={`R$ ${data?.exchange_rate?.toFixed(2)}`}
          sub="Banco Central do Brasil"
          icon={DollarSign}
          color="text-green-400"
        />
        <StatCard
          title="Produtos monitorados"
          value={data?.total_products ?? "—"}
          sub={`${data?.total_sealed ?? 0} selados`}
          icon={Package}
          color="text-pokemon-yellow"
        />
        <StatCard
          title="Melhores deals"
          value={data?.best_deals?.length ?? 0}
          sub="mais barato que importar"
          icon={Star}
          color="text-pokemon-yellow"
        />
        <StatCard
          title="Atualizado"
          value={
            data?.last_updated
              ? new Date(data.last_updated).toLocaleTimeString("pt-BR", {
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : "—"
          }
          sub={
            data?.last_updated
              ? new Date(data.last_updated).toLocaleDateString("pt-BR")
              : ""
          }
          icon={RefreshCw}
          color="text-blue-400"
        />
      </div>

      {/* Best Deals */}
      {data?.best_deals?.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <TrendingUp size={18} className="text-green-400" />
            Melhores negócios vs importar
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-xs border-b border-pokemon-border">
                  <th className="text-left pb-2 pr-4">Produto</th>
                  <th className="text-right pb-2 pr-4">Preço BR</th>
                  <th className="text-right pb-2 pr-4">TCGPlayer USD</th>
                  <th className="text-right pb-2 pr-4">Custo importação</th>
                  <th className="text-right pb-2">Economia</th>
                </tr>
              </thead>
              <tbody>
                {data.best_deals.map((p) => (
                  <tr key={p.id} className="border-b border-pokemon-border/50 hover:bg-pokemon-card/50">
                    <td className="py-2 pr-4 font-medium text-white max-w-xs truncate">{p.name}</td>
                    <td className="py-2 pr-4 text-right text-gray-300">
                      R$ {p.price_brl?.toFixed(0)}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-300">
                      {p.tcgplayer_usd ? `$ ${p.tcgplayer_usd?.toFixed(0)}` : "—"}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-400 text-xs">
                      {p.import_cost_brl ? `R$ ${p.import_cost_brl?.toFixed(0)}` : "—"}
                      <span className="block text-gray-500">(com 60% imposto)</span>
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
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Package size={18} className="text-pokemon-yellow" />
            Análise de EV — melhores caixas
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.best_ev_boxes.map((ev, i) => (
              <EVCard key={ev.product_id ?? i} ev={ev} />
            ))}
          </div>
        </section>
      )}

      {/* Import tax explainer */}
      <div className="card bg-blue-950/40 border-blue-800 text-sm text-gray-300">
        <p className="font-semibold text-blue-300 mb-1">ℹ️ Como calculamos o custo de importação</p>
        <p>
          Aplicamos 60% sobre o preço em dólar (II + IOF + ICMS típico para produtos Pokémon enviados dos EUA).
          Se o preço no Liga Pokémon é menor que esse valor, está mais barato comprar aqui do que importar.
        </p>
        <p className="mt-1 text-gray-400 text-xs">
          Câmbio atual: R$ {data?.exchange_rate?.toFixed(2)} · Fator de importação: 1.60x
        </p>
      </div>
    </div>
  );
}
