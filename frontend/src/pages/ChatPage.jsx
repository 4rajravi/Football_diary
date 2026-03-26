import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, BarChart3 } from 'lucide-react'
import { sendChatMessage } from '../services/api'
import ChartRenderer from '../components/ChartRenderer'

const SUGGESTIONS = [
  'Compare Messi vs Ronaldo in Champions League',
  'Show me the Premier League top scorers 2023',
  'Head-to-head: Barcelona vs Real Madrid',
  'Which player has the best goals per 90 this season?',
  "Show me Liverpool's form in their last 10 matches",
  'Who scored the most goals in the 2022 World Cup?',
]

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return

    const userMsg = { role: 'user', content: msg }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const response = await sendChatMessage(msg)
      const assistantMsg = {
        role: 'assistant',
        content: response.answer,
        chart: response.chart || null,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <EmptyState onSuggestionClick={(s) => handleSend(s)} />
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`animate-fade-in ${
                msg.role === 'user' ? 'flex justify-end' : ''
              }`}
            >
              {msg.role === 'user' ? (
                <div className="bg-surface border border-border rounded-2xl rounded-br-md px-4 py-3 max-w-lg">
                  {msg.content}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-surface border border-border rounded-2xl rounded-bl-md px-5 py-4 max-w-2xl">
                    <p className="text-white/90 leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </p>
                  </div>
                  {msg.chart && (
                    <div className="bg-surface border border-border rounded-xl p-4 max-w-2xl">
                      <ChartRenderer config={msg.chart} />
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="animate-fade-in flex items-center gap-2 text-white/40">
              <Loader2 size={16} className="animate-spin text-muted" />
              <span className="text-sm text-muted">Analyzing football data...</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-white/10 px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any match, player, or club..."
            className="flex-1 bg-surface border border-border rounded-xl px-4 py-3 text-sm
                       placeholder:text-muted focus:outline-none focus:border-white/20
                       transition-colors"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="bg-grass hover:bg-green-600 disabled:opacity-30 disabled:cursor-not-allowed
                       text-white rounded-xl px-4 py-3 transition-colors"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onSuggestionClick }) {
  return (
    <div className="flex flex-col items-center justify-center h-[50vh] text-center">
      <div className="bg-white/5 rounded-full p-4 mb-4">
        <BarChart3 size={32} className="text-grass" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Football Diary AI</h2>
      <p className="text-white/40 mb-8 max-w-md">
        Ask me anything about football — match history, player comparisons,
        club records, or unique stats. I'll search the database and show you
        charts when it helps.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSuggestionClick(s)}
            className="text-left text-sm px-4 py-3 rounded-lg border border-border
                       bg-surface hover:bg-surface-hover transition-colors text-muted
                       hover:text-white"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
