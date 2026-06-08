"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { APIKey, APIKeyCreateResponse } from "@/types"

const SCOPES = [
  "evaluations:write",
  "benchmarks:write",
  "traces:read",
  "metrics:read",
  "webhooks:write",
]

export default function APIKeysPage() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState("")
  const [selectedScopes, setSelectedScopes] = useState<string[]>([])
  const [expiresInDays, setExpiresInDays] = useState("")
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () =>
      apiFetch<{ items: APIKey[]; total: number; limit: number; offset: number }>("/api-keys/"),
  })

  const createKey = useMutation({
    mutationFn: (payload: { name: string; scopes: string[]; expires_in_days?: number }) =>
      apiFetch<APIKeyCreateResponse>("/api-keys/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (newKey) => {
      setCreatedKey(newKey.key)
      setShowCreate(false)
      setName("")
      setSelectedScopes([])
      setExpiresInDays("")
      queryClient.invalidateQueries({ queryKey: ["api-keys"] })
    },
  })

  const revokeKey = useMutation({
    mutationFn: (keyId: string) =>
      apiFetch(`/api-keys/${keyId}`, { method: "DELETE" }),
    onSuccess: () => {
      setConfirmRevoke(null)
      queryClient.invalidateQueries({ queryKey: ["api-keys"] })
    },
  })

  const toggleScope = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    )
  }

  const handleCreate = () => {
    if (!name || selectedScopes.length === 0) return
    createKey.mutate({
      name,
      scopes: selectedScopes,
      expires_in_days: expiresInDays ? parseInt(expiresInDays) : undefined,
    })
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">API Keys</h1>
        <button
          className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800 text-sm"
          onClick={() => setShowCreate(!showCreate)}
        >
          {showCreate ? "Cancel" : "Create API Key"}
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">New API Key</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="e.g. CI pipeline key"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Scopes</label>
              <div className="space-y-2">
                {SCOPES.map((scope) => (
                  <label key={scope} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedScopes.includes(scope)}
                      onChange={() => toggleScope(scope)}
                    />
                    <span className="font-mono">{scope}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Expires in (days, optional)
              </label>
              <input
                type="number"
                className="w-32 border rounded px-3 py-2 text-sm"
                placeholder="90"
                value={expiresInDays}
                onChange={(e) => setExpiresInDays(e.target.value)}
              />
            </div>
            <button
              className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800 disabled:opacity-50 text-sm"
              disabled={!name || selectedScopes.length === 0 || createKey.isPending}
              onClick={handleCreate}
            >
              {createKey.isPending ? "Creating..." : "Create Key"}
            </button>
          </div>
        </div>
      )}

      {/* Key List */}
      <div className="space-y-3">
        {isLoading && <p className="text-gray-500 text-sm">Loading...</p>}
        {data?.items.length === 0 && (
          <p className="text-gray-400 text-sm">No API keys yet. Create one to get started.</p>
        )}
        {data?.items.map((key) => (
          <div key={key.id} className="bg-white border rounded-xl p-5">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-sm">{key.name}</div>
                <div className="font-mono text-xs text-gray-500 mt-0.5">{key.key_prefix}...</div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {key.scopes.map((s) => (
                    <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span>Last used: {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : "Never"}</span>
                {!key.revoked && (
                  <button
                    className="text-red-500 hover:text-red-700"
                    onClick={() => setConfirmRevoke(key.id)}
                  >
                    Revoke
                  </button>
                )}
                {key.revoked && <span className="text-gray-400 italic">Revoked</span>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* One-time key dialog */}
      {createdKey && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-semibold mb-2">Save your API key</h2>
            <p className="text-sm text-amber-600 mb-4">
              ⚠️ This key will not be shown again. Copy it now.
            </p>
            <div className="font-mono text-xs bg-gray-50 rounded p-3 break-all mb-4 select-all border">
              {createdKey}
            </div>
            <div className="flex gap-2">
              <button
                className="flex-1 border rounded px-3 py-2 text-sm hover:bg-gray-50"
                onClick={() => navigator.clipboard.writeText(createdKey)}
              >
                Copy
              </button>
              <button
                className="flex-1 bg-black text-white rounded px-3 py-2 text-sm hover:bg-gray-800"
                onClick={() => setCreatedKey(null)}
              >
                I&apos;ve saved it
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Revoke confirm modal */}
      {confirmRevoke && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h2 className="text-lg font-semibold mb-2">Revoke API key?</h2>
            <p className="text-sm text-gray-600 mb-4">
              This key will stop working immediately. This cannot be undone.
            </p>
            <div className="flex gap-2">
              <button
                className="flex-1 border rounded px-3 py-2 text-sm hover:bg-gray-50"
                onClick={() => setConfirmRevoke(null)}
              >
                Cancel
              </button>
              <button
                className="flex-1 bg-red-600 text-white rounded px-3 py-2 text-sm hover:bg-red-700"
                onClick={() => revokeKey.mutate(confirmRevoke)}
                disabled={revokeKey.isPending}
              >
                {revokeKey.isPending ? "Revoking..." : "Revoke"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
