"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  MessageSquare,
  FlaskConical,
  ClipboardCheck,
  Activity,
  Zap,
  LogOut,
  Database,
  Key
} from "lucide-react"
import { RealtimeIndicator } from "@/components/layout/RealtimeIndicator"
import { useAuth } from "@/hooks/useAuth"
import { BarChart2 } from "lucide-react"

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/playground", icon: Zap, label: "Playground" },
  { href: "/prompts", icon: MessageSquare, label: "Prompts" },
  { href: "/benchmarks", icon: FlaskConical, label: "Benchmarks" },
  { href: "/reviews", icon: ClipboardCheck, label: "Reviews" },
  { href: "/traces", icon: Activity, label: "Traces" },
  { href: "/datasets", icon: Database, label: "Datasets" },
  { href: "/analytics", icon: BarChart2, label: "Analytics" },
  { href: "/api-keys", icon: Key, label: "API Keys" },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, signOut } = useAuth()

  return (
    <aside className="w-60 min-h-screen bg-gray-950 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-white rounded-md flex items-center justify-center">
            <span className="text-gray-950 font-bold text-sm">A</span>
          </div>
          <span className="text-white font-semibold text-lg">Aegis</span>
        </div>
        <p className="text-gray-500 text-xs mt-1">AI Evaluation Platform</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href))

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-white text-gray-950 font-medium"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <Icon size={16} />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-800">
        <RealtimeIndicator />
        <div className="px-3 py-3 border-t border-gray-800">
          <div className="text-xs text-gray-500 px-3 mb-2 truncate">
            {user?.email}
          </div>
          <button
            onClick={signOut}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 w-full transition-colors"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
        <div className="px-6 pb-4">
          <p className="text-gray-600 text-xs">MVP v0.1.0</p>
        </div>
      </div>
    </aside>
  )
}
