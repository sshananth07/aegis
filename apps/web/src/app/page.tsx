"use client"

import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import {
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar
} from "recharts"
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  ClipboardCheck,
  DollarSign,
  FlaskConical,
  type LucideIcon,
  XCircle,
  Zap,
} from "lucide-react"
import { useRealtimeDashboard } from "@/hooks/useRealtimeDashboard"

interface ProviderMetrics {
  total_evaluations: number
  success_rate: number
  avg_score: number
  avg_latency_ms: number
  p95_latency_ms: number
  avg_cost: number
}

interface PlatformOverview {
  benchmarks: {
    total_runs: number
    status_counts: Record<string, number>
    total_cases: number
    passed_cases: number
    pass_rate: number
    recent_runs: Array<{
      id: string
      status: string
      total_cases: number
      passed_cases: number
      avg_score: number
      avg_latency_ms: number
      avg_cost: number
      created_at: string
    }>
  }
  costs: {
    total_cost: number
    by_provider: Record<string, number>
  }
  failures: {
    total_failed_or_review_required: number
    reason_counts: Record<string, number>
    benchmark_reason_counts: Record<string, number>
    recent: Array<{
      id: string
      provider: string
      status: string
      score: number | null
      failure_reasons: string[]
      created_at: string
    }>
  }
  reviews: {
    total_reviews: number
    status_counts: Record<string, number>
  }
  evaluations: {
    total_evaluations: number
    status_counts: Record<string, number>
  }
}

function StatCard({
  label,
  value,
  icon: Icon,
  color = "text-gray-900"
}: {
  label: string
  value: string | number
  icon: LucideIcon
  color?: string
}) {
  return (
    <div className="bg-white border rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500">{label}</span>
        <Icon size={16} className="text-gray-400" />
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  )
}

function ProviderCard({
  provider,
  metrics
}: {
  provider: string
  metrics: ProviderMetrics
}) {
  const successPct = Math.round(metrics.success_rate * 100)
  const avgScore = Math.round(metrics.avg_score * 100)

  return (
    <div className="bg-white border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="font-semibold capitalize">{provider}</span>
        </div>
        <span className="text-xs text-gray-400">
          {metrics.total_evaluations} evals
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <div className="text-xs text-gray-500 mb-1">Success Rate</div>
          <div className="text-lg font-bold text-green-600">{successPct}%</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">Avg Score</div>
          <div className="text-lg font-bold">{avgScore}%</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">Avg Latency</div>
          <div className="text-lg font-bold">
            {Math.round(metrics.avg_latency_ms)}ms
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">p95 Latency</div>
          <div className="text-lg font-bold">
            {metrics.p95_latency_ms ? `${Math.round(metrics.p95_latency_ms)}ms` : "—"}
          </div>
        </div>
      </div>

      {/* Score bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Avg Score</span>
          <span>{avgScore}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full"
            style={{ width: `${avgScore}%` }}
          />
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  useRealtimeDashboard()
  const { data: metrics, isLoading } = useQuery({
    queryKey: ["provider-metrics"],
    queryFn: () => apiFetch<Record<string, ProviderMetrics>>("/metrics/providers"),
    refetchInterval: 30000,
  })
  const { data: overview } = useQuery({
    queryKey: ["platform-overview"],
    queryFn: () => apiFetch<PlatformOverview>("/metrics/overview"),
    refetchInterval: 30000,
  })

  const providers = metrics ? Object.entries(metrics) : []
  const costData = overview
    ? Object.entries(overview.costs.by_provider).map(([provider, cost]) => ({
        provider,
        cost,
      }))
    : []
  const failureData = overview
    ? Object.entries(overview.failures.reason_counts)
        .map(([reason, count]) => ({ reason, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 6)
    : []
  const totalEvals = providers.reduce((sum, [, m]) => sum + m.total_evaluations, 0)
  const avgSuccessRate = providers.length
    ? providers.reduce((sum, [, m]) => sum + m.success_rate, 0) / providers.length
    : 0
  const avgScore = providers.length
    ? providers.reduce((sum, [, m]) => sum + m.avg_score, 0) / providers.length
    : 0
  const avgLatency = providers.length
    ? providers.reduce((sum, [, m]) => sum + m.avg_latency_ms, 0) / providers.length
    : 0

  // Build chart data from provider metrics
  const scoreChartData = providers.map(([provider, m]) => ({
    provider,
    score: Math.round(m.avg_score * 100),
    latency: Math.round(m.avg_latency_ms),
    success: Math.round(m.success_rate * 100),
  }))

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="grid grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          AI evaluation platform overview
        </p>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Evaluations"
          value={totalEvals}
          icon={Activity}
        />
        <StatCard
          label="Avg Success Rate"
          value={`${Math.round(avgSuccessRate * 100)}%`}
          icon={CheckCircle}
          color="text-green-600"
        />
        <StatCard
          label="Avg Score"
          value={`${Math.round(avgScore * 100)}%`}
          icon={Zap}
          color="text-blue-600"
        />
        <StatCard
          label="Avg Latency"
          value={`${Math.round(avgLatency)}ms`}
          icon={Clock}
        />
      </div>

      {overview && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Benchmark Pass Rate"
            value={`${Math.round(overview.benchmarks.pass_rate * 100)}%`}
            icon={FlaskConical}
            color="text-emerald-600"
          />
          <StatCard
            label="Total Cost"
            value={`$${overview.costs.total_cost.toFixed(4)}`}
            icon={DollarSign}
            color="text-slate-700"
          />
          <StatCard
            label="Flagged Evaluations"
            value={overview.failures.total_failed_or_review_required}
            icon={XCircle}
            color="text-red-600"
          />
          <StatCard
            label="Pending Reviews"
            value={overview.reviews.status_counts.pending || 0}
            icon={ClipboardCheck}
            color="text-orange-600"
          />
        </div>
      )}

      {/* Provider Cards */}
      {providers.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Provider Health</h2>
          <div className="grid grid-cols-3 gap-4">
            {providers.map(([provider, m]) => (
              <ProviderCard key={provider} provider={provider} metrics={m} />
            ))}
          </div>
        </div>
      )}

      {/* Charts */}
      {scoreChartData.length > 0 && (
        <div className="grid grid-cols-2 gap-6 mb-8">
          {/* Score by Provider */}
          <div className="bg-white border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Avg Score by Provider
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={scoreChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="provider"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  domain={[0, 100]}
                />
                <Tooltip
                  formatter={(value) => [`${value}%`, "Score"]}
                />
                <Bar dataKey="score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Latency by Provider */}
          <div className="bg-white border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Avg Latency by Provider (ms)
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={scoreChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="provider"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(value) => [`${value}ms`, "Latency"]}
                />
                <Bar dataKey="latency" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {overview && (
        <div className="grid grid-cols-2 gap-6 mb-8">
          <div className="bg-white border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Cost by Provider
            </h3>
            {costData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={costData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="provider" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value) => [`$${Number(value).toFixed(6)}`, "Cost"]} />
                  <Bar dataKey="cost" fill="#0f766e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-400 py-16 text-center">
                No cost data yet.
              </p>
            )}
          </div>

          <div className="bg-white border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Failure Reasons
            </h3>
            {failureData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={failureData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis
                    dataKey="reason"
                    type="category"
                    width={140}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip />
                  <Bar dataKey="count" fill="#dc2626" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-400 py-16 text-center">
                No failure reasons recorded.
              </p>
            )}
          </div>
        </div>
      )}

      {overview && (
        <div className="grid grid-cols-2 gap-6 mb-8">
          <div className="bg-white border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-700">
                Recent Benchmark Runs
              </h3>
              <span className="text-xs text-gray-400">
                {overview.benchmarks.total_runs} total
              </span>
            </div>
            <div className="space-y-2">
              {overview.benchmarks.recent_runs.length > 0 ? (
                overview.benchmarks.recent_runs.map((run) => {
                  const passRate = run.total_cases
                    ? Math.round((run.passed_cases / run.total_cases) * 100)
                    : 0
                  return (
                    <div
                      key={run.id}
                      className="flex items-center justify-between border-b last:border-0 py-2 text-sm"
                    >
                      <div>
                        <div className="font-mono text-xs text-gray-500">
                          {run.id.slice(0, 8)}
                        </div>
                        <div className="text-xs text-gray-400">
                          {new Date(run.created_at).toLocaleString()}
                        </div>
                      </div>
                      <span className="capitalize text-gray-600">
                        {run.status}
                      </span>
                      <span className="font-medium">{passRate}%</span>
                    </div>
                  )
                })
              ) : (
                <p className="text-sm text-gray-400 py-8 text-center">
                  No benchmark runs yet.
                </p>
              )}
            </div>
          </div>

          <div className="bg-white border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-700">
                Recent Failures
              </h3>
              <span className="text-xs text-gray-400">
                {overview.failures.total_failed_or_review_required} flagged
              </span>
            </div>
            <div className="space-y-2">
              {overview.failures.recent.length > 0 ? (
                overview.failures.recent.map((failure) => (
                  <div key={failure.id} className="border-b last:border-0 py-2">
                    <div className="grid grid-cols-[minmax(0,1fr)_96px_128px] items-center gap-4 text-sm">
                      <span className="font-mono text-xs text-gray-500 truncate">
                        {failure.id.slice(0, 8)}
                      </span>
                      <span className="capitalize text-gray-600 text-left">
                        {failure.provider}
                      </span>
                      <span className="text-red-600 text-right">
                        {failure.status}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1 pr-32">
                      {failure.failure_reasons.length > 0 ? (
                        failure.failure_reasons.map((reason) => (
                          <span
                            key={reason}
                            className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full"
                          >
                            {reason}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-gray-400">
                          No detailed reason
                        </span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400 py-8 text-center">
                  No failed or review-required evaluations.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {providers.length === 0 && (
        <div className="bg-white border rounded-xl p-12 text-center">
          <AlertTriangle className="mx-auto text-gray-300 mb-3" size={40} />
          <p className="text-gray-500">No evaluation data yet.</p>
          <p className="text-gray-400 text-sm mt-1">
            Run some evaluations to see metrics here.
          </p>
        </div>
      )}
    </div>
  )
}
