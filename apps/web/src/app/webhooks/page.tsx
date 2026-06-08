"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Webhook, WebhookCreateResponse, WebhookDelivery } from "@/types"

const WEBHOOK_EVENTS = [
  "evaluation.completed",
  "benchmark.completed",
  "review.required",
]

export default function WebhooksPage() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [url, setUrl] = useState("")
  const [selectedEvents, setSelectedEvents] = useState<string[]>([])
  const [createdSecret, setCreatedSecret] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [expandedDeliveries, setExpandedDeliveries] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["webhooks"],
    queryFn: () =>
      apiFetch<{ items: Webhook[]; total: number; limit: number; offset: number }>("/webhooks/"),
  })

  const createWebhook = useMutation({
    mutationFn: (payload: { url: string; event_types: string[] }) =>
      apiFetch<WebhookCreateResponse>("/webhooks/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (result) => {
      setCreatedSecret(result.secret)
      setShowCreate(false)
      setUrl("")
      setSelectedEvents([])
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
    },
  })

  const deleteWebhook = useMutation({
    mutationFn: (id: string) => apiFetch(`/webhooks/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      setConfirmDelete(null)
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
    },
  })

  const toggleEvent = (event: string) => {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Webhooks</h1>
        <button
          className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800 text-sm"
          onClick={() => setShowCreate(!showCreate)}
        >
          {showCreate ? "Cancel" : "Add Webhook"}
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">New Webhook</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint URL</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="https://your-server.com/webhook"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Events</label>
              <div className="space-y-2">
                {WEBHOOK_EVENTS.map((event) => (
                  <label key={event} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedEvents.includes(event)}
                      onChange={() => toggleEvent(event)}
                    />
                    <span className="font-mono">{event}</span>
                  </label>
                ))}
              </div>
            </div>
            <button
              className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800 disabled:opacity-50 text-sm"
              disabled={!url || selectedEvents.length === 0 || createWebhook.isPending}
              onClick={() => createWebhook.mutate({ url, event_types: selectedEvents })}
            >
              {createWebhook.isPending ? "Creating..." : "Create Webhook"}
            </button>
          </div>
        </div>
      )}

      {/* Webhook List */}
      <div className="space-y-3">
        {isLoading && <p className="text-gray-500 text-sm">Loading...</p>}
        {data?.items.length === 0 && (
          <p className="text-gray-400 text-sm">No webhooks yet. Create one to get started.</p>
        )}
        {data?.items.map((wh) => (
          <WebhookCard
            key={wh.id}
            webhook={wh}
            onDelete={() => setConfirmDelete(wh.id)}
            expanded={expandedDeliveries === wh.id}
            onToggleDeliveries={() =>
              setExpandedDeliveries(expandedDeliveries === wh.id ? null : wh.id)
            }
          />
        ))}
      </div>

      {/* Secret one-time dialog */}
      {createdSecret && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-semibold mb-2">Save your webhook secret</h2>
            <p className="text-sm text-amber-600 mb-4">
              This secret will not be shown again. Use it to verify webhook signatures.
            </p>
            <div className="font-mono text-xs bg-gray-50 rounded p-3 break-all mb-4 select-all border">
              {createdSecret}
            </div>
            <div className="flex gap-2">
              <button
                className="flex-1 border rounded px-3 py-2 text-sm hover:bg-gray-50"
                onClick={() => navigator.clipboard.writeText(createdSecret)}
              >
                Copy
              </button>
              <button
                className="flex-1 bg-black text-white rounded px-3 py-2 text-sm hover:bg-gray-800"
                onClick={() => setCreatedSecret(null)}
              >
                {"I've saved it"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h2 className="text-lg font-semibold mb-2">Delete webhook?</h2>
            <p className="text-sm text-gray-600 mb-4">
              No further events will be delivered to this endpoint.
            </p>
            <div className="flex gap-2">
              <button
                className="flex-1 border rounded px-3 py-2 text-sm"
                onClick={() => setConfirmDelete(null)}
              >
                Cancel
              </button>
              <button
                className="flex-1 bg-red-600 text-white rounded px-3 py-2 text-sm hover:bg-red-700"
                onClick={() => deleteWebhook.mutate(confirmDelete)}
                disabled={deleteWebhook.isPending}
              >
                {deleteWebhook.isPending ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function WebhookCard({
  webhook,
  onDelete,
  expanded,
  onToggleDeliveries,
}: {
  webhook: Webhook
  onDelete: () => void
  expanded: boolean
  onToggleDeliveries: () => void
}) {
  const { data: deliveries } = useQuery({
    queryKey: ["webhook-deliveries", webhook.id],
    queryFn: () =>
      apiFetch<{ items: WebhookDelivery[]; total: number }>(`/webhooks/${webhook.id}/deliveries`),
    enabled: expanded,
  })

  return (
    <div className="bg-white border rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-sm font-mono text-gray-800 break-all">{webhook.url}</div>
          <div className="flex flex-wrap gap-1 mt-2">
            {webhook.event_types.map((e) => (
              <span key={e} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                {e}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-4">
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              webhook.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
            }`}
          >
            {webhook.active ? "active" : "inactive"}
          </span>
          <button
            className="text-red-500 hover:text-red-700 text-xs"
            onClick={onDelete}
          >
            Delete
          </button>
        </div>
      </div>
      <button
        className="text-xs text-gray-500 hover:text-gray-700"
        onClick={onToggleDeliveries}
      >
        {expanded ? "Hide deliveries" : "Show deliveries"}
      </button>
      {expanded && (
        <div className="mt-3 space-y-2">
          {deliveries?.items.length === 0 && (
            <p className="text-xs text-gray-400">No deliveries yet.</p>
          )}
          {deliveries?.items.map((d) => (
            <div key={d.id} className="flex items-center gap-3 text-xs">
              <span
                className={`px-2 py-0.5 rounded-full ${
                  d.status === "success"
                    ? "bg-green-100 text-green-700"
                    : "bg-red-100 text-red-700"
                }`}
              >
                {d.status}
              </span>
              <span className="text-gray-500 font-mono">{d.event_type}</span>
              {d.response_code && <span className="text-gray-400">{d.response_code}</span>}
              <span className="text-gray-400">
                {new Date(d.attempted_at).toLocaleString()}
              </span>
              {d.error_message && (
                <span className="text-red-500 truncate max-w-xs">{d.error_message}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
