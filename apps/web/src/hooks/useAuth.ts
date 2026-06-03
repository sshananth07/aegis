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

        // Only redirect to home on fresh sign in from auth page
        if (event === "SIGNED_IN") {
          const currentPath = window.location.pathname
          if (currentPath === "/auth" || currentPath === "/auth/callback") {
            router.push("/")
          }
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