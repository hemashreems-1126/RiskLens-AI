import { useState } from 'react'
import { api } from '../services/api'

export default function Audit() {
  const [invId, setInvId] = useState('')
  const [logs, setLogs] = useState(null)
  const [error, setError] = useState(null)

  const search = async () => {
    setError(null)
    try {
      const data = await api.getAudit(invId)
      setLogs(data)
    } catch (e) {
      setError(e.message)
      setLogs(null)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-brand-900">Audit Trail Lookup</h2>
      <div className="flex gap-2">
        <input
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm"
          placeholder="Paste an investigation ID (from its URL) to view its full audit trail"
          value={invId}
          onChange={(e) => setInvId(e.target.value)}
        />
        <button onClick={search} className="px-4 py-2 rounded-md bg-brand-900 text-white text-sm hover:bg-brand-800">Look up</button>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {logs && (
        <div className="bg-white border border-gray-200 rounded-lg divide-y">
          {logs.map((l, i) => (
            <div key={i} className="p-3 text-sm">
              <div className="flex justify-between">
                <span className="font-medium text-brand-900">{l.stage}</span>
                <span className="text-xs text-brand-600">{l.timestamp}</span>
              </div>
              <p className="text-xs text-brand-700">actor: {l.actor} · action: {l.action}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
