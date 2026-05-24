"use client"

import { useQuery } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { Activity, Clock } from "lucide-react"

interface Trace {
  id: string
  evaluation_id: string
  event_type: string
  provider: string | null
  latency_ms: number | null
  metadata_: Record<string, unknown> | null
  timestamp: string
}

interface Evaluation {
  id: string
  provider: string
  status: string
  score: number | null
  latency_ms: number | null
  token_usage: number | null
  token_usage_estimated: boolean | null
  cost: number | null
  response: string | null
  created_at: string
}

const eventColors: Record<string, string> = {
  evaluation_created: "bg-blue-500",
  provider_selected: "bg-purple-500",
  provider_succeeded: "bg-green-500",
  provider_failed: "bg-red-500",
  retry_triggered: "bg-yellow-500",
  fallback_triggered: "bg-orange-500",
  scoring_completed: "bg-teal-500",
  review_triggered: "bg-pink-500",
  evaluation_completed: "bg-green-600",
  evaluation_failed: "bg-red-600",
  review_completed: "bg-blue-600",
}

const statusColors: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  running: "bg-blue-100 text-blue-800",
  review_required: "bg-orange-100 text-orange-800",
  queued: "bg-gray-100 text-gray-800",
}

const failureEvents = new Set([
  "provider_failed",
  "retry_triggered",
  "fallback_triggered",
  "review_triggered",
  "evaluation_failed",
])

const reviewEvents = new Set([
  "review_triggered",
  "review_completed",
])

function TraceEvent({ trace, index, total }: {
  trace: Trace
  index: number
  total: number
}) {
  const color = eventColors[trace.event_type] || "bg-gray-400"
  const isLast = index === total - 1

  return (
    <div className="flex gap-4">
      {/* Timeline */}
      <div className="flex flex-col items-center">
        <div className={`w-3 h-3 rounded-full ${color} shrink-0 mt-1`} />
        {!isLast && <div className="w-0.5 bg-gray-200 flex-1 mt-1" />}
      </div>

      {/* Content */}
      <div className={`pb-6 flex-1 ${isLast ? "" : ""}`}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{trace.event_type}</span>
            {trace.provider && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
                {trace.provider}
              </span>
            )}
            {trace.latency_ms && (
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Clock size={10} />
                {trace.latency_ms}ms
              </span>
            )}
          </div>
          <span className="text-xs text-gray-400">
            {new Date(trace.timestamp).toLocaleTimeString()}
          </span>
        </div>

        {/* Metadata */}
        {trace.metadata_ && Object.keys(trace.metadata_).length > 0 && (
          <div className="bg-gray-50 rounded-lg p-3 mt-2">
            {Object.entries(trace.metadata_).map(([key, value]) => {
              if (value === null || value === undefined) return null
              if (Array.isArray(value) && value.length === 0) return null
              return (
                <div key={key} className="flex gap-2 text-xs mb-1 last:mb-0">
                  <span className="text-gray-500 shrink-0">{key}:</span>
                  <span className="text-gray-700 font-mono">
                    {typeof value === "object"
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default function TraceViewerPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const { data: evaluation, isLoading: evalLoading } = useQuery({
    queryKey: ["evaluation", id],
    queryFn: () => apiFetch<Evaluation>(`/evaluations/${id}`),
  })

  const { data: traces, isLoading: tracesLoading } = useQuery({
    queryKey: ["traces", id],
    queryFn: () => apiFetch<Trace[]>(`/evaluations/${id}/traces`),
  })

  if (evalLoading || tracesLoading) {
    return <div className="p-8 text-gray-500">Loading...</div>
  }

  if (!evaluation) {
    return <div className="p-8 text-gray-500">Evaluation not found</div>
  }

  // Compute total duration
  const firstTrace = traces?.[0]
  const lastTrace = traces?.[traces.length - 1]
  const totalDuration =
    firstTrace && lastTrace
      ? new Date(lastTrace.timestamp).getTime() -
        new Date(firstTrace.timestamp).getTime()
      : null
  const failureTimeline = (traces || []).filter((trace) =>
    failureEvents.has(trace.event_type)
  )
  const reviewTimeline = (traces || []).filter((trace) =>
    reviewEvents.has(trace.event_type)
  )

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <button
        className="text-sm text-gray-500 hover:text-black mb-6"
        onClick={() => router.back()}
      >
        ← Back
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Activity size={20} className="text-green-500" />
        <h1 className="text-2xl font-bold">Trace Viewer</h1>
        <span
          className={`text-xs px-2 py-1 rounded-full font-medium ${
            statusColors[evaluation.status] || "bg-gray-100 text-gray-800"
          }`}
        >
          {evaluation.status}
        </span>
      </div>

      {/* Evaluation Summary */}
      <div className="bg-white border rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">
          Evaluation Summary
        </h2>
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-xl font-bold">
              {evaluation.score !== null
                ? `${Math.round(evaluation.score * 100)}%`
                : "—"}
            </div>
            <div className="text-xs text-gray-500 mt-1">Score</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold">
              {evaluation.latency_ms ?? "—"}
            </div>
            <div className="text-xs text-gray-500 mt-1">Latency (ms)</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold">
              {evaluation.token_usage ?? "—"}
              {evaluation.token_usage_estimated && (
                <span className="text-yellow-500 text-sm ml-1">~</span>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-1">Tokens</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold capitalize">
              {evaluation.provider}
            </div>
            <div className="text-xs text-gray-500 mt-1">Provider</div>
          </div>
        </div>
        {totalDuration !== null && (
          <div className="mt-4 pt-4 border-t text-center">
            <span className="text-xs text-gray-500">
              Total execution time:{" "}
              <span className="font-medium">{totalDuration}ms</span>
            </span>
          </div>
        )}
      </div>

      {/* Response */}
      {evaluation.response && (
        <div className="bg-white border rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Response
          </h2>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {evaluation.response}
          </p>
        </div>
      )}

      {/* Trace Timeline */}
      <div className="bg-white border rounded-xl p-5">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-semibold text-gray-700">
            Execution Timeline
          </h2>
          <span className="text-xs text-gray-400">
            {traces?.length ?? 0} events
          </span>
        </div>

        {traces && traces.length > 0 ? (
          <div>
            {traces.map((trace, i) => (
              <TraceEvent
                key={trace.id}
                trace={trace}
                index={i}
                total={traces.length}
              />
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">
            No trace events found
          </p>
        )}
      </div>

      {/* Failure Timeline */}
      <div className="bg-white border rounded-xl p-5 mt-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-semibold text-gray-700">
            Failure Timeline
          </h2>
          <span className="text-xs text-gray-400">
            {failureTimeline.length} events
          </span>
        </div>

        {failureTimeline.length > 0 ? (
          <div>
            {failureTimeline.map((trace, i) => (
              <TraceEvent
                key={trace.id}
                trace={trace}
                index={i}
                total={failureTimeline.length}
              />
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">
            No failure events recorded for this evaluation.
          </p>
        )}
      </div>

      {/* Review Workflow Timeline */}
      <div className="bg-white border rounded-xl p-5 mt-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-semibold text-gray-700">
            Review Workflow Timeline
          </h2>
          <span className="text-xs text-gray-400">
            {reviewTimeline.length} events
          </span>
        </div>

        {reviewTimeline.length > 0 ? (
          <div>
            {reviewTimeline.map((trace, i) => (
              <TraceEvent
                key={trace.id}
                trace={trace}
                index={i}
                total={reviewTimeline.length}
              />
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">
            No review workflow events recorded for this evaluation.
          </p>
        )}
      </div>
    </div>
  )
}
