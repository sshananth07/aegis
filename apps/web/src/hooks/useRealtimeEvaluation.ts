import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { supabase } from "@/lib/supabase"

export function useRealtimeEvaluation(evaluationId: string) {
  const queryClient = useQueryClient()

  useEffect(() => {
    const client = supabase
    if (!evaluationId || !client) return

    const channel = client
      .channel(`evaluation:${evaluationId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "evaluations",
          filter: `id=eq.${evaluationId}`,
        },
        (payload: { new: Record<string, unknown> }) => {
          queryClient.setQueryData(
            ["evaluation", evaluationId],
            (old: unknown) =>
              old && typeof old === "object"
                ? { ...old, ...payload.new }
                : payload.new
          )
        }
      )
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "traces",
          filter: `evaluation_id=eq.${evaluationId}`,
        },
        () => {
          queryClient.invalidateQueries({
            queryKey: ["traces", evaluationId],
          })
        }
      )
      .subscribe()

    return () => {
      client.removeChannel(channel)
    }
  }, [evaluationId, queryClient])
}
