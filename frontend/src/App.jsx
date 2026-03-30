import { useEffect, useMemo, useRef, useState } from "react";

import ChatWindow from "./components/ChatWindow";
import MessageInput from "./components/MessageInput";
import ModelSelector from "./components/ModelSelector";
import { useLocalStorage } from "./hooks/useLocalStorage";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const TOKEN_KEY = "css_prep_token";
const EMAIL_KEY = "css_prep_email";

const TOPICS = [
  "Pakistan Affairs",
  "History",
  "Current Affairs",
  "Essay",
  "General Knowledge",
];

function buildStarter(topic) {
  return `Give me a CSS exam prep answer on ${topic} for Pakistan. Include key points and one likely exam question.`;
}

function createSessionId() {
  const key = "css-prep-ai-session-id";
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const next = `sess-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  window.localStorage.setItem(key, next);
  return next;
}

function isTokenValid(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp && payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export default function App() {
  const [messages, setMessages] = useLocalStorage("css-prep-ai-messages", []);
  const [selectedModel, setSelectedModel] = useLocalStorage("css-prep-ai-model", "gpt");
  const [theme, setTheme] = useLocalStorage("css-prep-ai-theme", "dark");
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastAttempt, setLastAttempt] = useState(null);
  const streamRef = useRef(null);

  // Auth state
  const [screen, setScreen] = useState("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authConfirmPassword, setAuthConfirmPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [loggedInEmail, setLoggedInEmail] = useState("");

  const sessionId = useMemo(() => createSessionId(), []);

  // Check for existing token on mount
  useEffect(() => {
    const token = window.localStorage.getItem(TOKEN_KEY);
    const email = window.localStorage.getItem(EMAIL_KEY);
    if (token && isTokenValid(token)) {
      setLoggedInEmail(email || "");
      setScreen("chat");
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
      window.localStorage.removeItem(EMAIL_KEY);
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
  }, [theme]);

  useEffect(() => {
    return () => {
      streamRef.current?.close();
    };
  }, []);

  const handleRegister = async () => {
    setAuthError("");
    if (authPassword !== authConfirmPassword) {
      setAuthError("Passwords do not match");
      return;
    }
    setAuthLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      if (res.status === 201) {
        setAuthEmail("");
        setAuthPassword("");
        setAuthConfirmPassword("");
        setAuthError("");
        setScreen("login");
      } else if (res.status === 409) {
        setAuthError("Email already registered");
      } else {
        const data = await res.json().catch(() => ({}));
        setAuthError(data.detail || "Registration failed");
      }
    } catch {
      setAuthError("Network error. Please try again.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogin = async () => {
    setAuthError("");
    setAuthLoading(true);
    try {
      const form = new FormData();
      form.append("username", authEmail);
      form.append("password", authPassword);
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        body: form,
      });
      if (res.ok) {
        const data = await res.json();
        window.localStorage.setItem(TOKEN_KEY, data.access_token);
        window.localStorage.setItem(EMAIL_KEY, authEmail);
        setLoggedInEmail(authEmail);
        setAuthEmail("");
        setAuthPassword("");
        setScreen("chat");
      } else if (res.status === 401) {
        setAuthError("Invalid email or password");
      } else {
        const data = await res.json().catch(() => ({}));
        setAuthError(data.detail || "Login failed");
      }
    } catch {
      setAuthError("Network error. Please try again.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(EMAIL_KEY);
    setMessages([]);
    setError("");
    setLastAttempt(null);
    setLoggedInEmail("");
    setScreen("login");
  };

  const updateAssistant = (assistantId, updater) => {
    setMessages((prev) => prev.map((msg) => (msg.id === assistantId ? { ...msg, ...updater(msg) } : msg)));
  };

  const sendMessage = (textOverride) => {
    if (loading) return;
    const text = (textOverride ?? input).trim();
    if (!text) return;

    const token = window.localStorage.getItem(TOKEN_KEY);
    if (!token) {
      handleLogout();
      return;
    }

    setError("");
    setInput("");
    setLastAttempt(text);

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      model: selectedModel,
      createdAt: Date.now(),
    };

    const assistantId = crypto.randomUUID();
    const assistantMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      model: selectedModel,
      messageId: null,
      streaming: true,
      feedback: null,
      createdAt: Date.now(),
    };

    const nextMessages = [...messages, userMessage].map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setLoading(true);

    streamRef.current?.close();
    const streamUrl = new URL(`${API_BASE}/api/v1/chat/stream`, window.location.href);
    streamUrl.searchParams.set("model", selectedModel);
    streamUrl.searchParams.set("messages", JSON.stringify(nextMessages));
    streamUrl.searchParams.set("user_id", "web-user");
    streamUrl.searchParams.set("session_id", sessionId);
    streamUrl.searchParams.set("token", token);

    const source = new EventSource(streamUrl.toString());
    streamRef.current = source;

    source.addEventListener("meta", (event) => {
      try {
        const data = JSON.parse(event.data);
        updateAssistant(assistantId, () => ({
          messageId: data.message_id || null,
          promptVersion: data.prompt_version || "v1",
        }));
      } catch {
        // no-op
      }
    });

    source.addEventListener("token", (event) => {
      try {
        const data = JSON.parse(event.data);
        const token = data.token || "";
        updateAssistant(assistantId, (msg) => ({ content: `${msg.content}${token}` }));
      } catch {
        // no-op
      }
    });

    source.addEventListener("done", (event) => {
      try {
        const data = JSON.parse(event.data);
        updateAssistant(assistantId, (msg) => ({
          streaming: false,
          messageId: data.message_id || msg.messageId,
        }));
      } finally {
        setLoading(false);
        source.close();
      }
    });

    source.addEventListener("error", () => {
      updateAssistant(assistantId, (msg) => ({
        streaming: false,
        content: msg.content || "Unable to stream response. Please retry.",
      }));
      setError("Streaming failed. Please try again.");
      setLoading(false);
      source.close();
    });
  };

  const updateFeedback = (assistantId, rating) => {
    setMessages((prev) => prev.map((msg) => (msg.id === assistantId ? { ...msg, feedback: rating } : msg)));
  };

  const clearChat = () => {
    setMessages([]);
    setError("");
    setLastAttempt(null);
  };

  if (screen === "login") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-light dark:bg-app">
        <div className="w-full max-w-md rounded-2xl border border-slate-300/80 bg-white/90 p-8 shadow-2xl dark:border-slate-700/70 dark:bg-slate-900/90">
          <h1 className="mb-1 text-center font-display text-2xl tracking-tight text-cyan-600 dark:text-cyan-300">
            CSS Prep AI
          </h1>
          <p className="mb-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Sign in to your account
          </p>

          <div className="flex flex-col gap-3">
            <input
              type="email"
              placeholder="Email address"
              value={authEmail}
              onChange={(e) => setAuthEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-cyan-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            <input
              type="password"
              placeholder="Password"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-cyan-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            {authError && (
              <p className="text-sm text-rose-500">{authError}</p>
            )}
            <button
              onClick={handleLogin}
              disabled={authLoading}
              className="w-full rounded-xl bg-cyan-600 px-4 py-2 font-medium text-white hover:bg-cyan-700 disabled:opacity-50"
            >
              {authLoading ? "Signing in…" : "Sign In"}
            </button>
          </div>

          <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">
            Don&apos;t have an account?{" "}
            <button
              onClick={() => { setAuthError(""); setScreen("register"); }}
              className="text-cyan-600 hover:underline dark:text-cyan-400"
            >
              Register
            </button>
          </p>
        </div>
      </div>
    );
  }

  if (screen === "register") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-light dark:bg-app">
        <div className="w-full max-w-md rounded-2xl border border-slate-300/80 bg-white/90 p-8 shadow-2xl dark:border-slate-700/70 dark:bg-slate-900/90">
          <h1 className="mb-1 text-center font-display text-2xl tracking-tight text-cyan-600 dark:text-cyan-300">
            CSS Prep AI
          </h1>
          <p className="mb-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Create a new account
          </p>

          <div className="flex flex-col gap-3">
            <input
              type="email"
              placeholder="Email address"
              value={authEmail}
              onChange={(e) => setAuthEmail(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-cyan-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            <input
              type="password"
              placeholder="Password (min 8 characters)"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-cyan-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            <input
              type="password"
              placeholder="Confirm password"
              value={authConfirmPassword}
              onChange={(e) => setAuthConfirmPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRegister()}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-cyan-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            {authError && (
              <p className="text-sm text-rose-500">{authError}</p>
            )}
            <button
              onClick={handleRegister}
              disabled={authLoading}
              className="w-full rounded-xl bg-cyan-600 px-4 py-2 font-medium text-white hover:bg-cyan-700 disabled:opacity-50"
            >
              {authLoading ? "Creating account…" : "Create Account"}
            </button>
          </div>

          <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">
            Already have an account?{" "}
            <button
              onClick={() => { setAuthError(""); setScreen("login"); }}
              className="text-cyan-600 hover:underline dark:text-cyan-400"
            >
              Sign In
            </button>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-app-light text-slate-900 dark:bg-app dark:text-slate-100">
      <div className="absolute -left-24 top-8 h-72 w-72 rounded-full bg-cyan-500/20 blur-3xl" />
      <div className="absolute -right-24 bottom-4 h-72 w-72 rounded-full bg-fuchsia-500/20 blur-3xl" />

      <main className="relative mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-4 px-4 py-6 md:px-8">
        <header className="rounded-2xl border border-slate-300/80 bg-white/70 p-4 shadow-2xl dark:border-slate-700/70 dark:bg-slate-900/70">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="font-display text-2xl tracking-tight text-cyan-300 md:text-3xl">CSS Prep AI</h1>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {loggedInEmail ? `Signed in as ${loggedInEmail}` : "Multi-LLM prep assistant for Pakistan CSS exam."}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <ModelSelector value={selectedModel} onChange={setSelectedModel} />
              <button
                onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {theme === "dark" ? "Light" : "Dark"}
              </button>
              <button
                onClick={clearChat}
                className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300 hover:bg-rose-500/20"
              >
                Clear
              </button>
              <button
                onClick={handleLogout}
                className="rounded-xl border border-slate-500/40 bg-slate-500/10 px-3 py-2 text-sm text-slate-300 hover:bg-slate-500/20"
              >
                Logout
              </button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {TOPICS.map((topic) => (
              <button
                key={topic}
                onClick={() => setInput(buildStarter(topic))}
                className="rounded-full border border-slate-300 bg-white/90 px-3 py-1 text-xs text-slate-700 hover:border-cyan-500 hover:text-cyan-700 dark:border-slate-600 dark:bg-slate-800/80 dark:text-slate-300 dark:hover:border-cyan-400 dark:hover:text-cyan-200"
              >
                {topic}
              </button>
            ))}
          </div>
        </header>

        <ChatWindow messages={messages} onFeedback={updateFeedback} />

        {error && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
            <div>{error}</div>
            {lastAttempt && (
              <button
                onClick={() => sendMessage(lastAttempt)}
                className="mt-2 rounded-lg border border-rose-400/50 px-3 py-1 text-xs hover:bg-rose-500/20"
              >
                Retry last message
              </button>
            )}
          </div>
        )}

        <MessageInput value={input} onChange={setInput} onSend={() => sendMessage()} disabled={loading} />
      </main>
    </div>
  );
}
