import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { supabase } from "@/lib/supabase"

export function useRealtimeJob(jobId: string | null) {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!jobId || !supabase) return

    const channel = supabase
      .channel(`job:${jobId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "jobs",
          filter: `id=eq.${jobId}`,
        },
        (payload) => {
          queryClient.setQueryData(
            ["job", jobId],
            (old: Record<string, unknown>) => ({ ...old, ...payload.new })
          )
        }
      )
      .subscribe()

    return () => {
      if (!supabase) return
      supabase.removeChannel(channel)
    }
  }, [jobId, queryClient])
}