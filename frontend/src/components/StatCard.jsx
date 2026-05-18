export default function StatCard({ title, value, sub, icon: Icon, color = "text-pokemon-yellow" }) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">{title}</p>
        {Icon && <Icon size={16} className={color} />}
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </div>
  );
}
