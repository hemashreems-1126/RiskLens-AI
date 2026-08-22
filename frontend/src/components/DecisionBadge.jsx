const styles = {
  ALLOW: 'bg-green-600 text-white',
  REVIEW: 'bg-amber-500 text-white',
  BLOCK: 'bg-red-600 text-white',
}

export default function DecisionBadge({ decision }) {
  if (!decision) return <span className="text-xs text-brand-600">pending</span>
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${styles[decision] || 'bg-gray-500 text-white'}`}>
      {decision}
    </span>
  )
}
