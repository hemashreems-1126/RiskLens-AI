import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function Transactions() {
  const [txns, setTxns] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listTransactions().then(setTxns).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="text-red-600">{error}</div>

  return (
    <div>
      <h2 className="text-lg font-semibold text-brand-900 mb-4">Transactions</h2>
      <div className="overflow-x-auto bg-white border border-gray-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-brand-50 text-brand-700 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Account</th>
              <th className="text-left px-4 py-2">Amount</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">Method</th>
              <th className="text-left px-4 py-2">Location</th>
              <th className="text-left px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {txns.map((t) => (
              <tr key={t.transaction_id} className={t.is_fraud ? 'bg-red-50' : ''}>
                <td className="px-4 py-2 font-mono text-xs">{t.account_id}</td>
                <td className="px-4 py-2">₹{t.amount.toLocaleString()}</td>
                <td className="px-4 py-2">{t.transaction_type}</td>
                <td className="px-4 py-2">{t.payment_method}</td>
                <td className="px-4 py-2">{t.location}</td>
                <td className="px-4 py-2">{t.transaction_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-brand-600 mt-2">Rows highlighted red carry the synthetic ground-truth fraud label (for evaluation only — not shown to the investigation agents).</p>
    </div>
  )
}
