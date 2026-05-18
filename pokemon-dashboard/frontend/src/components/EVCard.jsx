import RecommendationBadge from "./RecommendationBadge";

const RARITY_SHORT = {
  "Special Illustration Rare": "SAR",
  "Hyper Rare": "HR",
  "Illustration Rare": "IR",
  "Ultra Rare": "UR",
  "Double Rare": "DR",
  "Rare Holo": "RH",
  "Rare": "R",
};

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

function formatOdds(pullRate) {
  if (!pullRate) return null;
  if (pullRate >= 1) return `~${pullRate.toFixed(1)}×/cx`;
  return `1 em ${Math.round(1 / pullRate)} cx`;
}

export default function EVCard({ ev, exchangeRate }) {
  const isPositive = ev.expected_profit_loss_brl >= 0;
  const boxPrice = ev.price_brl ?? ev.box_price_brl;

  return (
    <div className="card flex flex-col gap-3">
      {/* Header */}
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

      {/* Box price + EV */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-gray-400 text-xs">Preço da caixa</p>
          <p className="font-bold text-white">R$ {boxPrice?.toFixed(0)}</p>
        </div>
        <div>
          <p className="text-gray-400 text-xs">EV estimado</p>
          <p className="font-bold text-white">R$ {ev.ev_per_box_brl?.toFixed(0)}</p>
        </div>
      </div>

      {/* Profit bar */}
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">Lucro/Prejuízo esperado</span>
          <span className={isPositive ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
            {isPositive ? "+" : ""}R$ {ev.expected_profit_loss_brl?.toFixed(0)} ({ev.expected_profit_loss_pct?.toFixed(1)}%)
          </span>
        </div>
        <ProfitBar pct={ev.expected_profit_loss_pct} />
      </div>

      {/* Notable pulls with odds */}
      {ev.notable_pulls?.length > 0 && (
        <div>
          <p className="text-gray-400 text-xs font-medium mb-1.5">Pulls de destaque</p>
          <div className="space-y-1.5">
            {ev.notable_pulls.map((card, i) => {
              const priceBrl = exchangeRate && card.price_usd
                ? `R$ ${(card.price_usd * exchangeRate).toFixed(0)}`
                : null;
              const odds = formatOdds(card.pull_rate);
              const rarityShort = RARITY_SHORT[card.rarity] ?? card.rarity;
              return (
                <div key={i} className="bg-pokemon-bg rounded-lg px-2.5 py-1.5">
                  <div className="flex items-start justify-between gap-1">
                    <span className="text-gray-200 text-xs font-medium leading-snug flex-1 min-w-0">
                      {card.name}
                    </span>
                    <span className="text-pokemon-yellow text-xs font-bold flex-shrink-0 ml-1">
                      ${card.price_usd?.toFixed(0)}
                      {priceBrl && <span className="text-gray-400 font-normal"> · {priceBrl}</span>}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    {rarityShort && (
                      <span className="text-[10px] text-purple-400 font-semibold">{rarityShort}</span>
                    )}
                    {odds && (
                      <span className="text-[10px] text-blue-400">{odds}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <p className="text-xs text-gray-500 italic border-t border-pokemon-border pt-2">
        {ev.recommendation_reason}
      </p>
    </div>
  );
}
