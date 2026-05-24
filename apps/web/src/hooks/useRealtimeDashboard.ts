import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { supabase } from "@/lib/supabase"

export function useRealtimeDashboard() {
  const queryClient = useQueryClient()

  useEffect(() => {
    const client = supabase
    if (!client) return

    const channel = client
      .channel("dashboard")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "evaluations",
        },
        () => {
          queryClient.invalidateQueries({ queryKey: ["provider-metrics"] })
          queryClient.invalidateQueries({ queryKey: ["evaluations-list"] })
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "evaluations",
        },
        () => {
          queryClient.invalidateQueries({ queryKey: ["provider-metrics"] })
          queryClient.invalidateQueries({ queryKey: ["evaluations-list"] })
        }
      )
      .subscribe()

    return () => {
      client.removeChannel(channel)
    }
  }, [queryClient])
}
