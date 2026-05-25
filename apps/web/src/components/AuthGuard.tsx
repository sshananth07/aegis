"use client"

import { useAuth } from "@/hooks/useAuth"
import { usePathname, useRouter } from "next/navigation"
import { useEffect } from "react"
import { Sidebar } from "@/components/layout/Sidebar"

const PUBLIC_ROUTES = ["/auth", "/auth/callback"]

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const pathname = usePathname()
  const router = useRouter()
  const isPublic = PUBLIC_ROUTES.some(route => pathname.startsWith(route))

  useEffect(() => {
    if (!loading && !user && !isPublic) {
      router.push("/auth")
    }
  }, [user, loading, isPublic, router])

  // Always show loading spinner until auth state is known
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500 text-sm">Loading...</p>
        </div>
      </div>
    )
  }

  if (isPublic) return <>{children}</>

  // Don't render protected content until user is confirmed
  if (!user) return null

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}