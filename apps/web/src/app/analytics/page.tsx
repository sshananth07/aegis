"use client"

import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts"
import {
  AlertTriangle, TrendingDown,
  Activity, DollarSign, Shield
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

const COLORS = ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#8b5cf6", "#6b7280"]

const severityColors: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
}

const severityIcons: Record<string, string> = {
  critical: "🔴",
  high: "🟠",
}

interface FailureOverview {
  total_evaluations: number
  total_failures: number
  failure_rate: number
  top_failure_reason: string | null
  regression_alerts: number
}

interface FailureTimeseriesPoint {
  date: string
  total: number
  failed: number
  failure_rate: number
  pass_rate: number
}

interface FailureReason {
  failure_reason: string
  count: number
}

interface ProviderStability {
  provider: string
  total_evaluations: number
  failure_rate: number
  avg_latency_ms: number
  avg_score: number
  avg_cost: number
  cost_efficiency_score: number | null
}

interface CostOverview {
  total_cost: number
  avg_cost_per_eval: number
  most_expensive_provider: string | null
}

interface CostByProvider {
  provider: string
  total_cost: number
  avg_cost: number
  cost_efficiency_score: number | null
}

interface CostTimeseriesPoint {
  date: string
  cost: number
}

interface Regression {
  entity_type: string
  entity_id: string
  metric: string
  previous: number
  current: number
  change_percent: number
  severity: string
}

interface BenchmarkStability {
  suite_id: string
  suite_name: string
  total_runs: number
  avg_pass_rate: number
  std_deviation: number
  stability: string
  trend: string | null
  latest_pass_rate: number | null
}

interface BenchmarkHistoryPoint {
  run_id: string
  suite_id: string
  date: string
  pass_rate: number
  avg_score: number
  avg_latency_ms: number
  total_cases: number
  passed_cases: number
}

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  color = "text-gray-900",
}: {
  label: string
  value: string | number
  sub?: string
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
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

export default function AnalyticsPage() {
  const { data: failureOverview } = useQuery({
    queryKey: ["analytics-failure-overview"],
    queryFn: () => apiFetch<FailureOverview>("/analytics/failures/overview"),
    refetchInterval: 30000,
  })

  const { data: timeseries } = useQuery({
    queryKey: ["analytics-timeseries"],
    queryFn: () => apiFetch<FailureTimeseriesPoint[]>("/analytics/failures/timeseries?days=14"),
  })

  const { data: byReason } = useQuery({
    queryKey: ["analytics-by-reason"],
    queryFn: () => apiFetch<FailureReason[]>("/analytics/failures/by-reason"),
  })

  const { data: providerStability } = useQuery({
    queryKey: ["analytics-provider-stability"],
    queryFn: () => apiFetch<ProviderStability[]>("/analytics/failures/providers"),
  })

  const { data: costOverview } = useQuery({
    queryKey: ["analytics-cost-overview"],
    queryFn: () => apiFetch<CostOverview>("/analytics/costs/overview"),
  })

  const { data: costByProvider } = useQuery({
    queryKey: ["analytics-cost-providers"],
    queryFn: () => apiFetch<CostByProvider[]>("/analytics/costs/providers"),
  })

  const { data: costTimeseries } = useQuery({
    queryKey: ["analytics-cost-timeseries"],
    queryFn: () => apiFetch<CostTimeseriesPoint[]>("/analytics/costs/timeseries?days=14"),
  })

  const { data: regressions } = useQuery({
    queryKey: ["analytics-regressions"],
    queryFn: () => apiFetch<Regression[]>("/analytics/regressions"),
    refetchInterval: 60000,
  })

  const { data: benchmarkStability } = useQuery({
    queryKey: ["analytics-benchmark-stability"],
    queryFn: () => apiFetch<BenchmarkStability[]>("/analytics/benchmarks/stability"),
  })

  const { data: benchmarkHistory } = useQuery({
    queryKey: ["analytics-benchmark-history"],
    queryFn: () => apiFetch<BenchmarkHistoryPoint[]>("/analytics/benchmarks/history"),
  })

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Activity size={20} className="text-red-500" />
          <h1 className="text-2xl font-bold">Failure Analytics</h1>
        </div>
        <p className="text-gray-500">
          Reliability intelligence — failure trends, regressions, and cost analysis.
        </p>
      </div>

      {/* Regression Alerts */}
      {regressions && regressions.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <AlertTriangle size={18} className="text-orange-500" />
            Regression Alerts
            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
              {regressions.length}
            </span>
          </h2>
          <div className="space-y-2">
            {regressions.map((r, i) => (
              <div
                key={i}
                className={`border rounded-xl p-4 flex items-center justify-between ${
                  severityColors[r.severity] ?? "bg-gray-100 text-gray-800"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span>{severityIcons[r.severity] ?? "⚠️"}</span>
                  <div>
                    <span className="font-medium capitalize">{r.entity_type}</span>{" "}
                    <span className="font-mono text-sm">{r.entity_id}</span>
                    <span className="mx-2">—</span>
                    <span className="capitalize">{r.metric.replace(/_/g, " ")}</span>{" "}
                    {r.change_percent < 0 ? "dropped" : "increased"} by{" "}
                    <span className="font-bold">{Math.abs(r.change_percent)}%</span>
                  </div>
                </div>
                <div className="text-sm font-mono">
                  {r.previous.toFixed(2)} → {r.current.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Overview Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Failures"
          value={failureOverview?.total_failures ?? "—"}
          sub={`${Math.round((failureOverview?.failure_rate ?? 0) * 100)}% failure rate`}
          icon={AlertTriangle}
          color="text-red-600"
        />
        <StatCard
          label="Top Failure Reason"
          value={failureOverview?.top_failure_reason?.replace(/_/g, " ") ?? "—"}
          icon={TrendingDown}
          color="text-orange-600"
        />
        <StatCard
          label="Total Cost"
          value={`$${costOverview?.total_cost?.toFixed(6) ?? "0"}`}
          sub={`$${costOverview?.avg_cost_per_eval?.toFixed(6) ?? "0"} avg/eval`}
          icon={DollarSign}
          color="text-green-600"
        />
        <StatCard
          label="Regression Alerts"
          value={failureOverview?.regression_alerts ?? 0}
          sub="last 7 days"
          icon={Shield}
          color={
            (failureOverview?.regression_alerts ?? 0) > 0
              ? "text-red-600"
              : "text-green-600"
          }
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Failure Trend */}
        <div className="bg-white border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Failure Rate Trend (14 days)
          </h3>
          {timeseries && timeseries.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={timeseries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  tickFormatter={(d) => d.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  tickFormatter={(v) => `${Math.round(v * 100)}%`}
                />
                <Tooltip
                  formatter={(v) => [
                    `${Math.round(Number(v ?? 0) * 100)}%`,
                    "Rate",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="failure_rate"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Failure Rate"
                />
                <Line
                  type="monotone"
                  dataKey="pass_rate"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Pass Rate"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              Not enough data yet
            </div>
          )}
        </div>

        {/* Failure Reasons Pie */}
        <div className="bg-white border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Failure Reasons Breakdown
          </h3>
          {byReason && byReason.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={byReason}
                  dataKey="count"
                  nameKey="failure_reason"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                >
                  {byReason.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v, n) => [v, String(n).replace(/_/g, " ")]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No failures recorded
            </div>
          )}
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Cost Trend */}
        <div className="bg-white border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Daily Cost (14 days)
          </h3>
          {costTimeseries && costTimeseries.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={costTimeseries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  tickFormatter={(d) => d.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  tickFormatter={(v) => `$${v.toFixed(4)}`}
                />
                <Tooltip
                  formatter={(v) => [`$${Number(v ?? 0).toFixed(6)}`, "Cost"]}
                />
                <Bar dataKey="cost" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No cost data yet
            </div>
          )}
        </div>

        {/* Cost Efficiency */}
        <div className="bg-white border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Cost Efficiency Leaderboard
          </h3>
          {costByProvider && costByProvider.length > 0 ? (
            <div className="space-y-3">
              {costByProvider.map((p, i) => (
                <div
                  key={p.provider}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-gray-300">
                      #{i + 1}
                    </span>
                    <div>
                      <div className="font-medium capitalize">{p.provider}</div>
                      <div className="text-xs text-gray-500">
                        ${p.total_cost.toFixed(6)} total
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {p.cost_efficiency_score ? (
                      <>
                        <div className="font-bold text-green-600">
                          {p.cost_efficiency_score.toFixed(2)}
                        </div>
                        <div className="text-xs text-gray-500">quality/$</div>
                      </>
                    ) : (
                      <div className="text-gray-400 text-sm">Free</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No cost data yet
            </div>
          )}
        </div>
      </div>

      {/* Provider Stability Table */}
      <div className="bg-white border rounded-xl p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          Provider Stability
        </h3>
        {providerStability && providerStability.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  {["Provider", "Evals", "Failure %", "Avg Latency", "Avg Score", "Efficiency"].map((h) => (
                    <th key={h} className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {providerStability.map((p) => (
                  <tr key={p.provider} className="border-b last:border-0">
                    <td className="py-3 px-3 font-medium capitalize">{p.provider}</td>
                    <td className="py-3 px-3 text-gray-600">{p.total_evaluations}</td>
                    <td className="py-3 px-3">
                      <span className={`font-medium ${
                        p.failure_rate > 0.3 ? "text-red-600"
                        : p.failure_rate > 0.1 ? "text-orange-500"
                        : "text-green-600"
                      }`}>
                        {Math.round(p.failure_rate * 100)}%
                      </span>
                    </td>
                    <td className="py-3 px-3 text-gray-600">{p.avg_latency_ms}ms</td>
                    <td className="py-3 px-3 text-gray-600">{Math.round(p.avg_score * 100)}%</td>
                    <td className="py-3 px-3">
                      {p.cost_efficiency_score ? (
                        <span className="font-medium text-green-600">
                          {p.cost_efficiency_score}
                        </span>
                      ) : (
                        <span className="text-gray-400">Free</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400 text-sm">
            No provider data yet
          </div>
        )}
      </div>

      {/* Benchmark Stability */}
      <div className="bg-white border rounded-xl p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          Benchmark Stability
        </h3>
        {benchmarkStability && benchmarkStability.length > 0 ? (
          <div className="space-y-3">
            {benchmarkStability.map((suite) => {
              const stabilityColor = ({
                stable: "bg-green-100 text-green-700",
                variable: "bg-yellow-100 text-yellow-700",
                unstable: "bg-red-100 text-red-700",
              } satisfies Record<string, string>)[suite.stability] ?? "bg-gray-100 text-gray-700"

              const trendIcon = ({
                improving: "↑",
                degrading: "↓",
                stable: "→",
              } satisfies Record<string, string>)[suite.trend ?? ""] ?? "—"

              const trendColor = ({
                improving: "text-green-600",
                degrading: "text-red-600",
                stable: "text-gray-500",
              } satisfies Record<string, string>)[suite.trend ?? ""] ?? "text-gray-400"

              return (
                <div
                  key={suite.suite_id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-xl"
                >
                  <div>
                    <div className="font-medium">{suite.suite_name}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {suite.total_runs} runs · σ {suite.std_deviation?.toFixed(3)}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="font-bold">
                        {Math.round(suite.avg_pass_rate * 100)}%
                      </div>
                      <div className="text-xs text-gray-500">avg pass rate</div>
                    </div>
                    <span className={`text-lg font-bold ${trendColor}`}>
                      {trendIcon}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${stabilityColor}`}>
                      {suite.stability}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400 text-sm">
            Run benchmark suites to see stability analysis
          </div>
        )}
      </div>

      {/* Benchmark History Chart */}
      {benchmarkHistory && benchmarkHistory.length > 0 && (
        <div className="bg-white border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Benchmark Pass Rate History
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={benchmarkHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                tickLine={false}
                tickFormatter={(d) => d.slice(5)}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                tickLine={false}
                domain={[0, 1]}
                tickFormatter={(v) => `${Math.round(v * 100)}%`}
              />
              <Tooltip
                formatter={(v: unknown) => [
                  `${Math.round(Number(v) * 100)}%`,
                  "Pass Rate",
                ]}
              />
              <Line
                type="monotone"
                dataKey="pass_rate"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
