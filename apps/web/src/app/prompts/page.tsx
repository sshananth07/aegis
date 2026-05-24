"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { Prompt } from "@/types"

export default function PromptsPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: () => apiFetch<Prompt[]>("/prompts/"),
  })

  const createPrompt = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      apiFetch<Prompt>("/prompts/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prompts"] })
      setName("")
      setDescription("")
    },
  })

  return (
    <div className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Prompts</h1>

      {/* Create Prompt Form */}
      <div className="border rounded-lg p-6 mb-8 bg-white">
        <h2 className="text-lg font-semibold mb-4">Create Prompt</h2>
        <input
          className="w-full border rounded px-3 py-2 mb-3"
          placeholder="Prompt name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="w-full border rounded px-3 py-2 mb-3"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button
          className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800 disabled:opacity-50"
          disabled={!name || createPrompt.isPending}
          onClick={() => createPrompt.mutate({ name, description })}
        >
          {createPrompt.isPending ? "Creating..." : "Create Prompt"}
        </button>
      </div>

      {/* Prompts List */}
      <div className="space-y-3">
        {isLoading && <p className="text-gray-500">Loading...</p>}
        {prompts?.map((prompt) => (
          <div
            key={prompt.id}
            className="border rounded-lg p-4 bg-white hover:border-black cursor-pointer transition-colors"
            onClick={() => router.push(`/prompts/${prompt.id}`)}
          >
            <div className="font-medium">{prompt.name}</div>
            {prompt.description && (
              <div className="text-sm text-gray-500 mt-1">{prompt.description}</div>
            )}
            <div className="text-xs text-gray-400 mt-2">
              {new Date(prompt.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}