const BADGE_MAP = {
  "COMPRA FORTE": "badge-buy-strong",
  COMPRA: "badge-buy",
  NEUTRO: "badge-neutral",
  AGUARDAR: "badge-wait",
  EVITAR: "badge-avoid",
  OPEN: "badge-open",
  OPEN_OR_SELL: "badge-open",
  KEEP_SEALED: "badge-hold",
  BUY_AND_HOLD: "badge-buy",
  AVOID: "badge-avoid",
  "ÓTIMO NEGÓCIO": "badge-buy-strong",
  "BOM NEGÓCIO": "badge-buy",
  "PREÇO JUSTO": "badge-neutral",
  "LIGEIRAMENTE CARO": "badge-wait",
  CARO: "badge-avoid",
  "Sem dados EUA": "bg-gray-600 text-white text-xs font-bold px-2 py-1 rounded-full",
};

const LABEL_MAP = {
  OPEN: "ABRIR",
  OPEN_OR_SELL: "ABRIR / VENDER",
  KEEP_SEALED: "GUARDAR SELADO",
  BUY_AND_HOLD: "COMPRAR E GUARDAR",
  AVOID: "EVITAR",
  "COMPRA FORTE": "COMPRA FORTE ⭐",
  COMPRA: "COMPRAR",
  NEUTRO: "NEUTRO",
  AGUARDAR: "AGUARDAR",
  EVITAR: "EVITAR",
};

export default function RecommendationBadge({ value, className = "" }) {
  if (!value) return null;
  const cls = BADGE_MAP[value] || "badge-neutral";
  const label = LABEL_MAP[value] || value;
  return <span className={`${cls} ${className}`}>{label}</span>;
}
