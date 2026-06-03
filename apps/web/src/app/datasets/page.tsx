"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { Dataset } from "@/types"
import { Database, Plus, ChevronRight, Trash2 } from "lucide-react"

export default function DatasetsPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  const { data: datasets, isLoading } = useQuery({
    queryKey: ["datasets"],
    queryFn: () => apiFetch<Dataset[]>("/benchmarks/datasets"),
  })

  const createDataset = useMutation({
    mutationFn: () =>
      apiFetch<Dataset>("/benchmarks/datasets", {
        method: "POST",
        body: JSON.stringify({ name, description, items: [] }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] })
      setShowCreate(false)
      setName("")
      setDescription("")
    },
  })

  const deleteDataset = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/benchmarks/datasets/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] })
      setConfirmDelete(null)
    },
  })

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Database size={20} className="text-blue-500" />
            <h1 className="text-2xl font-bold">Datasets</h1>
          </div>
          <p className="text-gray-500">
            Manage test datasets for benchmark evaluation suites.
          </p>
        </div>
        <button
          className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm"
          onClick={() => setShowCreate(!showCreate)}
        >
          <Plus size={16} />
          New Dataset
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Create Dataset</h2>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                placeholder="Dataset name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Description</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                placeholder="Optional description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              className="bg-black text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800 disabled:opacity-50"
              disabled={!name || createDataset.isPending}
              onClick={() => createDataset.mutate()}
            >
              {createDataset.isPending ? "Creating..." : "Create Dataset"}
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

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Delete Dataset?</h3>
            <p className="text-sm text-gray-500 mb-6">
              This will permanently delete the dataset and all its items. This
              cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
                disabled={deleteDataset.isPending}
                onClick={() => deleteDataset.mutate(confirmDelete)}
              >
                {deleteDataset.isPending ? "Deleting..." : "Delete"}
              </button>
              <button
                className="flex-1 text-gray-500 border px-4 py-2 rounded-lg text-sm hover:text-gray-700"
                onClick={() => setConfirmDelete(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Datasets List */}
      <div className="space-y-3">
        {isLoading && (
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded-xl" />
            ))}
          </div>
        )}

        {datasets?.map((dataset) => (
          <div
            key={dataset.id}
            className="bg-white border rounded-xl p-5 hover:border-gray-400 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div
                className="flex-1 cursor-pointer"
                onClick={() => router.push(`/datasets/${dataset.id}`)}
              >
                <div className="font-semibold">{dataset.name}</div>
                {dataset.description && (
                  <div className="text-sm text-gray-500 mt-0.5">
                    {dataset.description}
                  </div>
                )}
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                    {dataset.items?.length ?? 0} items
                  </span>
                  <span className="text-xs text-gray-400">
                    {new Date(dataset.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  onClick={(e) => {
                    e.stopPropagation()
                    setConfirmDelete(dataset.id)
                  }}
                >
                  <Trash2 size={16} />
                </button>
                <ChevronRight
                  size={16}
                  className="text-gray-400 cursor-pointer"
                  onClick={() => router.push(`/datasets/${dataset.id}`)}
                />
              </div>
            </div>
          </div>
        ))}

        {!isLoading && datasets?.length === 0 && (
          <div className="bg-white border rounded-xl p-12 text-center">
            <Database className="mx-auto text-gray-300 mb-3" size={40} />
            <p className="text-gray-500">No datasets yet.</p>
            <p className="text-gray-400 text-sm mt-1">
              Click &quot;New Dataset&quot; to create one.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}