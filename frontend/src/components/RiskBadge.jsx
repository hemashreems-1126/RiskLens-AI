const styles = {
  LOW: 'bg-green-100 text-green-800 border-green-300',
  MEDIUM: 'bg-amber-100 text-amber-800 border-amber-300',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-300',
  CRITICAL: 'bg-red-100 text-red-800 border-red-300',
}

export default function RiskBadge({ level }) {
  if (!level) return null
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold border ${styles[level] || 'bg-gray-100 text-gray-800 border-gray-300'}`}>
      {level}
    </span>
  )
}
