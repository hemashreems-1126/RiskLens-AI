import { useEffect, useState } from 'react'
import { api } from '../services/api'
import StatCard from '../components/StatCard'

export default function Evaluation() {
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getEvaluation().then(setMetrics).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="text-red-600">{error}</div>
  if (!metrics) return <div className="text-brand-600">Loading evaluation…</div>

  const cm = metrics.confusion_matrix

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-brand-900">Held-out Test Evaluation</h2>
      <p className="text-sm text-brand-700 bg-amber-50 border border-amber-200 rounded-md p-3">{metrics.disclaimer}</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Accuracy" value={metrics.accuracy} />
        <StatCard label="Precision" value={metrics.precision} />
        <StatCard label="Recall" value={metrics.recall} />
        <StatCard label="F1 Score" value={metrics.f1_score} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="False Positive Rate" value={metrics.false_positive_rate} />
        <StatCard label="Test Set Size" value={metrics.test_set_size} sub={`Train: ${metrics.train_set_size}`} />
        <StatCard label="Total Estimated Cost" value={`₹${metrics.total_estimated_cost.toLocaleString()}`} />
      </div>

      <div>
        <h3 className="text-sm font-semibold text-brand-900 mb-3">Confusion Matrix</h3>
        <div className="grid grid-cols-2 gap-3 max-w-md">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
            <p className="text-xs text-brand-600">True Positives</p>
            <p className="text-xl font-semibold">{cm.true_positives}</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
            <p className="text-xs text-brand-600">False Positives</p>
            <p className="text-xl font-semibold">{cm.false_positives}</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
            <p className="text-xs text-brand-600">False Negatives</p>
            <p className="text-xl font-semibold">{cm.false_negatives}</p>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
            <p className="text-xs text-brand-600">True Negatives</p>
            <p className="text-xl font-semibold">{cm.true_negatives}</p>
          </div>
        </div>
      </div>

      <p className="text-xs text-brand-600">{metrics.cost_assumptions.note} FP cost: ₹{metrics.cost_assumptions.false_positive_cost_per_case}/case, FN cost: ₹{metrics.cost_assumptions.false_negative_cost_per_case}/case.</p>
    </div>
  )
}
