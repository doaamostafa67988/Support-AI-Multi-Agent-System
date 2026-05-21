"use client"

import { useEffect, useState, useRef, useCallback } from "react"

// BUG FIX 21: The old frontend sent and received raw text strings.
// The fixed backend now sends JSON frames: { type: "ai" | "error", text: string }.
// The frontend must parse these instead of treating every message as an AI reply.

// BUG FIX 22: No reconnection logic. If the WebSocket dropped (server restart,
// network blip), the chat silently died with no indication to the user.
// Fix: exponential-backoff reconnect with visible status indicator.

// BUG FIX 23: No loading / "thinking" state. After sending a message the user had
// no feedback that the system was working. Fix: show a typing indicator.

interface Message {
  id: number
  sender: "user" | "ai" | "error" | "system"
  text: string
  ts: Date
}

type ConnState = "connecting" | "connected" | "reconnecting" | "failed"

const MAX_RECONNECT = 5
const BACKEND_PORT = 8000

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0,
      sender: "system",
      text: "👋 Hello! I'm your AI support assistant. How can I help you today?",
      ts: new Date(),
    },
  ])
  const [input, setInput] = useState("")
  const [connState, setConnState] = useState<ConnState>("connecting")
  const [isThinking, setIsThinking] = useState(false)

  const socketRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const msgId = useRef(1)
  const bottomRef = useRef<HTMLDivElement>(null)

  const addMessage = useCallback((sender: Message["sender"], text: string) => {
    setMessages((prev) => [
      ...prev,
      { id: msgId.current++, sender, text, ts: new Date() },
    ])
  }, [])

  const connect = useCallback(() => {
    // Clean up existing socket
    if (socketRef.current) {
      socketRef.current.onclose = null
      socketRef.current.close()
    }

    const hostname = window.location.hostname
    const ws = new WebSocket(`ws://${hostname}:${BACKEND_PORT}/ws/chat`)
    socketRef.current = ws

    ws.onopen = () => {
      setConnState("connected")
      reconnectAttempts.current = 0
      if (reconnectAttempts.current > 0) {
        addMessage("system", "✅ Reconnected to support server.")
      }
    }

    ws.onmessage = (event) => {
      setIsThinking(false)
      try {
        const frame = JSON.parse(event.data) as { type: string; text: string }
        if (frame.type === "error") {
          addMessage("error", frame.text)
        } else {
          addMessage("ai", frame.text)
        }
      } catch {
        // Fallback: plain text (backwards compat)
        addMessage("ai", event.data)
      }
    }

    ws.onerror = () => {
      setIsThinking(false)
    }

    ws.onclose = () => {
      setIsThinking(false)
      const attempts = reconnectAttempts.current

      if (attempts >= MAX_RECONNECT) {
        setConnState("failed")
        addMessage("error", "Connection lost. Please refresh the page.")
        return
      }

      setConnState("reconnecting")
      const delay = Math.min(1000 * 2 ** attempts, 16000)
      reconnectAttempts.current = attempts + 1

      reconnectTimer.current = setTimeout(connect, delay)
    }
  }, [addMessage])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      socketRef.current?.close()
    }
  }, [connect])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isThinking])

  const sendMessage = () => {
    const ws = socketRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN || !input.trim() || isThinking) return

    const text = input.trim()
    addMessage("user", text)
    setInput("")
    setIsThinking(true)
    ws.send(text)
  }

  const statusColor: Record<ConnState, string> = {
    connected: "bg-emerald-400",
    connecting: "bg-yellow-400 animate-pulse",
    reconnecting: "bg-orange-400 animate-pulse",
    failed: "bg-red-500",
  }

  const statusLabel: Record<ConnState, string> = {
    connected: "Connected",
    connecting: "Connecting…",
    reconnecting: "Reconnecting…",
    failed: "Disconnected",
  }

  return (
    <div className="flex flex-col h-screen bg-[#0f0f13] text-white font-sans">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#15151c]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-lg font-bold shadow-lg shadow-violet-900/40">
            ⚡
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white">
              Support AI
            </h1>
            <p className="text-xs text-white/40">Multi-Agent Customer Support</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-white/50">
          <span className={`w-2 h-2 rounded-full ${statusColor[connState]}`} />
          {statusLabel[connState]}
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/10">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.sender !== "user" && (
              <div className="w-7 h-7 mt-1 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-xs flex-shrink-0">
                {msg.sender === "error" ? "⚠" : "✦"}
              </div>
            )}
            <div
              className={`max-w-[78%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                msg.sender === "user"
                  ? "bg-violet-600 text-white rounded-br-sm"
                  : msg.sender === "error"
                  ? "bg-red-900/40 border border-red-500/30 text-red-200 rounded-bl-sm"
                  : msg.sender === "system"
                  ? "bg-white/5 border border-white/10 text-white/70 rounded-bl-sm italic"
                  : "bg-[#1e1e2a] border border-white/10 text-white/90 rounded-bl-sm"
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isThinking && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 mt-1 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-xs flex-shrink-0">
              ✦
            </div>
            <div className="bg-[#1e1e2a] border border-white/10 px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-6 pt-3 border-t border-white/10 bg-[#15151c]">
        <div className="flex gap-3 max-w-3xl mx-auto">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                sendMessage()
              }
            }}
            placeholder={
              connState === "connected"
                ? "Ask about your order, refunds, or returns…"
                : "Waiting for connection…"
            }
            disabled={connState !== "connected" || isThinking}
            className="flex-1 bg-[#0f0f13] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-violet-500/60 disabled:opacity-40 transition-colors"
          />
          <button
            onClick={sendMessage}
            disabled={connState !== "connected" || isThinking || !input.trim()}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-30 disabled:cursor-not-allowed text-white font-medium px-5 py-3 rounded-xl text-sm transition-colors shadow-lg shadow-violet-900/30"
          >
            Send
          </button>
        </div>
        <p className="text-center text-xs text-white/20 mt-2">
          Powered by LangGraph · Groq · ChromaDB
        </p>
      </div>
    </div>
  )
}
