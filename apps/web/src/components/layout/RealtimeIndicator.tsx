"use client"

import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"

export function RealtimeIndicator() {
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const client = supabase
    if (!client) return

    const channel = client.channel("connection-check")
      .subscribe((status: string) => {
        setConnected(status === "SUBSCRIBED")
      })

    return () => {
      client.removeChannel(channel)
    }
  }, [])

  return (
    <div className="flex items-center gap-1.5 px-6 py-3">
      <div
        className={`w-1.5 h-1.5 rounded-full ${
          connected ? "bg-green-500 animate-pulse" : "bg-gray-500"
        }`}
      />
      <span className="text-xs text-gray-500">
        {connected ? "Live" : "Connecting..."}
      </span>
    </div>
  )
}
