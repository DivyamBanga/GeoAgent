import { useState, useRef, useEffect } from "react"
import type { MapMarker } from "./MapPanel"
import ScoreCard, { type Scores } from "./ScoreCard"

interface Message {
  role: "user" | "assistant" | "status"
  content: string
  scores?: Scores
}

interface ChatPanelProps {
  onMapUpdate: (markers: MapMarker[]) => void
  onCenterChange: (center: [number, number]) => void
}

export default function ChatPanel({ onMapUpdate, onCenterChange: _onCenterChange }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => { scrollToBottom() }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const question = input.trim()
    setInput("")
    setMessages(prev => [...prev, { role: "user", content: question }])
    setLoading(true)

    // Collect scores from tool_result events during this request
    const collectedScores: Scores = {}

    try {
      const response = await fetch("http://localhost:8000/api/analyze/stream/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue

          const data = JSON.parse(line.slice(6))

          if (data.type === "status") {
            setMessages(prev => [...prev, { role: "status", content: data.message }])
          } else if (data.type === "tool_call") {
            setMessages(prev => [...prev, {
              role: "status",
              content: `Calling ${data.tool}...`
            }])
          } else if (data.type === "tool_result") {
            // Collect score from this tool
            if (data.result && typeof data.result.score === "number") {
              collectedScores[data.tool] = data.result.score
            }
            // Update map with competitor data
            if (data.tool === "find_competitors" && data.result.competitors) {
              const competitorMarkers: MapMarker[] = data.result.competitors.map(
                (c: { name: string; lat?: number; lng?: number }) => ({
                  lat: c.lat || 0,
                  lng: c.lng || 0,
                  label: c.name,
                  type: "competitor" as const,
                })
              )
              onMapUpdate(competitorMarkers)
            }
          } else if (data.type === "answer") {
            // Compute overall score from collected sub-scores
            const scoreValues = Object.values(collectedScores)
            if (scoreValues.length > 0) {
              collectedScores.overall = Math.round(
                scoreValues.reduce((sum, s) => sum + s, 0) / scoreValues.length
              )
            }

            setMessages(prev => [...prev, {
              role: "assistant",
              content: data.content,
              scores: scoreValues.length > 0 ? { ...collectedScores } : undefined,
            }])
          }
        }
      }
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Error connecting to server." }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "16px", borderBottom: "1px solid #e0e0e0" }}>
        <h2 style={{ margin: 0 }}>GeoAgent</h2>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
        {messages.map((msg, i) => (
          <div key={i}>
            <div style={{
              marginBottom: msg.scores ? "4px" : "12px",
              padding: "8px 12px",
              borderRadius: "8px",
              backgroundColor: msg.role === "user" ? "#e3f2fd"
                : msg.role === "status" ? "#fff3e0"
                : "#f5f5f5",
              fontSize: msg.role === "status" ? "0.85em" : "1em",
              color: msg.role === "status" ? "#e65100" : "#212121",
              whiteSpace: "pre-wrap",
            }}>
              {msg.content}
            </div>
            {msg.scores && (
              <div style={{ marginBottom: "12px" }}>
                <ScoreCard scores={msg.scores} />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} style={{ padding: "16px", borderTop: "1px solid #e0e0e0", display: "flex", gap: "8px" }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about a location..."
          disabled={loading}
          style={{ flex: 1, padding: "10px", borderRadius: "6px", border: "1px solid #ccc", fontSize: "1em" }}
        />
        <button type="submit" disabled={loading}
          style={{
            padding: "10px 20px", borderRadius: "6px",
            background: loading ? "#90caf9" : "#1976d2",
            color: "white", border: "none", cursor: loading ? "default" : "pointer",
            fontSize: "1em",
          }}>
          {loading ? "..." : "Ask"}
        </button>
      </form>
    </div>
  )
}
