import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import RiskBadge from '../components/RiskBadge'

export default function Investigations() {
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(null)
  const [params] = useSearchParams()
  const navigate = useNavigate()

  const load = () => api.listAlerts().then(setAlerts).catch((e) => setError(e.message))

  useEffect(() => { load() }, [])

  const investigate = async (alertId) => {
    setRunning(alertId)
    try {
      const inv = await api.startInvestigation(alertId)
      navigate(`/investigations/${inv.investigation_id}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(null)
    }
  }

  const highlighted = params.get('alert')

  if (error) return <div className="text-red-600">{error}</div>

  return (
    <div>
      <h2 className="text-lg font-semibold text-brand-900 mb-4">Investigations</h2>
      <div className="bg-white border border-gray-200 rounded-lg divide-y">
        {alerts.map((a) => (
          <div key={a.alert_id} className={`flex items-center justify-between p-4 ${a.alert_id === highlighted ? 'bg-amber-50' : ''}`}>
            <div>
              <p className="text-sm font-medium text-brand-900">₹{a.amount.toLocaleString()} · {a.transaction_type} · {a.payment_method}</p>
              <p className="text-xs text-brand-600">{a.flag_reason.join(' · ')}</p>
              <p className="text-xs text-brand-600">anomaly score {a.anomaly_score} · status {a.status}</p>
            </div>
            <div className="flex items-center gap-3">
              <RiskBadge level={a.initial_risk} />
              <button
                onClick={() => investigate(a.alert_id)}
                disabled={running === a.alert_id}
                className="text-sm px-3 py-1.5 rounded-md bg-brand-900 text-white hover:bg-brand-800 transition disabled:opacity-50"
              >
                {running === a.alert_id ? 'Investigating…' : 'Investigate'}
              </button>
            </div>
          </div>
        ))}
        {alerts.length === 0 && <p className="p-4 text-sm text-brand-600">No alerts yet — try resetting demo data from the dashboard.</p>}
      </div>
    </div>
  )
}
