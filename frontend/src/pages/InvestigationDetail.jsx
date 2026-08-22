import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../services/api'
import RiskBadge from '../components/RiskBadge'
import DecisionBadge from '../components/DecisionBadge'

const STAGE_LABELS = {
  planner: '1. Planner',
  evidence_agent: '2. Evidence Agent',
  behavior_agent: '3. Behavior Agent',
  network_agent: '4. Network Agent',
  compliance_agent: '5. Compliance Agent',
  risk_assessment: '6. Risk Assessment',
  decision_agent: '7. Decision',
  explainability_agent: '8. Explainability',
  audit_report: '9. Audit Report',
}

const SIGNAL_LABELS = {
  anomaly_score: 'Anomaly Score',
  behavior_anomaly: 'Behavior Anomaly',
  velocity_anomaly: 'Velocity Anomaly',
  amount_deviation: 'Amount Deviation',
  balance_drain: 'Balance Drain',
  network_risk: 'Network Risk',
  rule_violations: 'Rule Violations',
}

function formatValue(value) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') return Number(value.toFixed(3))
  if (value === null || value === undefined) return '—'
  return String(value)
}

function EvidenceCard({ title, detail }) {
  if (!detail || typeof detail !== 'object') return null

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-brand-900 mb-3">
        {title}
      </h4>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(detail).map(([key, value]) => (
          <div key={key} className="bg-brand-50 rounded-md p-3">
            <p className="text-xs text-brand-600 mb-1">
              {key.replaceAll('_', ' ')}
            </p>

            <p className="text-sm font-medium text-brand-900">
              {formatValue(value)}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function InvestigationDetail() {
  const { id } = useParams()

  const [inv, setInv] = useState(null)
  const [error, setError] = useState(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState(false)

  const load = () =>
    api
      .getInvestigation(id)
      .then(setInv)
      .catch((e) => setError(e.message))

  useEffect(() => {
    load()
  }, [id])

  const review = async (decision) => {
    setSubmitting(true)

    try {
      await api.reviewInvestigation(id, decision, notes)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const feedback = async (wasCorrect) => {
    try {
      await api.submitFeedback(id, wasCorrect, '')
      setFeedbackSent(true)
    } catch (e) {
      setError(e.message)
    }
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    )
  }

  if (!inv) {
    return (
      <div className="text-brand-600">
        Loading investigation…
      </div>
    )
  }

  const riskEvent = inv.agent_events?.find(
    (e) => e.agent_name === 'risk_assessment'
  )

  const riskBreakdown = riskEvent?.detail?.breakdown || {}

  const evidenceEvents = inv.agent_events?.filter((e) =>
    [
      'evidence_agent',
      'behavior_agent',
      'network_agent',
      'compliance_agent',
    ].includes(e.agent_name)
  )

  return (
    <div className="space-y-6">

      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-brand-900">
            Investigation Case
          </h2>

          <p className="text-xs text-brand-600 mt-1">
            Case ID: {inv.case_id}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <RiskBadge level={inv.risk_level} />

          <DecisionBadge decision={inv.decision} />

          {inv.llm_mode === 'mock' && (
            <span className="text-xs px-2 py-1 rounded bg-gray-200 text-gray-700">
              AI reasoning: offline/mock
            </span>
          )}

          {inv.llm_mode === 'live' && (
            <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-700">
              AI reasoning: Groq live
            </span>
          )}
        </div>
      </div>

      {/* RISK SUMMARY */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-brand-600">
            Risk Score
          </p>

          <p className="text-3xl font-bold text-brand-900 mt-1">
            {inv.risk_score ?? '—'}
            <span className="text-sm font-normal text-brand-600">
              /100
            </span>
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-brand-600">
            Risk Level
          </p>

          <div className="mt-2">
            <RiskBadge level={inv.risk_level} />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-brand-600">
            Investigation Loops
          </p>

          <p className="text-2xl font-bold text-brand-900 mt-1">
            {inv.loops_used}
          </p>
        </div>

      </div>

      {/* AI EXPLANATION */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-sm font-semibold text-brand-900 mb-2">
          Why was this transaction flagged?
        </h3>

        <p className="text-sm text-brand-700 leading-6">
          {inv.explanation || 'No explanation available.'}
        </p>
      </div>

      {/* RISK FACTOR BREAKDOWN */}
      {Object.keys(riskBreakdown).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-brand-900 mb-3">
            Risk Factor Breakdown
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(riskBreakdown).map(([key, value]) => (
              <div
                key={key}
                className="bg-white border border-gray-200 rounded-lg p-4"
              >
                <p className="text-xs text-brand-600">
                  {SIGNAL_LABELS[key] || key.replaceAll('_', ' ')}
                </p>

                <p className="text-xl font-semibold text-brand-900 mt-1">
                  {value}
                </p>

                <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-700 rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(0, value))}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AGENT EVIDENCE */}
      {evidenceEvents?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-brand-900 mb-3">
            Investigation Evidence
          </h3>

          <div className="space-y-3">
            {evidenceEvents.map((event, index) => (
              <div key={index}>

                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">

                    <h4 className="text-sm font-semibold text-brand-900">
                      {STAGE_LABELS[event.agent_name] ||
                        event.agent_name}
                    </h4>

                    <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-700">
                      {event.status}
                    </span>

                  </div>

                  <p className="text-sm text-brand-700 mb-3">
                    {event.finding_summary}
                  </p>

                  {event.detail && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Object.entries(event.detail).map(
                        ([key, value]) => (
                          <div
                            key={key}
                            className="bg-brand-50 rounded-md p-3"
                          >
                            <p className="text-xs text-brand-600">
                              {key.replaceAll('_', ' ')}
                            </p>

                            <p className="text-sm font-medium text-brand-900 mt-1">
                              {formatValue(value)}
                            </p>
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>

              </div>
            ))}
          </div>
        </div>
      )}

      {/* INVESTIGATION TIMELINE */}
      <div>
        <h3 className="text-sm font-semibold text-brand-900 mb-3">
          Investigation Timeline
        </h3>

        <div className="space-y-2">

          {inv.agent_events?.map((event, index) => (
            <div
              key={index}
              className="bg-white border border-gray-200 rounded-lg p-4"
            >

              <div className="flex items-center justify-between">

                <p className="text-sm font-medium text-brand-900">
                  {STAGE_LABELS[event.agent_name] ||
                    event.agent_name}
                </p>

                <span className="text-xs text-brand-600">
                  {event.status}
                </span>

              </div>

              <p className="text-xs text-brand-700 mt-1">
                {event.finding_summary}
              </p>

            </div>
          ))}

        </div>
      </div>

      {/* HUMAN REVIEW */}
      {inv.status === 'awaiting_review' && (
        <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-3">

          <div>
            <p className="text-sm font-semibold text-brand-900">
              Human Review Required
            </p>

            <p className="text-xs text-brand-600 mt-1">
              The system has routed this case to a human because the
              risk requires additional review.
            </p>
          </div>

          <textarea
            className="w-full text-sm border border-gray-300 rounded-md p-3"
            placeholder="Reviewer notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          <div className="flex gap-2 flex-wrap">

            <button
              disabled={submitting}
              onClick={() => review('ALLOW')}
              className="px-4 py-2 rounded-md bg-green-600 text-white text-sm hover:bg-green-700 disabled:opacity-50"
            >
              Allow
            </button>

            <button
              disabled={submitting}
              onClick={() => review('BLOCK')}
              className="px-4 py-2 rounded-md bg-red-600 text-white text-sm hover:bg-red-700 disabled:opacity-50"
            >
              Block
            </button>

            <button
              disabled={submitting}
              onClick={() => review('ESCALATE')}
              className="px-4 py-2 rounded-md bg-amber-500 text-white text-sm hover:bg-amber-600 disabled:opacity-50"
            >
              Escalate
            </button>

          </div>
        </div>
      )}

      {/* FEEDBACK */}
      {inv.status === 'completed' && !feedbackSent && (
        <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-3">

          <div>
            <p className="text-sm font-semibold text-brand-900">
              Was this decision correct?
            </p>

            <p className="text-xs text-brand-600 mt-1">
              Your feedback is stored for evaluation.
            </p>
          </div>

          <div className="flex gap-2">

            <button
              onClick={() => feedback(true)}
              className="px-4 py-2 rounded-md border border-green-600 text-green-700 text-sm hover:bg-green-50"
            >
              Yes, correct
            </button>

            <button
              onClick={() => feedback(false)}
              className="px-4 py-2 rounded-md border border-red-600 text-red-700 text-sm hover:bg-red-50"
            >
              No, incorrect
            </button>

          </div>

        </div>
      )}

      {feedbackSent && (
        <p className="text-sm text-green-700">
          ✓ Feedback recorded — thank you.
        </p>
      )}

    </div>
  )
}