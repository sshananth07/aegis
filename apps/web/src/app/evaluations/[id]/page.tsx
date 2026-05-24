"use client"

import { useQuery } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { Evaluation } from "@/types"
import { useRealtimeEvaluation } from "@/hooks/useRealtimeEvaluation"

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500"

  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{pct}%</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function EvaluationPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  useRealtimeEvaluation(id)

  const { data: evaluation, isLoading } = useQuery({
    queryKey: ["evaluation", id],
    queryFn: () => apiFetch<Evaluation>(`/evaluations/${id}`),
  })

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!evaluation) return <div className="p-8 text-gray-500">Not found</div>

  const scoreDetails = evaluation.score_details as Record<string, number | null> | null

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold">Evaluation Result</h1>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${statusColors[evaluation.status]}`}>
          {evaluation.status}
        </span>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="border rounded-lg p-4 bg-white text-center">
          <div className="text-2xl font-bold">
            {evaluation.score !== null ? `${Math.round(evaluation.score * 100)}%` : "—"}
          </div>
          <div className="text-xs text-gray-500 mt-1">Score</div>
        </div>
        <div className="border rounded-lg p-4 bg-white text-center">
          <div className="text-2xl font-bold">{evaluation.latency_ms ?? "—"}</div>
          <div className="text-xs text-gray-500 mt-1">Latency (ms)</div>
        </div>
        <div className="border rounded-lg p-4 bg-white text-center">
          <div className="text-2xl font-bold">{evaluation.token_usage ?? "—"}</div>
          <div className="text-xs text-gray-500 mt-1">Tokens</div>
        </div>
        <div className="border rounded-lg p-4 bg-white text-center">
          <div className="text-2xl font-bold">
            {evaluation.cost ? `$${evaluation.cost.toFixed(4)}` : "—"}
          </div>
          <div className="text-xs text-gray-500 mt-1">Cost</div>
        </div>
      </div>

      {/* Score Breakdown */}
      {scoreDetails && Object.values(scoreDetails).some(v => v !== null) && (
        <div className="border rounded-lg p-6 bg-white mb-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Score Breakdown</h2>
          <ScoreBar label="JSON Validity" value={scoreDetails.json_validity} />
          <ScoreBar label="Exact Match" value={scoreDetails.exact_match} />
          <ScoreBar label="Semantic Similarity" value={scoreDetails.semantic_similarity} />
        </div>
      )}

      {/* Provider */}
      <div className="border rounded-lg p-4 bg-white mb-4">
        <div className="text-xs text-gray-500 mb-1">Provider</div>
        <div className="font-medium capitalize">{evaluation.provider}</div>
      </div>
      
      {/* View Traces Link */}
      <div className="border rounded-lg p-4 bg-white mb-4">
        <div className="flex items-center justify-between">
          <div className="text-xs text-gray-500">Execution Traces</div>
          <button
            className="text-xs text-blue-500 hover:text-blue-700 flex items-center gap-1"
            onClick={() => router.push(`/traces/${evaluation.id}`)}
          >
            View trace →
          </button>
        </div>
      </div>

      {/* Response */}
      <div className="border rounded-lg p-4 bg-white">
        <div className="text-xs text-gray-500 mb-2">Response</div>
        {evaluation.response ? (
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{evaluation.response}</p>
        ) : (
          <p className="text-sm text-gray-400 italic">
            {evaluation.status === "running" ? "Waiting for response..." : "No response"}
          </p>
        )}
      </div>
    </div>
  )
}