"use client"

import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { BenchmarkSuite, BenchmarkRun, Job } from "@/types"
import { useJob } from "@/hooks/useJob"
import { Play, ChevronRight, CheckCircle, Clock } from "lucide-react"

const statusColors: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  running: "bg-blue-100 text-blue-800",
  partially_completed: "bg-yellow-100 text-yellow-800",
  queued: "bg-gray-100 text-gray-800",
}

export default function SuiteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const activeJob = useJob(activeJobId)

  const { data: suite } = useQuery({
    queryKey: ["suite", id],
    queryFn: () => apiFetch<BenchmarkSuite>(`/benchmarks/suites/${id}`),
  })

  const { data: runs, refetch } = useQuery({
    queryKey: ["runs", id],
    queryFn: () =>
      apiFetch<BenchmarkRun[]>(`/benchmarks/suites/${id}/runs`),
  })

  const runSuite = useMutation({
    mutationFn: () =>
      apiFetch<Job>(`/benchmarks/suites/${id}/run`, {
        method: "POST",
      }),
    onSuccess: (job) => {
      setActiveJobId(job.id)
      refetch()
    },
  })

  return (
    <div className="p-8">
      {/* Header */}
      <button
        className="text-sm text-gray-500 hover:text-black mb-6"
        onClick={() => router.push("/benchmarks")}
      >
        ← Back to Benchmarks
      </button>

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">{suite?.name}</h1>
          {suite?.description && (
            <p className="text-gray-500 mt-1">{suite.description}</p>
          )}
          {suite && (
            <div className="flex items-center gap-3 mt-2">
              {suite.providers.map((p) => (
                <span
                  key={p}
                  className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize"
                >
                  {p}
                </span>
              ))}
              <span className="text-xs text-gray-400">
                pass threshold: {suite.pass_threshold}
              </span>
            </div>
          )}
        </div>
        <button
          className="flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          disabled={runSuite.isPending || activeJob?.status === "queued" || activeJob?.status === "running"}
          onClick={() => runSuite.mutate()}
        >
          <Play size={16} />
          {activeJob?.status === "running"
            ? `Running ${activeJob.progress}/${activeJob.total}`
            : activeJob?.status === "queued"
            ? "Queued..."
            : "Run Suite"}
        </button>
      </div>

      {/* Run History */}
      <h2 className="text-lg font-semibold mb-4">Run History</h2>
      <div className="space-y-3">
        {runs?.map((run) => {
          const passed = parseInt(run.passed_cases)
          const total = parseInt(run.total_cases)
          const passRate = total > 0 ? Math.round((passed / total) * 100) : 0

          return (
            <div
              key={run.id}
              className="bg-white border rounded-xl p-5 hover:border-gray-400 cursor-pointer transition-colors"
              onClick={() => router.push(`/benchmarks/runs/${run.id}`)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${
                      statusColors[run.status] || "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {run.status}
                  </span>
                  <div className="flex items-center gap-1.5 text-sm text-gray-600">
                    <CheckCircle size={14} className="text-green-500" />
                    {passed}/{total} passed
                    <span className="text-gray-400">({passRate}%)</span>
                  </div>
                  {run.avg_score !== null && (
                    <div className="text-sm text-gray-600">
                      avg score:{" "}
                      <span className="font-medium">
                        {Math.round(run.avg_score * 100)}%
                      </span>
                    </div>
                  )}
                  {run.avg_latency_ms !== null && (
                    <div className="flex items-center gap-1 text-sm text-gray-600">
                      <Clock size={14} />
                      {Math.round(run.avg_latency_ms)}ms
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">
                    {new Date(run.created_at).toLocaleDateString()}
                  </span>
                  <ChevronRight size={16} className="text-gray-400" />
                </div>
              </div>
            </div>
          )
        })}
        {runs?.length === 0 && (
          <div className="bg-white border rounded-xl p-12 text-center">
            <p className="text-gray-500">No runs yet.</p>
            <p className="text-gray-400 text-sm mt-1">
              Click &quot;Run Suite&quot; to start the first evaluation.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
