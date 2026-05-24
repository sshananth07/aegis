"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { ClipboardCheck, CheckCircle, XCircle, MessageSquare } from "lucide-react"
import { useRealtimeReviewQueue } from "@/hooks/useRealtimeReviewQueue"

interface Review {
  id: string
  evaluation_id: string
  reviewer_id: string
  status: string
  comment: string | null
  created_at: string
  updated_at: string
}

interface EvaluationSummary {
  id: string
  provider: string
  score: number | null
  response: string | null
  status: string
  latency_ms: number | null
}

interface TraceSummary {
  event_type: string
  latency_ms: number | null
  timestamp: string
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
}

function ReviewCard({
  review,
  onAction,
}: {
  review: Review
  onAction: (id: string, status: string, comment: string) => void
}) {
  const [comment, setComment] = useState("")
  const [expanded, setExpanded] = useState(false)

  const { data: evaluation } = useQuery({
    queryKey: ["evaluation", review.evaluation_id],
    queryFn: () =>
      apiFetch<EvaluationSummary>(`/evaluations/${review.evaluation_id}`),
  })

  const { data: traces } = useQuery({
    queryKey: ["traces", review.evaluation_id],
    queryFn: () =>
      apiFetch<TraceSummary[]>(`/evaluations/${review.evaluation_id}/traces`),
    enabled: expanded,
  })

  return (
    <div className="bg-white border rounded-xl overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-xs px-2 py-1 rounded-full font-medium ${
                  statusColors[review.status]
                }`}
              >
                {review.status}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(review.created_at).toLocaleDateString()}
              </span>
            </div>
            <div className="text-sm text-gray-500">
              Evaluation:{" "}
              <span className="font-mono text-xs">{review.evaluation_id}</span>
            </div>
          </div>
          {evaluation && (
            <div className="text-right">
              <div className="text-sm font-medium capitalize">
                {evaluation.provider}
              </div>
              <div className="text-xs text-gray-500">
                score:{" "}
                {evaluation.score !== null
                  ? `${Math.round(evaluation.score * 100)}%`
                  : "—"}
              </div>
            </div>
          )}
        </div>

        {/* Response preview */}
        {evaluation?.response && (
          <div className="bg-gray-50 rounded-lg p-3 mb-4">
            <div className="text-xs text-gray-500 mb-1">Response</div>
            <p className="text-sm text-gray-700 line-clamp-3">
              {evaluation.response}
            </p>
          </div>
        )}

        {/* Traces toggle */}
        <button
          className="text-xs text-blue-500 hover:text-blue-700 mb-4"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Hide traces" : "Show traces"}
        </button>

        {/* Traces */}
        {expanded && traces && (
          <div className="mb-4 space-y-1">
            {traces.map((trace, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 rounded px-3 py-1.5"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                <span className="font-medium">{trace.event_type}</span>
                {trace.latency_ms && (
                  <span className="text-gray-400">{trace.latency_ms}ms</span>
                )}
                <span className="text-gray-400 ml-auto">
                  {new Date(trace.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Review action */}
        {review.status === "pending" && (
          <div className="border-t pt-4">
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm mb-3 resize-none h-20"
              placeholder="Add a comment (optional)..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                className="flex items-center gap-1.5 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 transition-colors"
                onClick={() => onAction(review.id, "approved", comment)}
              >
                <CheckCircle size={14} />
                Approve
              </button>
              <button
                className="flex items-center gap-1.5 bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700 transition-colors"
                onClick={() => onAction(review.id, "rejected", comment)}
              >
                <XCircle size={14} />
                Reject
              </button>
            </div>
          </div>
        )}

        {/* Completed review */}
        {review.status !== "pending" && review.comment && (
          <div className="border-t pt-4">
            <div className="flex items-start gap-2 text-sm text-gray-600">
              <MessageSquare size={14} className="mt-0.5 shrink-0" />
              <span>{review.comment}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ReviewsPage() {
  const queryClient = useQueryClient()

  useRealtimeReviewQueue()

  const { data: queue, isLoading } = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => apiFetch<Review[]>("/reviews/queue"),
  })

  const submitReview = useMutation({
    mutationFn: ({
      reviewId,
      status,
      comment,
    }: {
      reviewId: string
      status: string
      comment: string
    }) =>
      apiFetch(`/reviews/${reviewId}`, {
        method: "POST",
        body: JSON.stringify({ status, comment: comment || null }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
    },
  })

  const handleAction = (id: string, status: string, comment: string) => {
    submitReview.mutate({ reviewId: id, status, comment })
  }

  const pending = queue?.filter((r) => r.status === "pending") || []
  const completed = queue?.filter((r) => r.status !== "pending") || []

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <ClipboardCheck size={20} className="text-blue-500" />
          <h1 className="text-2xl font-bold">Review Queue</h1>
        </div>
        <p className="text-gray-500">
          Evaluations flagged for human review due to low scores or divergence.
        </p>
      </div>

      {isLoading && (
        <div className="animate-pulse space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-40 bg-gray-200 rounded-xl" />
          ))}
        </div>
      )}

      {/* Pending */}
      {pending.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            Pending
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full">
              {pending.length}
            </span>
          </h2>
          <div className="space-y-4">
            {pending.map((review) => (
              <ReviewCard
                key={review.id}
                review={review}
                onAction={handleAction}
              />
            ))}
          </div>
        </div>
      )}

      {/* Completed */}
      {completed.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3 text-gray-600">
            Completed
          </h2>
          <div className="space-y-4">
            {completed.map((review) => (
              <ReviewCard
                key={review.id}
                review={review}
                onAction={handleAction}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && queue?.length === 0 && (
        <div className="bg-white border rounded-xl p-12 text-center">
          <ClipboardCheck
            className="mx-auto text-gray-300 mb-3"
            size={40}
          />
          <p className="text-gray-500">No reviews pending.</p>
          <p className="text-gray-400 text-sm mt-1">
            Evaluations with low scores or divergence will appear here.
          </p>
        </div>
      )}
    </div>
  )
}
