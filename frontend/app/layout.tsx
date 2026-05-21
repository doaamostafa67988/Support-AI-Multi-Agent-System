import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Support AI — Multi-Agent Customer Support",
  description: "AI-powered customer support system built with LangGraph, Groq, and ChromaDB.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
