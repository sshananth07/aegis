"use client"

import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { useRouter, useParams } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { PromptVersion, Job } from "@/types"
import { useJob } from "@/hooks/useJob"

export default function PromptDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [template, setTemplate] = useState("")
  const [expectedOutput, setExpectedOutput] = useState("")
  const [checkJson, setCheckJson] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState("gemini")
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const activeJob = useJob(activeJobId)

  const { data: versions, refetch } = useQuery({
    queryKey: ["versions", id],
    queryFn: () => apiFetch<PromptVersion[]>(`/prompts/${id}/versions`),
  })

  const createVersion = useMutation({
    mutationFn: (data: { template: string }) =>
      apiFetch<PromptVersion>(`/prompts/${id}/versions`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      refetch()
      setTemplate("")
    },
  })

  const runEvaluation = useMutation({
    mutationFn: (prompt_version_id: string) =>
      apiFetch<Job>("/evaluations/", {
        method: "POST",
        body: JSON.stringify({
          prompt_version_id,
          provider: selectedProvider,
          expected_output: expectedOutput || null,
          check_json: checkJson,
        }),
      }),
    onSuccess: (job) => {
      setActiveJobId(job.id)
    },
  })

  return (
    <div className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Prompt Versions</h1>

      {/* Create Version */}
      <div className="border rounded-lg p-6 mb-8 bg-white">
        <h2 className="text-lg font-semibold mb-4">Add Version</h2>
        <textarea
          className="w-full border rounded px-3 py-2 mb-3 h-32 resize-none"
          placeholder="Enter your prompt template..."
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
        />
        <button
          className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800 disabled:opacity-50"
          disabled={!template || createVersion.isPending}
          onClick={() => createVersion.mutate({ template })}
        >
          {createVersion.isPending ? "Saving..." : "Save Version"}
        </button>
      </div>

      {/* Evaluation Options */}
      <div className="border rounded-lg p-6 mb-8 bg-white">
        <h2 className="text-lg font-semibold mb-4">Evaluation Settings</h2>

        <div className="mb-3">
          <label className="text-sm text-gray-600 block mb-1">Provider</label>
          <select
            className="border rounded px-3 py-2 w-full"
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
          >
            <option value="gemini">Gemini</option>
            <option value="ollama">Ollama (Local)</option>
          </select>
        </div>

        <div className="mb-3">
          <label className="text-sm text-gray-600 block mb-1">
            Expected Output <span className="text-gray-400">(optional)</span>
          </label>
          <textarea
            className="w-full border rounded px-3 py-2 h-20 resize-none"
            placeholder="Leave blank if no expected output..."
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

      {/* Versions List */}
      <div className="space-y-4">
        {versions?.map((version) => (
          <div key={version.id} className="border rounded-lg p-4 bg-white">
            <div className="flex justify-between items-start mb-3">
              <span className="text-sm font-medium text-gray-500">
                v{version.version}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(version.created_at).toLocaleDateString()}
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-4 whitespace-pre-wrap">
              {version.template}
            </p>
            <button
              className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50"
              disabled={runEvaluation.isPending || (activeJob && ["queued", "running"].includes(activeJob.status))}
              onClick={() => runEvaluation.mutate(version.id)}
            >
              {activeJob?.status === "running"
                ? `Running... (${activeJob.progress}/${activeJob.total})`
                : activeJob?.status === "queued"
                ? "Queued..."
                : "▶ Run Evaluation"}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
