"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useRouter } from "next/navigation"
import { Activity, Search, ChevronRight } from "lucide-react"
import { useRealtimeDashboard } from "@/hooks/useRealtimeDashboard"

interface Evaluation {
  id: string
  provider: string
  status: string
  score: number | null
  latency_ms: number | null
  token_usage: number | null
  token_usage_estimated: boolean | null
  cost: number | null
  created_at: string
}

interface ProviderMetric {
  total_evaluations: number
}

const statusColors: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  running: "bg-blue-100 text-blue-800",
  review_required: "bg-orange-100 text-orange-800",
  queued: "bg-gray-100 text-gray-800",
  partially_completed: "bg-yellow-100 text-yellow-800",
}

export default function TracesPage() {
  const router = useRouter()
  const [search, setSearch] = useState("")
  const [filterProvider, setFilterProvider] = useState("all")
  const [filterStatus, setFilterStatus] = useState("all")

  useRealtimeDashboard()

  const { data: metrics } = useQuery({
    queryKey: ["provider-metrics"],
    queryFn: () => apiFetch<Record<string, ProviderMetric>>("/metrics/providers"),
  })

  // Fetch evaluations via CSV export parsed as list
  // We'll use a dedicated list endpoint instead
  const { data: evaluations, isLoading } = useQuery({
    queryKey: ["evaluations-list"],
    queryFn: () => apiFetch<Evaluation[]>("/evaluations/"),
  })

  const providers = metrics ? Object.keys(metrics) : []

  const filtered = (evaluations || []).filter((e) => {
    const matchesSearch = search
      ? e.id.includes(search) || e.provider.includes(search.toLowerCase())
      : true
    const matchesProvider =
      filterProvider === "all" ? true : e.provider === filterProvider
    const matchesStatus =
      filterStatus === "all" ? true : e.status === filterStatus
    return matchesSearch && matchesProvider && matchesStatus
  })

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Activity size={20} className="text-green-500" />
          <h1 className="text-2xl font-bold">Traces</h1>
        </div>
        <p className="text-gray-500">
          Browse and inspect execution traces for all evaluations.
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            className="w-full border rounded-lg pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
            placeholder="Search by ID or provider..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={filterProvider}
          onChange={(e) => setFilterProvider(e.target.value)}
        >
          <option value="all">All Providers</option>
          {providers.map((p) => (
            <option key={p} value={p}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </option>
          ))}
        </select>

        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
        >
          <option value="all">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="review_required">Review Required</option>
          <option value="running">Running</option>
        </select>

        <span className="text-sm text-gray-400 ml-auto">
          {filtered.length} evaluations
        </span>
      </div>

      {/* Table */}
      <div className="bg-white border rounded-xl overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-6 gap-4 px-5 py-3 border-b bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
          <div className="col-span-2">Evaluation ID</div>
          <div>Provider</div>
          <div>Status</div>
          <div>Score</div>
          <div>Latency</div>
        </div>

        {/* Rows */}
        {isLoading && (
          <div className="animate-pulse">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="grid grid-cols-6 gap-4 px-5 py-4 border-b"
              >
                {[...Array(6)].map((_, j) => (
                  <div key={j} className="h-4 bg-gray-200 rounded" />
                ))}
              </div>
            ))}
          </div>
        )}

        {!isLoading && filtered.length === 0 && (
          <div className="py-12 text-center">
            <Activity className="mx-auto text-gray-300 mb-3" size={32} />
            <p className="text-gray-500 text-sm">No evaluations found.</p>
          </div>
        )}

        {filtered.map((evaluation) => (
          <div
            key={evaluation.id}
            className="grid grid-cols-6 gap-4 px-5 py-4 border-b last:border-0 hover:bg-gray-50 cursor-pointer transition-colors items-center"
            onClick={() => router.push(`/traces/${evaluation.id}`)}
          >
            {/* ID */}
            <div className="col-span-2 flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
              <span className="font-mono text-xs text-gray-600 truncate">
                {evaluation.id}
              </span>
            </div>

            {/* Provider */}
            <div>
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
                {evaluation.provider}
              </span>
            </div>

            {/* Status */}
            <div>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  statusColors[evaluation.status] ||
                  "bg-gray-100 text-gray-800"
                }`}
              >
                {evaluation.status}
              </span>
            </div>

            {/* Score */}
            <div className="text-sm font-medium">
              {evaluation.score !== null
                ? `${Math.round(evaluation.score * 100)}%`
                : "—"}
            </div>

            {/* Latency */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">
                {evaluation.latency_ms ? `${evaluation.latency_ms}ms` : "—"}
              </span>
              <ChevronRight size={14} className="text-gray-400" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
