import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Package,
  Calculator,
  ArrowLeftRight,
  Briefcase,
  Zap,
} from "lucide-react";

const links = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/products", icon: Package, label: "Produtos" },
  { to: "/ev", icon: Calculator, label: "Análise de EV" },
  { to: "/compare", icon: ArrowLeftRight, label: "BR vs EUA" },
  { to: "/portfolio", icon: Briefcase, label: "Portfolio" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 flex-shrink-0 bg-pokemon-card border-r border-pokemon-border flex flex-col">
      <div className="p-5 border-b border-pokemon-border">
        <div className="flex items-center gap-2">
          <Zap size={22} className="text-pokemon-yellow" />
          <span className="font-bold text-lg tracking-tight text-white">
            PokéPrice
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-1">Liga Pokémon · Dashboard</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-pokemon-red text-white"
                  : "text-gray-400 hover:text-white hover:bg-pokemon-border"
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-pokemon-border text-xs text-gray-500">
        Dados: Liga Pokémon · TCGPlayer · PriceCharting
      </div>
    </aside>
  );
}
