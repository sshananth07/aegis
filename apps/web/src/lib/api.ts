import { supabase } from "@/lib/supabase"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function getToken(): Promise<string | null> {
  if (!supabase) return null

  // First try to get existing session
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) return session.access_token

  // If no session, wait for auth state to settle
  return new Promise((resolve) => {
    const { data: { subscription } } = supabase!.auth.onAuthStateChange(
      (_event, session) => {
        subscription.unsubscribe()
        resolve(session?.access_token ?? null)
      }
    )
    // Timeout after 3 seconds
    setTimeout(() => {
      subscription.unsubscribe()
      resolve(null)
    }, 3000)
  })
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = await getToken()

  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    ...options,
  })

  if (res.status === 401) {
    window.location.href = "/auth"
    throw new Error("Unauthorized")
  }

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error)
  }

  return res.json()
}