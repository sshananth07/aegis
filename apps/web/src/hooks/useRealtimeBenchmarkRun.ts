import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { supabase } from "@/lib/supabase"

export function useRealtimeBenchmarkRun(runId: string) {
  const queryClient = useQueryClient()

  useEffect(() => {
    const client = supabase
    if (!runId || !client) return

    const channel = client
      .channel(`benchmark_run:${runId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "benchmark_runs",
          filter: `id=eq.${runId}`,
        },
        (payload: { new: Record<string, unknown> }) => {
          queryClient.setQueryData(
            ["run", runId],
            (old: unknown) =>
              old && typeof old === "object"
                ? { ...old, ...payload.new }
                : payload.new
          )
          if (payload.new.status === "completed") {
            queryClient.invalidateQueries({
              queryKey: ["provider-summary", runId],
            })
          }
        }
      )
      .subscribe()

    return () => {
      client.removeChannel(channel)
    }
  }, [runId, queryClient])
}
