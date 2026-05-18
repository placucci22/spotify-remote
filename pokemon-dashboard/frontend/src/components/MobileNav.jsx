import { NavLink } from "react-router-dom";
import { NAV_LINKS } from "./Sidebar";

export default function MobileNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-pokemon-card border-t border-pokemon-border flex justify-around items-stretch h-16">
      {NAV_LINKS.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center flex-1 gap-1 text-[10px] font-medium transition-colors ${
              isActive ? "text-pokemon-yellow" : "text-gray-500"
            }`
          }
        >
          <Icon size={20} />
          <span className="leading-none">{label.split(" ")[0]}</span>
        </NavLink>
      ))}
    </nav>
  );
}
