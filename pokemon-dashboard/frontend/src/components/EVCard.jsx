import RecommendationBadge from "./RecommendationBadge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

function ProfitBar({ pct }) {
  const clamped = Math.max(-100, Math.min(100, pct));
  const isPositive = clamped >= 0;
  const width = Math.abs(clamped);
  return (
    <div className="w-full bg-gray-700 rounded-full h-2 mt-1">
      <div
        className={`h-2 rounded-full transition-all ${isPositive ? "bg-green-500" : "bg-red-500"}`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export default function EVCard({ ev }) {
  const isPositive = ev.expected_profit_loss_brl >= 0;
  const TrendIcon =
    ev.sealed_trend === "INCREASING"
      ? TrendingUp
      : ev.sealed_trend === "DECREASING"
      ? TrendingDown
      : Minus;

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-white text-sm leading-tight">
            {ev.set_name || ev.product_name}
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {ev.packs_per_box} packs · R$ {ev.pack_price_brl?.toFixed(2)}/pack
          </p>
        </div>
        <RecommendationBadge value={ev.recommendation} />
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-gray-400 text-xs">Preço da caixa</p>
          <p className="font-bold text-white">R$ {ev.price_brl?.toFixed(0) ?? ev.box_price_brl?.toFixed(0)}</p>
        </div>
        <div>
          <p className="text-gray-400 text-xs">EV estimado</p>
          <p className="font-bold text-white">R$ {ev.ev_per_box_brl?.toFixed(0)}</p>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">Lucro/Prejuízo esperado</span>
          <span className={isPositive ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
            {isPositive ? "+" : ""}R$ {ev.expected_profit_loss_brl?.toFixed(0)} ({ev.expected_profit_loss_pct?.toFixed(1)}%)
          </span>
        </div>
        <ProfitBar pct={ev.expected_profit_loss_pct} />
      </div>

      {ev.notable_pulls?.length > 0 && (
        <div>
          <p className="text-gray-400 text-xs mb-1">Pulls de destaque</p>
          <div className="space-y-1">
            {ev.notable_pulls.slice(0, 3).map((card, i) => (
              <div key={i} className="flex justify-between text-xs">
                <span className="text-gray-300 truncate max-w-[70%]">{card.name}</span>
                <span className="text-pokemon-yellow font-semibold">
                  ${card.price_usd?.toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-gray-500 italic border-t border-pokemon-border pt-2">
        {ev.recommendation_reason}
      </p>
    </div>
  );
}
