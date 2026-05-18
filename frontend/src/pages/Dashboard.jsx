import { useEffect, useState } from "react";
import { getDashboard, refreshProducts } from "../api/client";
import StatCard from "../components/StatCard";
import EVCard from "../components/EVCard";
import { DollarSign, Package, RefreshCw, Loader, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    getDashboard()
      .then(setData)
      .catch(() => setError("Erro ao carregar dados."))
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
      </div>

      {/* Quick link to comparison page */}
      <Link
        to="/compare"
        className="flex items-center justify-between card hover:bg-pokemon-card/80 transition-colors group"
      >
        <div>
          <p className="text-white font-semibold text-sm">Ver comparação BR vs EUA</p>
          <p className="text-gray-400 text-xs mt-0.5">
            Preços TCGPlayer convertidos · câmbio R$ {data?.exchange_rate?.toFixed(2)}/USD
          </p>
        </div>
        <ArrowRight size={18} className="text-gray-400 group-hover:text-white flex-shrink-0" />
      </Link>

      {/* EV Analysis */}
      {data?.best_ev_boxes?.length > 0 && (
        <section>
          <h2 className="text-base md:text-lg font-semibold text-white mb-1 flex items-center gap-2">
            <Package size={16} className="text-pokemon-yellow" />
            Análise de EV — melhores caixas para abrir
          </h2>
          <p className="text-xs text-gray-500 mb-3">
            EV positivo = abre a caixa · EV negativo = guarda selado
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.best_ev_boxes.map((ev, i) => (
              <EVCard key={ev.product_id ?? ev.id ?? i} ev={ev} />
            ))}
          </div>
        </section>
      )}

      {/* Info */}
      <div className="card bg-blue-950/40 border-blue-800 text-xs text-gray-400">
        <p className="text-blue-300 font-semibold mb-1">ℹ️ Sobre os dados</p>
        <p>
          Preços do ligapokemon.com.br. EV calculado com pull rates e preços TCGPlayer estáticos.
          Atualizado: {data?.last_updated ? new Date(data.last_updated).toLocaleString("pt-BR") : "—"}
        </p>
      </div>
    </div>
  );
}
