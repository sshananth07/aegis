import type { Metadata } from "next"
import { Providers } from "./providers"
import { Sidebar } from "@/components/layout/Sidebar"
import "./globals.css"

export const metadata: Metadata = {
  title: "Aegis — AI Evaluation Platform",
  description: "Cloud-native AI evaluation and reliability platform",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50">
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 overflow-auto">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
