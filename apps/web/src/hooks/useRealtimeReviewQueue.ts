import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { supabase } from "@/lib/supabase"

export function useRealtimeReviewQueue() {
  const queryClient = useQueryClient()

  useEffect(() => {
    const client = supabase
    if (!client) return

    const channel = client
      .channel("review_queue")
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "evaluations",
        },
        (payload: { new: Record<string, unknown> }) => {
          if (payload.new.status === "review_required") {
            queryClient.invalidateQueries({ queryKey: ["review-queue"] })
          }
        }
      )
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "reviews",
        },
        () => {
          queryClient.invalidateQueries({ queryKey: ["review-queue"] })
        }
      )
      .subscribe()

    return () => {
      client.removeChannel(channel)
    }
  }, [queryClient])
}
