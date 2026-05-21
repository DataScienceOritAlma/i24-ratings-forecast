"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { ask, type AskResponse } from "@/lib/api";
import NavBar from "@/components/NavBar";

interface Message {
  role: "user" | "assistant";
  content: string;
  data?: AskResponse;
  timestamp: number;
}

const SUGGESTIONS = [
  { icon: "📅", text: "מה הצפי לקבינט שישי ביום שישי הבא?" },
  { icon: "🌅", text: "כמה רייטינג יהיה לחדר החדשות מחר?" },
  { icon: "📺", text: "מה התחזית לתוכנית 7 שרון גל בעוד שבוע?" },
  { icon: "⚡", text: "מה הצפי למהדורה המרכזית באירוע מיוחד?" },
];

export default function ChatPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) { router.replace("/"); return; }
      setEmail(data.session.user.email ?? null);
    });
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    const now = Date.now();
    setMessages((m) => [...m, { role: "user", content: question, timestamp: now }]);
    setInput("");
    setLoading(true);
    try {
      const r = await ask({ question });
      setMessages((m) => [...m, {
        role: "assistant",
        content: r.answer,
        data: r,
        timestamp: Date.now(),
      }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setMessages((m) => [...m, {
        role: "assistant",
        content: `❌ שגיאה: ${msg}\n\nודאי שה-Backend רץ ב-localhost:8000`,
        timestamp: Date.now(),
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }

  if (!email) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
          <p className="text-muted mt-3">טוען...</p>
        </div>
      </div>
    );
  }

  const showWelcome = messages.length === 0;

  return (
    <main className="min-h-screen flex flex-col bg-slate-50">
      <NavBar email={email} title="שאל את האפליקציה" />

      <div className="flex-1 max-w-3xl w-full mx-auto px-4 py-6 flex flex-col">
        {/* Welcome screen */}
        {showWelcome && (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-4 pb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-dark to-brand-primary text-white text-4xl shadow-lg mb-5">
              💬
            </div>
            <h1 className="text-3xl font-black text-brand-dark mb-2">
              שאל בעברית טבעית
            </h1>
            <p className="text-muted max-w-md mx-auto mb-8 leading-relaxed">
              שאלי על תוכנית, תאריך, ושעה — ואקבלי תחזית רייטינג עם רווח-ביטחון של 80%.
              <br />
              <span className="text-sm opacity-80">בלי טפסים. בלי לחיצות. רק שאלה.</span>
            </p>
            <div className="grid sm:grid-cols-2 gap-3 w-full max-w-2xl">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  onClick={() => send(s.text)}
                  className="group text-right bg-white hover:bg-brand-primary/5 border border-slate-200 hover:border-brand-primary rounded-xl p-4 transition shadow-sm hover:shadow-card"
                >
                  <div className="flex items-start gap-3">
                    <div className="text-2xl flex-shrink-0">{s.icon}</div>
                    <div>
                      <div className="text-sm text-ink leading-relaxed">{s.text}</div>
                      <div className="text-xs text-brand-primary mt-1 opacity-0 group-hover:opacity-100 transition">
                        לחצי כדי לשאול ←
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {!showWelcome && (
          <div className="flex-1 space-y-4 overflow-y-auto mb-4 pb-4">
            {messages.map((m, i) => (
              <MessageBubble key={i} m={m} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}

        {/* Input bar */}
        <form
          onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="bg-white rounded-2xl shadow-card p-2 flex gap-2 items-center sticky bottom-4 border border-slate-200"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="שאלי בעברית — לדוגמה: 'מה הצפי לקבינט שישי בשישי הבא?'"
            className="flex-1 px-4 py-2.5 rounded-xl border-0 focus:outline-none bg-transparent text-base"
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-l from-brand-primary to-brand-dark text-white font-bold hover:shadow-md hover:shadow-brand-primary/30 transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            ) : (
              <>שלחי <span className="text-lg leading-none">←</span></>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-muted mt-3">
          🎯 דיוק המודל: MAE 0.263 · 87% מהתחזיות בטווח ±0.5 מהאמת
        </p>
      </div>
    </main>
  );
}

function MessageBubble({ m }: { m: Message }) {
  const isUser = m.role === "user";
  const time = new Date(m.timestamp).toLocaleTimeString("he-IL", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={`flex ${isUser ? "justify-start" : "justify-end"} items-end gap-2`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-dark to-brand-primary text-white flex items-center justify-center text-sm flex-shrink-0">
          📺
        </div>
      )}
      <div className={`max-w-[85%] ${isUser ? "" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-brand-primary text-white rounded-bl-sm"
              : "bg-white shadow-card rounded-br-sm"
          }`}
        >
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {m.content}
          </div>

          {m.data?.prediction && (
            <div className="mt-3 pt-3 border-t border-slate-200 space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <PredStat
                  n={m.data.prediction.predicted_rating.toFixed(2)}
                  label="רייטינג"
                  primary
                />
                <PredStat
                  n={m.data.prediction.estimated_households.toLocaleString("he-IL")}
                  label="בתי-אב"
                />
                <PredStat
                  n={m.data.prediction.estimated_viewers.toLocaleString("he-IL")}
                  label="צופים"
                />
              </div>
              <div className="text-xs text-muted text-center pt-1">
                טווח 80%:{" "}
                <span className="font-bold tabular-nums text-ink">
                  {m.data.prediction.prediction_low.toFixed(2)}
                </span>
                {" — "}
                <span className="font-bold tabular-nums text-ink">
                  {m.data.prediction.prediction_high.toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {m.data && m.data.confidence !== "high" && (
            <div className="mt-2 text-[10px] text-muted bg-slate-50 rounded px-2 py-1">
              ביטחון בפענוח: {m.data.confidence === "medium" ? "בינוני" : "נמוך"}
              {m.data.extracted.program_name && ` · ${m.data.extracted.program_name}`}
              {" · "}
              {m.data.extracted.target_date}
            </div>
          )}
        </div>
        <div className={`text-[10px] text-muted mt-1 ${isUser ? "text-right pr-2" : "text-left pl-2"}`}>
          {time}
        </div>
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center text-sm flex-shrink-0">
          👤
        </div>
      )}
    </div>
  );
}

function PredStat({ n, label, primary }: { n: string; label: string; primary?: boolean }) {
  return (
    <div className={`rounded-lg p-2 text-center ${primary ? "bg-brand-primary/10" : "bg-slate-50"}`}>
      <div className={`font-black tabular-nums ${primary ? "text-brand-primary text-lg" : "text-ink text-base"}`}>
        {n}
      </div>
      <div className="text-[10px] text-muted mt-0.5">{label}</div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-end items-end gap-2">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-dark to-brand-primary text-white flex items-center justify-center text-sm flex-shrink-0">
        📺
      </div>
      <div className="bg-white shadow-card rounded-2xl rounded-br-sm px-4 py-3 flex items-center gap-1">
        <span className="w-2 h-2 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-2 h-2 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-2 h-2 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}
