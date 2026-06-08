"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Webhook, WebhookCreateResponse, WebhookDelivery } from "@/types"
import { Trash2, ChevronDown, ChevronUp, Copy, Plus, X } from "lucide-react"

const EVENT_TYPES = [
  "evaluation.completed",
  "benchmark.completed",
  "review.required",
]

function SecretDialog({
  secret,
  onClose,
}: {
  secret: string
  onClose: () => void
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(secret)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-semibold">Webhook Secret</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
          Save your webhook secret — it will not be shown again.
        </p>
        <div className="font-mono text-sm bg-gray-50 rounded p-3 break-all mb-4 border">
          {secret}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Copy size={14} />
            {copied ? "Copied!" : "Copy"}
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 text-sm bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
          >
            I&apos;ve saved it
          </button>
        </div>
      </div>
    </div>
  )
}

function DeleteConfirmDialog({
  webhookUrl,
  onConfirm,
  onCancel,
  isPending,
}: {
  webhookUrl: string
  onConfirm: () => void
  onCancel: () => void
  isPending: boolean
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
        <h2 className="text-lg font-semibold mb-2">Delete Webhook</h2>
        <p className="text-sm text-gray-600 mb-1">
          Are you sure you want to delete this webhook?
        </p>
        <p className="text-sm font-mono bg-gray-50 rounded px-2 py-1 text-gray-700 mb-4 break-all">
          {webhookUrl}
        </p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {isPending ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  )
}

function DeliveryHistory({ webhookId }: { webhookId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["webhook-deliveries", webhookId],
    queryFn: () =>
      apiFetch<{ items: WebhookDelivery[]; total: number }>(
        `/webhooks/${webhookId}/deliveries`
      ),
  })

  if (isLoading) {
    return <p className="text-xs text-gray-400 py-2">Loading deliveries...</p>
  }

  if (!data?.items?.length) {
    return <p className="text-xs text-gray-400 py-2">No deliveries yet.</p>
  }

  return (
    <div className="space-y-2 mt-2">
      {data.items.map((delivery) => (
        <div
          key={delivery.id}
          className="flex items-start gap-3 text-xs bg-gray-50 rounded-lg px-3 py-2"
        >
          <span
            className={`px-2 py-0.5 rounded-full font-medium shrink-0 ${
              delivery.status === "success"
                ? "bg-green-100 text-green-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {delivery.status}
          </span>
          <span className="text-gray-600 shrink-0">{delivery.event_type}</span>
          {delivery.response_code != null && (
            <span className="text-gray-400 shrink-0">
              HTTP {delivery.response_code}
            </span>
          )}
          {delivery.error_message && (
            <span className="text-red-500 truncate">{delivery.error_message}</span>
          )}
          <span className="text-gray-400 ml-auto shrink-0">
            {new Date(delivery.attempted_at).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}

function WebhookCard({
  webhook,
  onDelete,
  isDeleting,
}: {
  webhook: Webhook
  onDelete: (id: string) => void
  isDeleting: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  return (
    <>
      {showDeleteConfirm && (
        <DeleteConfirmDialog
          webhookUrl={webhook.url}
          onConfirm={() => {
            onDelete(webhook.id)
            setShowDeleteConfirm(false)
          }}
          onCancel={() => setShowDeleteConfirm(false)}
          isPending={isDeleting}
        />
      )}
      <div className="bg-white border rounded-xl p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm font-medium truncate">
                {webhook.url}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${
                  webhook.active
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                {webhook.active ? "active" : "inactive"}
              </span>
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
              {webhook.event_types.map((evt) => (
                <span
                  key={evt}
                  className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full"
                >
                  {evt}
                </span>
              ))}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              Created {new Date(webhook.created_at).toLocaleDateString()}
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 px-2 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            >
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              Deliveries
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              aria-label="Delete webhook"
            >
              <Trash2 size={15} />
            </button>
          </div>
        </div>

        {expanded && (
          <div className="mt-3 border-t pt-3">
            <DeliveryHistory webhookId={webhook.id} />
          </div>
        )}
      </div>
    </>
  )
}

export default function WebhooksPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [url, setUrl] = useState("")
  const [selectedEvents, setSelectedEvents] = useState<string[]>([])
  const [createdSecret, setCreatedSecret] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["webhooks"],
    queryFn: () =>
      apiFetch<{ items: Webhook[]; total: number; limit: number; offset: number }>(
        "/webhooks/"
      ),
  })

  const createWebhook = useMutation({
    mutationFn: (data: { url: string; event_types: string[] }) =>
      apiFetch<WebhookCreateResponse>("/webhooks/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (result) => {
      setCreatedSecret(result.secret)
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
      setUrl("")
      setSelectedEvents([])
      setShowForm(false)
    },
  })

  const deleteWebhook = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/webhooks/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
      setDeletingId(null)
    },
  })

  const toggleEvent = (evt: string) => {
    setSelectedEvents((prev) =>
      prev.includes(evt) ? prev.filter((e) => e !== evt) : [...prev, evt]
    )
  }

  const handleDelete = (id: string) => {
    setDeletingId(id)
    deleteWebhook.mutate(id)
  }

  return (
    <>
      {createdSecret && (
        <SecretDialog
          secret={createdSecret}
          onClose={() => setCreatedSecret(null)}
        />
      )}

      <div className="max-w-4xl mx-auto p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Webhooks</h1>
            <p className="text-sm text-gray-500 mt-1">
              Receive HTTP callbacks when events happen in Aegis.
            </p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 text-sm transition-colors"
          >
            {showForm ? (
              <>
                <X size={14} /> Cancel
              </>
            ) : (
              <>
                <Plus size={14} /> Add Webhook
              </>
            )}
          </button>
        </div>

        {/* Create form */}
        {showForm && (
          <div className="bg-white border rounded-xl p-5 mb-6">
            <h2 className="text-base font-semibold mb-4">New Webhook</h2>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                URL <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                placeholder="https://your-server.com/webhook"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Events
              </label>
              <div className="space-y-2">
                {EVENT_TYPES.map((evt) => (
                  <label
                    key={evt}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedEvents.includes(evt)}
                      onChange={() => toggleEvent(evt)}
                      className="rounded"
                    />
                    <span className="text-sm font-mono text-gray-700">{evt}</span>
                  </label>
                ))}
              </div>
            </div>
            <button
              disabled={
                !url ||
                selectedEvents.length === 0 ||
                createWebhook.isPending
              }
              onClick={() =>
                createWebhook.mutate({ url, event_types: selectedEvents })
              }
              className="bg-black text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {createWebhook.isPending ? "Creating..." : "Create Webhook"}
            </button>
            {createWebhook.isError && (
              <p className="text-red-500 text-sm mt-2">
                {(createWebhook.error as Error).message}
              </p>
            )}
          </div>
        )}

        {/* Webhooks list */}
        {isLoading && <p className="text-gray-500 text-sm">Loading...</p>}
        {!isLoading && data?.items?.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">No webhooks yet.</p>
            <p className="text-xs mt-1">
              Add a webhook to receive event notifications.
            </p>
          </div>
        )}
        <div className="space-y-4">
          {data?.items?.map((webhook) => (
            <WebhookCard
              key={webhook.id}
              webhook={webhook}
              onDelete={handleDelete}
              isDeleting={deletingId === webhook.id && deleteWebhook.isPending}
            />
          ))}
        </div>
      </div>
    </>
  )
}
