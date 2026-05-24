"use client"

import { useQuery } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { BenchmarkRun, BenchmarkResult } from "@/types"
import {
  CheckCircle, XCircle, AlertTriangle,
  ChevronDown, ChevronUp
} from "lucide-react"
import { useState } from "react"
import { useRealtimeBenchmarkRun } from "@/hooks/useRealtimeBenchmarkRun"

interface ProviderSummaryStats {
  pass_rate: number
  avg_score: number
  avg_latency_ms: number
  passed_cases: number
  total_cases: number
}

const statusColors: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  running: "bg-blue-100 text-blue-800",
  partially_completed: "bg-yellow-100 text-yellow-800",
}

function ResultCard({ result }: { result: BenchmarkResult }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`bg-white border rounded-xl overflow-hidden ${
        result.passed ? "border-l-4 border-l-green-500" : "border-l-4 border-l-red-500"
      }`}
    >
      <div
        className="p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {result.passed ? (
              <CheckCircle size={16} className="text-green-500 shrink-0" />
            ) : (
              <XCircle size={16} className="text-red-500 shrink-0" />
            )}
            <div>
              <div className="text-sm font-medium">{result.input}</div>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-gray-500 capitalize">
                  {result.provider}
                </span>
                <span className="text-xs text-gray-500">
                  score: {Math.round(result.score * 100)}%
                </span>
                <span className="text-xs text-gray-500">
                  {result.latency_ms}ms
                </span>
                {result.divergence_detected && (
                  <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                    <AlertTriangle size={10} />
                    divergence
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {result.failure_reasons?.length > 0 && (
              <div className="flex gap-1">
                {result.failure_reasons.map((r) => (
                  <span
                    key={r}
                    className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full"
                  >
                    {r}
                  </span>
                ))}
              </div>
            )}
            {expanded ? (
              <ChevronUp size={14} className="text-gray-400" />
            ) : (
              <ChevronDown size={14} className="text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t px-4 pb-4 pt-3 space-y-3">
          {/* Response */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Response</div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg p-3">
              {result.response || "No response"}
            </p>
          </div>

          {/* Rankings */}
          {result.rankings && result.rankings.length > 1 && (
            <div>
              <div className="text-xs text-gray-500 mb-2">
                Provider Rankings
              </div>
              <div className="space-y-1">
                {result.rankings.map((r) => (
                  <div
                    key={r.provider}
                    className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 text-xs">
                        #{r.rank}
                      </span>
                      <span className="capitalize font-medium">
                        {r.provider}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-gray-600">
                      <span>{Math.round(r.score * 100)}%</span>
                      <span>{r.latency_ms}ms</span>
                      {r.passed ? (
                        <CheckCircle size={12} className="text-green-500" />
                      ) : (
                        <XCircle size={12} className="text-red-500" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Divergence */}
          {result.divergence_detected && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-orange-700 text-sm">
                <AlertTriangle size={14} />
                <span className="font-medium">Divergence detected</span>
                <span className="text-orange-500">
                  score: {result.divergence_score?.toFixed(2)}
                </span>
              </div>
              <p className="text-xs text-orange-600 mt-1">
                Providers gave significantly different responses to this input.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function BenchmarkRunPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  useRealtimeBenchmarkRun(id)

  const { data: run, isLoading } = useQuery({
    queryKey: ["run", id],
    queryFn: () => apiFetch<BenchmarkRun>(`/benchmarks/runs/${id}`),
  })

  const { data: providerSummary } = useQuery({
    queryKey: ["provider-summary", id],
    queryFn: () =>
      apiFetch<Record<string, ProviderSummaryStats>>(
        `/benchmarks/runs/${id}/provider-summary`
      ),
    enabled: run?.status === "completed",
  })

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!run) return <div className="p-8 text-gray-500">Run not found</div>

  const passed = parseInt(run.passed_cases)
  const total = parseInt(run.total_cases)
  const passRate = total > 0 ? Math.round((passed / total) * 100) : 0

  // Group results by evaluation_group_id
  const grouped = (run.results || []).reduce((acc, result) => {
    const key = result.evaluation_group_id || result.input
    if (!acc[key]) acc[key] = []
    acc[key].push(result)
    return acc
  }, {} as Record<string, BenchmarkResult[]>)

  return (
    <div className="p-8">
      <button
        className="text-sm text-gray-500 hover:text-black mb-6"
        onClick={() => router.back()}
      >
        ← Back
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold">Benchmark Run</h1>
        <span
          className={`text-xs px-2 py-1 rounded-full font-medium ${
            statusColors[run.status] || "bg-gray-100 text-gray-800"
          }`}
        >
          {run.status}
        </span>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white border rounded-xl p-4 text-center">
          <div className="text-2xl font-bold">{passRate}%</div>
          <div className="text-xs text-gray-500 mt-1">Pass Rate</div>
          <div className="text-xs text-gray-400">{passed}/{total} cases</div>
        </div>
        <div className="bg-white border rounded-xl p-4 text-center">
          <div className="text-2xl font-bold">
            {run.avg_score !== null
              ? `${Math.round(run.avg_score * 100)}%`
              : "—"}
          </div>
          <div className="text-xs text-gray-500 mt-1">Avg Score</div>
        </div>
        <div className="bg-white border rounded-xl p-4 text-center">
          <div className="text-2xl font-bold">
            {run.avg_latency_ms !== null
              ? `${Math.round(run.avg_latency_ms)}ms`
              : "—"}
          </div>
          <div className="text-xs text-gray-500 mt-1">Avg Latency</div>
        </div>
        <div className="bg-white border rounded-xl p-4 text-center">
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-xs text-gray-500 mt-1">Total Cases</div>
        </div>
      </div>

      {/* Provider Summary */}
      {providerSummary && Object.keys(providerSummary).length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">Provider Comparison</h2>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(providerSummary).map(([provider, stats]) => (
              <div key={provider} className="bg-white border rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span className="font-medium capitalize">{provider}</span>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Pass Rate</span>
                    <span className="font-medium">
                      {Math.round(stats.pass_rate * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Avg Score</span>
                    <span className="font-medium">
                      {Math.round(stats.avg_score * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Avg Latency</span>
                    <span className="font-medium">
                      {Math.round(stats.avg_latency_ms)}ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Cases</span>
                    <span className="font-medium">
                      {stats.passed_cases}/{stats.total_cases}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      <h2 className="text-lg font-semibold mb-3">
        Results
        <span className="text-sm font-normal text-gray-500 ml-2">
          Click to expand
        </span>
      </h2>
      <div className="space-y-3">
        {Object.entries(grouped).map(([groupId, results]) => (
          <div key={groupId}>
            {results.map((result, i) => (
              <div key={i} className={i > 0 ? "mt-2" : ""}>
                <ResultCard result={result} />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
