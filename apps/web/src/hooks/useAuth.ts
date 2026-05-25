"use client"

import { useEffect, useState, useCallback } from "react"
import { supabase } from "@/lib/supabase"
import { useRouter } from "next/navigation"
import type { User } from "@supabase/supabase-js"

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    if (!supabase) {
      // Use setTimeout to avoid setState in effect body
      const timer = setTimeout(() => setLoading(false), 0)
      return () => clearTimeout(timer)
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setUser(session?.user ?? null)
        setLoading(false)

        if (event === "SIGNED_OUT") {
          router.push("/auth")
        }

        if (event === "SIGNED_IN") {
          router.push("/")
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [router])

  const signOut = useCallback(async () => {
    await supabase?.auth.signOut()
  }, [])

  return { user, loading, signOut }
}