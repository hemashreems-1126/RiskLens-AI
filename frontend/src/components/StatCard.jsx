export default function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-brand-600">{label}</p>
      <p className="text-2xl font-semibold text-brand-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-brand-600 mt-1">{sub}</p>}
    </div>
  )
}
