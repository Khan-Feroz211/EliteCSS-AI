import { useEffect, useRef, useState } from "react"

const MODELS = [
  { id: "gpt",    label: "GPT-4o mini", color: "bg-emerald-500", ring: "ring-emerald-400", text: "text-emerald-700", light: "bg-emerald-50" },
  { id: "claude", label: "Claude",       color: "bg-amber-500",  ring: "ring-amber-400",  text: "text-amber-700",  light: "bg-amber-50"   },
  { id: "gemini", label: "Gemini",       color: "bg-blue-500",   ring: "ring-blue-400",   text: "text-blue-700",   light: "bg-blue-50"    },
]

const CHIPS = [
  "Explain Pakistan Affairs topics for CSS",
  "What are important essays for CSS 2025?",
  "Key events in Pakistan history for CSS",
  "Tips for CSS précis writing",
  "Current affairs Pakistan 2024-25",
  "Recommended books for CSS preparation",
]

const API = import.meta.env.VITE_API_BASE_URL || ""

export default function App() {
  const [screen, setScreen]             = useState("login")
  const [messages, setMessages]         = useState([])
  const [input, setInput]               = useState("")
  const [model, setModel]               = useState("gpt")
  const [loading, setLoading]           = useState(false)
  const [streamingId, setStreamingId]   = useState(null)
  const [error, setError]               = useState("")
  const [authEmail, setAuthEmail]       = useState("")
  const [authPassword, setAuthPassword] = useState("")
  const [authConfirm, setAuthConfirm]   = useState("")
  const [authError, setAuthError]       = useState("")
  const [authLoading, setAuthLoading]   = useState(false)
  const [userEmail, setUserEmail]       = useState("")

  const bottomRef   = useRef(null)
  const textareaRef = useRef(null)

  // Check for existing token on mount
  useEffect(() => {
    const token = localStorage.getItem("css_prep_token")
    const email = localStorage.getItem("css_prep_email")
    if (token) {
      setUserEmail(email || "")
      setScreen("chat")
    }
  }, [])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px"
    }
  }, [input])

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleRegister = async () => {
    setAuthError("")
    if (authPassword !== authConfirm) {
      setAuthError("Passwords do not match")
      return
    }
    setAuthLoading(true)
    try {
      const res = await fetch(`${API}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      })
      if (res.status === 201) {
        setAuthEmail("")
        setAuthPassword("")
        setAuthConfirm("")
        setAuthError("")
        setScreen("login")
      } else if (res.status === 409) {
        setAuthError("Email already registered")
      } else {
        const data = await res.json().catch(() => ({}))
        setAuthError(data.detail || "Registration failed")
      }
    } catch {
      setAuthError("Network error. Please try again.")
    } finally {
      setAuthLoading(false)
    }
  }

  const handleLogin = async () => {
    setAuthError("")
    setAuthLoading(true)
    try {
      const form = new FormData()
      form.append("username", authEmail)
      form.append("password", authPassword)
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        body: form,
      })
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem("css_prep_token", data.access_token)
        localStorage.setItem("css_prep_email", authEmail)
        setUserEmail(authEmail)
        setScreen("chat")
      } else if (res.status === 401) {
        setAuthError("Invalid email or password")
      } else {
        const data = await res.json().catch(() => ({}))
        setAuthError(data.detail || "Login failed")
      }
    } catch {
      setAuthError("Network error. Please try again.")
    } finally {
      setAuthLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("css_prep_token")
    localStorage.removeItem("css_prep_email")
    setScreen("login")
    setMessages([])
    setUserEmail("")
  }

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const token = localStorage.getItem("css_prep_token")
    if (!token) { handleLogout(); return }

    const userMsg = { id: crypto.randomUUID(), role: "user", content: input.trim() }
    const assistantId = crypto.randomUUID()
    const assistantMsg = {
      id: assistantId,
      role: "assistant",
      content: "",
      model,
      latency_ms: null,
      streaming: true,
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setInput("")
    setLoading(true)
    setError("")
    setStreamingId(assistantId)

    const start = Date.now()

    try {
      const res = await fetch(`${API}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + token,
        },
        body: JSON.stringify({
          message: userMsg.content,
          model,
          history: messages
            .filter(m => !m.streaming)
            .map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (res.status === 401) { handleLogout(); return }
      if (!res.ok) { throw new Error(`HTTP ${res.status}`) }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let done = false

      while (!done) {
        const { value, done: streamDone } = await reader.read()
        if (streamDone) break
        const text = decoder.decode(value)
        const lines = text.split("\n")
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          const data = line.slice(6)
          if (data === "[DONE]") { done = true; break }
          if (data.startsWith("[ERROR]")) {
            setError(data.slice(7).trim() || "Streaming error")
            done = true
            break
          }
          const chunk = data.replace(/\\n/g, "\n")
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, content: m.content + chunk } : m
          ))
        }
      }

      const latency = Date.now() - start
      setMessages(prev => prev.map(m =>
        m.id === assistantId ? { ...m, streaming: false, latency_ms: latency } : m
      ))
    } catch (err) {
      setError(err.message || "Something went wrong")
      setMessages(prev => prev.filter(m => m.id !== assistantId))
    } finally {
      setLoading(false)
      setStreamingId(null)
    }
  }

  // AUTH SCREENS
  if (screen === "login" || screen === "register") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-semibold text-gray-900">CSS Prep AI</h1>
            <p className="text-gray-500 mt-2">Pakistan CSS Exam Assistant</p>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              {screen === "login" ? "Welcome back" : "Create account"}
            </h2>

            {authError && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-4">
                {authError}
              </div>
            )}

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={authEmail}
                onChange={e => setAuthEmail(e.target.value)}
                onKeyDown={e => e.key === "Enter" && (screen === "login" ? handleLogin() : handleRegister())}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                value={authPassword}
                onChange={e => setAuthPassword(e.target.value)}
                onKeyDown={e => e.key === "Enter" && (screen === "login" ? handleLogin() : handleRegister())}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition"
              />
            </div>

            {screen === "register" && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                <input
                  type="password"
                  value={authConfirm}
                  onChange={e => setAuthConfirm(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleRegister()}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition"
                />
              </div>
            )}

            <button
              onClick={screen === "login" ? handleLogin : handleRegister}
              disabled={authLoading}
              className="w-full bg-gray-900 text-white rounded-xl py-3 text-sm font-medium hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {authLoading ? "Please wait..." : screen === "login" ? "Sign in" : "Create account"}
            </button>

            <p className="text-center text-sm text-gray-500 mt-6">
              {screen === "login" ? "Don't have an account? " : "Already have an account? "}
              <button
                onClick={() => { setAuthError(""); setScreen(screen === "login" ? "register" : "login") }}
                className="text-gray-900 font-medium hover:underline"
              >
                {screen === "login" ? "Register" : "Sign in"}
              </button>
            </p>
          </div>
        </div>
      </div>
    )
  }

  // CHAT SCREEN
  return (
    <div className="flex flex-col h-screen bg-white">
      {/* HEADER */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white sticky top-0 z-10">
        <div>
          <h1 className="font-semibold text-gray-900">CSS Prep AI</h1>
          <p className="text-xs text-gray-400">{userEmail}</p>
        </div>
        <div className="flex items-center gap-2">
          {MODELS.map(m => (
            <button
              key={m.id}
              onClick={() => setModel(m.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition border ${
                model === m.id
                  ? `${m.color} text-white border-transparent`
                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-300"
              }`}
            >
              {m.label}
            </button>
          ))}
          <button
            onClick={handleLogout}
            className="ml-2 text-xs text-gray-400 hover:text-gray-600 transition px-2 py-1.5 rounded-lg hover:bg-gray-50"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* MESSAGE THREAD */}
      <div className="flex-1 overflow-y-auto scrollbar-hide px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-6">

          {/* EMPTY STATE */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="text-4xl mb-4">✦</div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">What can I help you with?</h2>
              <p className="text-gray-400 text-sm mb-8">Ask anything about the CSS competitive exam</p>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {CHIPS.map(chip => (
                  <button
                    key={chip}
                    onClick={() => setInput(chip)}
                    className="px-4 py-2 bg-gray-50 hover:bg-gray-100 text-gray-600 text-xs rounded-full border border-gray-200 hover:border-gray-300 transition text-left"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* MESSAGES */}
          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
              {msg.role === "assistant" && (
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-1 ${MODELS.find(m => m.id === msg.model)?.color || "bg-gray-400"}`}>
                  {msg.model?.[0]?.toUpperCase()}
                </div>
              )}
              <div className={`max-w-[75%] ${
                msg.role === "user"
                  ? "bg-gray-900 text-white rounded-3xl rounded-tr-sm px-5 py-3"
                  : "bg-gray-50 text-gray-800 rounded-3xl rounded-tl-sm px-5 py-3"
              }`}>
                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {msg.content}
                  {msg.streaming && (
                    <span className="inline-block w-0.5 h-4 bg-gray-400 ml-0.5 animate-pulse align-middle" />
                  )}
                </p>
                {!msg.streaming && msg.latency_ms && (
                  <p className="text-xs text-gray-400 mt-1">
                    {MODELS.find(m => m.id === msg.model)?.label} · {(msg.latency_ms / 1000).toFixed(1)}s
                  </p>
                )}
              </div>
            </div>
          ))}

          {/* ERROR BANNER */}
          {error && (
            <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-xl px-4 py-3">
              <p className="text-sm text-red-600">{error}</p>
              <button
                onClick={() => setError("")}
                className="text-red-400 hover:text-red-600 ml-4 text-lg leading-none"
              >
                ×
              </button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* INPUT AREA */}
      <div className="border-t border-gray-100 bg-white px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-3 bg-gray-50 rounded-2xl px-4 py-3 border border-gray-200 focus-within:border-gray-400 transition">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about Pakistan Affairs, essays, past papers..."
              rows={1}
              maxLength={2000}
              className="flex-1 bg-transparent resize-none outline-none text-sm text-gray-900 placeholder-gray-400 max-h-40 leading-relaxed"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition ${
                loading || !input.trim()
                  ? "bg-gray-200 cursor-not-allowed"
                  : "bg-gray-900 hover:bg-gray-700 cursor-pointer"
              }`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </div>
          <div className="flex justify-between mt-2 px-1">
            <p className="text-xs text-gray-400">Enter to send · Shift+Enter for new line</p>
            <p className="text-xs text-gray-400">{input.length}/2000</p>
          </div>
        </div>
      </div>
    </div>
  )
}
