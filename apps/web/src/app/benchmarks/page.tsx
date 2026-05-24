"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { BenchmarkSuite, Dataset, Prompt, PromptVersion } from "@/types"
import { FlaskConical, Plus, ChevronRight } from "lucide-react"

export default function BenchmarksPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    name: "",
    description: "",
    prompt_id: "",
    prompt_version_id: "",
    dataset_id: "",
    providers: ["gemini"],
    pass_threshold: 0.5,
    semantic_similarity_threshold: 0.5,
    keyword_coverage_threshold: 0.5,
    json_validity_required: false,
  })

  const { data: suites, isLoading } = useQuery({
    queryKey: ["benchmark-suites"],
    queryFn: () => apiFetch<BenchmarkSuite[]>("/benchmarks/suites"),
  })

  const { data: prompts } = useQuery({
    queryKey: ["prompts"],
    queryFn: () => apiFetch<Prompt[]>("/prompts/"),
  })

  const { data: versions } = useQuery({
    queryKey: ["versions", form.prompt_id],
    queryFn: () =>
      apiFetch<PromptVersion[]>(`/prompts/${form.prompt_id}/versions`),
    enabled: !!form.prompt_id,
  })

  const { data: datasets } = useQuery({
    queryKey: ["datasets"],
    queryFn: () => apiFetch<Dataset[]>("/benchmarks/datasets"),
  })

  const createSuite = useMutation({
    mutationFn: () =>
      apiFetch<BenchmarkSuite>("/benchmarks/suites", {
        method: "POST",
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["benchmark-suites"] })
      setShowCreate(false)
      setForm({
        name: "",
        description: "",
        prompt_id: "",
        prompt_version_id: "",
        dataset_id: "",
        providers: ["gemini"],
        pass_threshold: 0.5,
        semantic_similarity_threshold: 0.5,
        keyword_coverage_threshold: 0.5,
        json_validity_required: false,
      })
    },
  })

  const toggleProvider = (p: string) => {
    setForm((prev) => ({
      ...prev,
      providers: prev.providers.includes(p)
        ? prev.providers.filter((x) => x !== p)
        : [...prev.providers, p],
    }))
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FlaskConical size={20} className="text-purple-500" />
            <h1 className="text-2xl font-bold">Benchmarks</h1>
          </div>
          <p className="text-gray-500">
            Define and run evaluation suites across providers.
          </p>
        </div>
        <button
          className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm"
          onClick={() => setShowCreate(!showCreate)}
        >
          <Plus size={16} />
          New Suite
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Create Benchmark Suite</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Suite name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Description
              </label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Optional description"
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Prompt</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={form.prompt_id}
                onChange={(e) =>
                  setForm({
                    ...form,
                    prompt_id: e.target.value,
                    prompt_version_id: "",
                  })
                }
              >
                <option value="">Select prompt...</option>
                {prompts?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Prompt Version
              </label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={form.prompt_version_id}
                onChange={(e) =>
                  setForm({ ...form, prompt_version_id: e.target.value })
                }
                disabled={!form.prompt_id}
              >
                <option value="">Select version...</option>
                {versions?.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Dataset</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={form.dataset_id}
                onChange={(e) =>
                  setForm({ ...form, dataset_id: e.target.value })
                }
              >
                <option value="">Select dataset...</option>
                {datasets?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Pass Threshold
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={form.pass_threshold}
                onChange={(e) =>
                  setForm({
                    ...form,
                    pass_threshold: parseFloat(e.target.value),
                  })
                }
              />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-2">
                Providers
              </label>
              <div className="flex gap-3">
                {["gemini", "ollama"].map((p) => (
                  <label
                    key={p}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={form.providers.includes(p)}
                      onChange={() => toggleProvider(p)}
                      className="w-4 h-4"
                    />
                    <span className="text-sm capitalize">{p}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              className="bg-black text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800 disabled:opacity-50"
              disabled={
                !form.name ||
                !form.prompt_id ||
                !form.prompt_version_id ||
                !form.dataset_id ||
                form.providers.length === 0 ||
                createSuite.isPending
              }
              onClick={() => createSuite.mutate()}
            >
              {createSuite.isPending ? "Creating..." : "Create Suite"}
            </button>
            <button
              className="text-gray-500 px-4 py-2 rounded-lg text-sm hover:text-gray-700"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Suites List */}
      <div className="space-y-3">
        {isLoading && (
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded-xl" />
            ))}
          </div>
        )}
        {suites?.map((suite) => (
          <div
            key={suite.id}
            className="bg-white border rounded-xl p-5 hover:border-gray-400 cursor-pointer transition-colors"
            onClick={() => router.push(`/benchmarks/${suite.id}`)}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold">{suite.name}</div>
                {suite.description && (
                  <div className="text-sm text-gray-500 mt-0.5">
                    {suite.description}
                  </div>
                )}
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
                    threshold: {suite.pass_threshold}
                  </span>
                </div>
              </div>
              <ChevronRight size={16} className="text-gray-400" />
            </div>
          </div>
        ))}
        {!isLoading && suites?.length === 0 && (
          <div className="bg-white border rounded-xl p-12 text-center">
            <FlaskConical
              className="mx-auto text-gray-300 mb-3"
              size={40}
            />
            <p className="text-gray-500">No benchmark suites yet.</p>
            <p className="text-gray-400 text-sm mt-1">
              Click &quot;New Suite&quot; to create one.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
