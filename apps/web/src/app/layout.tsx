import type { Metadata } from "next"
import { Providers } from "./providers"
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
          {children}
        </Providers>
      </body>
    </html>
  )
}
