"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Evaluation } from "@/types"
import { Zap, Copy, Check } from "lucide-react"

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  review_required: "bg-orange-100 text-orange-800",
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500"

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

export default function PlaygroundPage() {
  const [prompt, setPrompt] = useState("")
  const [provider, setProvider] = useState("gemini")
  const [expectedOutput, setExpectedOutput] = useState("")
  const [checkJson, setCheckJson] = useState(false)
  const [copied, setCopied] = useState(false)

  const run = useMutation({
    mutationFn: () =>
      apiFetch<Evaluation>("/prompts/playground", {
        method: "POST",
        body: JSON.stringify({
          prompt,
          provider,
          expected_output: expectedOutput || null,
          check_json: checkJson,
        }),
      }),
  })

  const handleCopy = () => {
    if (run.data?.response) {
      navigator.clipboard.writeText(run.data.response)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const scoreDetails = run.data?.score_details as Record<
    string,
    number | null
  > | null

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Zap size={20} className="text-yellow-500" />
          <h1 className="text-2xl font-bold">Playground</h1>
        </div>
        <p className="text-gray-500">
          Test prompts ad-hoc against any provider. Results are automatically logged.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left — Input */}
        <div className="space-y-4">
          {/* Prompt */}
          <div className="bg-white border rounded-xl p-5">
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Prompt
            </label>
            <textarea
              className="w-full border rounded-lg px-3 py-2 h-48 resize-none text-sm focus:outline-none focus:ring-2 focus:ring-black"
              placeholder="Enter your prompt here..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>

          {/* Settings */}
          <div className="bg-white border rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-medium text-gray-700">Settings</h2>

            <div>
              <label className="text-xs text-gray-500 block mb-1">Provider</label>
              <select
                className="border rounded-lg px-3 py-2 w-full text-sm"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="gemini">Gemini</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Expected Output{" "}
                <span className="text-gray-400">(optional — enables scoring)</span>
              </label>
              <textarea
                className="w-full border rounded-lg px-3 py-2 h-20 resize-none text-sm focus:outline-none focus:ring-2 focus:ring-black"
                placeholder="Leave blank to skip scoring..."
                value={expectedOutput}
                onChange={(e) => setExpectedOutput(e.target.value)}
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={checkJson}
                onChange={(e) => setCheckJson(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-600">Check JSON validity</span>
            </label>
          </div>

          <button
            className="w-full bg-black text-white py-3 rounded-xl font-medium hover:bg-gray-800 disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
            disabled={!prompt || run.isPending}
            onClick={() => run.mutate()}
          >
            <Zap size={16} />
            {run.isPending ? "Running..." : "Run Evaluation"}
          </button>
        </div>

        {/* Right — Output */}
        <div className="space-y-4">
          {/* Response */}
          <div className="bg-white border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-medium text-gray-700">
                Response
              </label>
              <div className="flex items-center gap-2">
                {run.data && (
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${
                      statusColors[run.data.status] || ""
                    }`}
                  >
                    {run.data.status}
                  </span>
                )}
                {run.data?.response && (
                  <button
                    onClick={handleCopy}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {copied ? (
                      <Check size={14} className="text-green-500" />
                    ) : (
                      <Copy size={14} />
                    )}
                  </button>
                )}
              </div>
            </div>

            <div className="min-h-48 text-sm text-gray-700 whitespace-pre-wrap">
              {run.isPending && (
                <div className="flex items-center gap-2 text-gray-400">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <div
                    className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
              )}
              {!run.isPending && !run.data && (
                <p className="text-gray-400 italic">
                  Response will appear here...
                </p>
              )}
              {run.data?.response}
            </div>
          </div>

          {/* Metrics */}
          {run.data && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white border rounded-xl p-4 text-center">
                <div className="text-xl font-bold">
                  {run.data.score !== null
                    ? `${Math.round(run.data.score * 100)}%`
                    : "—"}
                </div>
                <div className="text-xs text-gray-500 mt-1">Score</div>
              </div>
              <div className="bg-white border rounded-xl p-4 text-center">
                <div className="text-xl font-bold">
                  {run.data.latency_ms ?? "—"}
                </div>
                <div className="text-xs text-gray-500 mt-1">Latency (ms)</div>
              </div>
              <div className="bg-white border rounded-xl p-4 text-center">
                <div className="text-xl font-bold">
                  {run.data.token_usage ?? "—"}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Tokens
                  {run.data.token_usage_estimated && (
                    <span className="text-yellow-500 ml-1">~</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Score Breakdown */}
          {scoreDetails &&
            Object.values(scoreDetails).some((v) => v !== null) && (
              <div className="bg-white border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">
                  Score Breakdown
                </h3>
                <ScoreBar
                  label="JSON Validity"
                  value={scoreDetails.json_validity ?? null}
                />
                <ScoreBar
                  label="Exact Match"
                  value={scoreDetails.exact_match ?? null}
                />
                <ScoreBar
                  label="Semantic Similarity"
                  value={scoreDetails.semantic_similarity ?? null}
                />
              </div>
            )}

          {/* Provider info */}
          {run.data && (
            <div className="bg-white border rounded-xl p-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Provider</span>
                <span className="font-medium capitalize">
                  {run.data.provider}
                </span>
              </div>
              {run.data.cost ? (
                <div className="flex justify-between text-sm mt-2">
                  <span className="text-gray-500">Cost</span>
                  <span className="font-medium">
                    ${run.data.cost.toFixed(6)}
                  </span>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
