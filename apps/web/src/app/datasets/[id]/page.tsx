"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import { Dataset, DatasetItem } from "@/types"
import { Database, Plus, Trash2, ChevronDown, ChevronUp, Pencil, Check, X } from "lucide-react"

interface NewItem {
  input_text: string
  expected_output: string
  check_json: boolean
  required_keywords: string
  required_json_fields: string
}

interface EditState {
  input_text: string
  expected_output: string
  check_json: boolean
  required_keywords: string
  required_json_fields: string
}

function ItemCard({
  item,
  datasetId,
  onDelete,
  isDeleting,
}: {
  item: DatasetItem
  datasetId: string
  onDelete: (id: string) => void
  isDeleting: boolean
}) {
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editState, setEditState] = useState<EditState>({
    input_text: item.input_text,
    expected_output: item.expected_output ?? "",
    check_json: item.check_json,
    required_keywords: (item.required_keywords ?? []).join(", "),
    required_json_fields: (item.required_json_fields ?? []).join(", "),
  })

  const updateItem = useMutation({
    mutationFn: () =>
      apiFetch(`/benchmarks/datasets/${datasetId}/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          input_text: editState.input_text,
          expected_output: editState.expected_output || null,
          check_json: editState.check_json,
          required_keywords: editState.required_keywords
            ? editState.required_keywords.split(",").map((k) => k.trim()).filter(Boolean)
            : [],
          required_json_fields: editState.required_json_fields
            ? editState.required_json_fields.split(",").map((f) => f.trim()).filter(Boolean)
            : [],
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dataset", datasetId] })
      setEditing(false)
    },
  })

  const handleCancelEdit = () => {
    setEditState({
      input_text: item.input_text,
      expected_output: item.expected_output ?? "",
      check_json: item.check_json,
      required_keywords: (item.required_keywords ?? []).join(", "),
      required_json_fields: (item.required_json_fields ?? []).join(", "),
    })
    setEditing(false)
  }

  return (
    <div className="border rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="p-4 hover:bg-gray-50 transition-colors"
        onClick={() => !editing && setExpanded(!expanded)}
        style={{ cursor: editing ? "default" : "pointer" }}
      >
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-700 truncate flex-1 mr-4">
            {item.input_text}
          </p>
          <div className="flex items-center gap-2 shrink-0">
            {item.check_json && (
              <span className="text-xs bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full">
                JSON
              </span>
            )}
            {item.expected_output && (
              <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full">
                Expected
              </span>
            )}
            <button
              className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                setExpanded(true)
                setEditing(true)
              }}
            >
              <Pencil size={13} />
            </button>
            <button
              className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              disabled={isDeleting}
              onClick={(e) => {
                e.stopPropagation()
                onDelete(item.id)
              }}
            >
              <Trash2 size={13} />
            </button>
            {expanded ? (
              <ChevronUp size={14} className="text-gray-400" />
            ) : (
              <ChevronDown size={14} className="text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {/* Expanded — view or edit */}
      {expanded && (
        <div className="border-t px-4 pb-4 pt-3 space-y-3 bg-gray-50">
          {editing ? (
            <>
              <div>
                <label className="text-xs text-gray-500 block mb-1">
                  Input Text <span className="text-red-400">*</span>
                </label>
                <textarea
                  className="w-full border rounded-lg px-3 py-2 text-sm h-24 resize-none bg-white focus:outline-none focus:ring-2 focus:ring-black"
                  value={editState.input_text}
                  onChange={(e) =>
                    setEditState({ ...editState, input_text: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">
                  Expected Output{" "}
                  <span className="text-gray-400">(optional)</span>
                </label>
                <textarea
                  className="w-full border rounded-lg px-3 py-2 text-sm h-20 resize-none bg-white focus:outline-none focus:ring-2 focus:ring-black"
                  value={editState.expected_output}
                  onChange={(e) =>
                    setEditState({ ...editState, expected_output: e.target.value })
                  }
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">
                    Required Keywords{" "}
                    <span className="text-gray-400">(comma separated)</span>
                  </label>
                  <input
                    className="w-full border rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-black"
                    placeholder="keyword1, keyword2"
                    value={editState.required_keywords}
                    onChange={(e) =>
                      setEditState({ ...editState, required_keywords: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">
                    Required JSON Fields{" "}
                    <span className="text-gray-400">(comma separated)</span>
                  </label>
                  <input
                    className="w-full border rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-black"
                    placeholder="field1, field2"
                    value={editState.required_json_fields}
                    onChange={(e) =>
                      setEditState({ ...editState, required_json_fields: e.target.value })
                    }
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={editState.check_json}
                  onChange={(e) =>
                    setEditState({ ...editState, check_json: e.target.checked })
                  }
                  className="w-4 h-4"
                />
                <span className="text-sm text-gray-600">Check JSON validity</span>
              </label>
              <div className="flex gap-2 pt-1">
                <button
                  className="flex items-center gap-1.5 bg-black text-white px-3 py-1.5 rounded-lg text-sm hover:bg-gray-800 disabled:opacity-50"
                  disabled={!editState.input_text || updateItem.isPending}
                  onClick={() => updateItem.mutate()}
                >
                  <Check size={13} />
                  {updateItem.isPending ? "Saving..." : "Save"}
                </button>
                <button
                  className="flex items-center gap-1.5 text-gray-500 border px-3 py-1.5 rounded-lg text-sm hover:text-gray-700"
                  onClick={handleCancelEdit}
                >
                  <X size={13} />
                  Cancel
                </button>
              </div>
              {updateItem.isError && (
                <p className="text-xs text-red-500">Failed to save. Please try again.</p>
              )}
            </>
          ) : (
            <>
              <div>
                <div className="text-xs text-gray-500 mb-1">Input</div>
                <p className="text-sm text-gray-700 bg-white border rounded-lg p-3">
                  {item.input_text}
                </p>
              </div>
              {item.expected_output && (
                <div>
                  <div className="text-xs text-gray-500 mb-1">Expected Output</div>
                  <p className="text-sm text-gray-700 bg-white border rounded-lg p-3">
                    {item.expected_output}
                  </p>
                </div>
              )}
              {(item.required_keywords?.length > 0 || item.required_json_fields?.length > 0) && (
                <div className="grid grid-cols-2 gap-4">
                  {item.required_keywords?.length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Required Keywords</div>
                      <div className="flex flex-wrap gap-1">
                        {item.required_keywords.map((k) => (
                          <span key={k} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                            {k}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {item.required_json_fields?.length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Required JSON Fields</div>
                      <div className="flex flex-wrap gap-1">
                        {item.required_json_fields.map((f) => (
                          <span key={f} className="text-xs bg-yellow-50 text-yellow-600 px-2 py-0.5 rounded-full">
                            {f}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              <div className="flex gap-4 text-xs text-gray-500">
                <span>Check JSON: {item.check_json ? "Yes" : "No"}</span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const queryClient = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [newItem, setNewItem] = useState<NewItem>({
    input_text: "",
    expected_output: "",
    check_json: false,
    required_keywords: "",
    required_json_fields: "",
  })

  const { data: dataset, isLoading } = useQuery({
    queryKey: ["dataset", id],
    queryFn: () => apiFetch<Dataset>(`/benchmarks/datasets/${id}`),
  })

  const addItem = useMutation({
    mutationFn: () =>
      apiFetch(`/benchmarks/datasets/${id}/items`, {
        method: "POST",
        body: JSON.stringify({
          input_text: newItem.input_text,
          expected_output: newItem.expected_output || null,
          check_json: newItem.check_json,
          required_keywords: newItem.required_keywords
            ? newItem.required_keywords.split(",").map((k) => k.trim()).filter(Boolean)
            : [],
          required_json_fields: newItem.required_json_fields
            ? newItem.required_json_fields.split(",").map((f) => f.trim()).filter(Boolean)
            : [],
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dataset", id] })
      queryClient.invalidateQueries({ queryKey: ["datasets"] })
      setShowAdd(false)
      setNewItem({
        input_text: "",
        expected_output: "",
        check_json: false,
        required_keywords: "",
        required_json_fields: "",
      })
    },
  })

  const deleteItem = useMutation({
    mutationFn: (itemId: string) =>
      apiFetch(`/benchmarks/datasets/${id}/items/${itemId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dataset", id] })
      queryClient.invalidateQueries({ queryKey: ["datasets"] })
      setConfirmDelete(null)
    },
  })

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!dataset) return <div className="p-8 text-gray-500">Dataset not found</div>

  return (
    <div className="p-8">
      <button
        className="text-sm text-gray-500 hover:text-black mb-6"
        onClick={() => router.push("/datasets")}
      >
        ← Back to Datasets
      </button>

      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Database size={20} className="text-blue-500" />
            <h1 className="text-2xl font-bold">{dataset.name}</h1>
          </div>
          {dataset.description && (
            <p className="text-gray-500">{dataset.description}</p>
          )}
          <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full mt-2 inline-block">
            {dataset.items?.length ?? 0} items
          </span>
        </div>
        <button
          className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm"
          onClick={() => setShowAdd(!showAdd)}
        >
          <Plus size={16} />
          Add Item
        </button>
      </div>

      {/* Add Item Form */}
      {showAdd && (
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Add Dataset Item</h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Input Text <span className="text-red-400">*</span>
              </label>
              <textarea
                className="w-full border rounded-lg px-3 py-2 text-sm h-24 resize-none focus:outline-none focus:ring-2 focus:ring-black"
                placeholder="The input to send to the model..."
                value={newItem.input_text}
                onChange={(e) =>
                  setNewItem({ ...newItem, input_text: e.target.value })
                }
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Expected Output <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                className="w-full border rounded-lg px-3 py-2 text-sm h-20 resize-none focus:outline-none focus:ring-2 focus:ring-black"
                placeholder="The expected model response for scoring..."
                value={newItem.expected_output}
                onChange={(e) =>
                  setNewItem({ ...newItem, expected_output: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 block mb-1">
                  Required Keywords <span className="text-gray-400">(comma separated)</span>
                </label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  placeholder="keyword1, keyword2"
                  value={newItem.required_keywords}
                  onChange={(e) =>
                    setNewItem({ ...newItem, required_keywords: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">
                  Required JSON Fields <span className="text-gray-400">(comma separated)</span>
                </label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  placeholder="field1, field2"
                  value={newItem.required_json_fields}
                  onChange={(e) =>
                    setNewItem({ ...newItem, required_json_fields: e.target.value })
                  }
                />
              </div>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={newItem.check_json}
                onChange={(e) =>
                  setNewItem({ ...newItem, check_json: e.target.checked })
                }
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-600">Check JSON validity</span>
            </label>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              className="bg-black text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800 disabled:opacity-50"
              disabled={!newItem.input_text || addItem.isPending}
              onClick={() => addItem.mutate()}
            >
              {addItem.isPending ? "Adding..." : "Add Item"}
            </button>
            <button
              className="text-gray-500 px-4 py-2 rounded-lg text-sm hover:text-gray-700"
              onClick={() => setShowAdd(false)}
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
            <h3 className="text-lg font-semibold mb-2">Remove Item?</h3>
            <p className="text-sm text-gray-500 mb-6">
              This will permanently remove this test case from the dataset.
            </p>
            <div className="flex gap-3">
              <button
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
                disabled={deleteItem.isPending}
                onClick={() => deleteItem.mutate(confirmDelete)}
              >
                {deleteItem.isPending ? "Removing..." : "Remove"}
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

      {/* Items List */}
      <div className="space-y-3">
        {dataset.items?.length === 0 && (
          <div className="bg-white border rounded-xl p-12 text-center">
            <Database className="mx-auto text-gray-300 mb-3" size={40} />
            <p className="text-gray-500">No items yet.</p>
            <p className="text-gray-400 text-sm mt-1">
              Click &quot;Add Item&quot; to add test cases.
            </p>
          </div>
        )}
        {dataset.items?.map((item) => (
          <ItemCard
            key={item.id}
            item={item}
            datasetId={id}
            onDelete={(itemId) => setConfirmDelete(itemId)}
            isDeleting={deleteItem.isPending && confirmDelete === item.id}
          />
        ))}
      </div>
    </div>
  )
}
