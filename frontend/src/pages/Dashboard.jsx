import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import StatCard from '../components/StatCard'
import RiskBadge from '../components/RiskBadge'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState(null)
  const [resetting, setResetting] = useState(false)

  const load = async () => {
    try {
      const [s, a] = await Promise.all([api.dashboardSummary(), api.listAlerts()])
      setSummary(s)
      setAlerts(a.slice(0, 8))
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => { load() }, [])

  const handleReset = async () => {
    setResetting(true)
    try {
      await api.demoReset()
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setResetting(false)
    }
  }

  if (error) return <div className="text-red-600">Could not reach the backend: {error}</div>
  if (!summary) return <div className="text-brand-600">Loading dashboard…</div>

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-brand-900">Risk Operations Dashboard</h2>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="text-sm px-3 py-1.5 rounded-md border border-brand-700 text-brand-700 hover:bg-brand-700 hover:text-white transition disabled:opacity-50"
        >
          {resetting ? 'Resetting…' : 'Reset demo data'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Total Transactions" value={summary.total_transactions} />
        <StatCard label="Suspicious" value={summary.suspicious_transactions} />
        <StatCard label="High Risk" value={summary.high_risk} />
        <StatCard label="Blocked" value={summary.blocked} />
        <StatCard label="Pending Review" value={summary.pending_review} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Fraud Precision" value={summary.fraud_precision} />
        <StatCard label="Fraud Recall" value={summary.fraud_recall} />
        <StatCard label="F1 Score" value={summary.f1_score} />
        <StatCard label="False Positive Rate" value={summary.false_positive_rate} sub={`Est. cost ₹${summary.false_positive_cost}`} />
      </div>

      <div>
        <h3 className="text-sm font-semibold text-brand-900 mb-3">Open alerts — click to investigate</h3>
        <div className="bg-white border border-gray-200 rounded-lg divide-y">
          {alerts.length === 0 && <p className="p-4 text-sm text-brand-600">No open alerts.</p>}
          {alerts.map((a) => (
            <Link
              key={a.alert_id}
              to={`/investigations?alert=${a.alert_id}`}
              className="flex items-center justify-between p-4 hover:bg-brand-50 transition"
            >
              <div>
                <p className="text-sm font-medium text-brand-900">₹{a.amount.toLocaleString()} · {a.transaction_type}</p>
                <p className="text-xs text-brand-600">{a.flag_reason.join(' · ')}</p>
              </div>
              <RiskBadge level={a.initial_risk} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
