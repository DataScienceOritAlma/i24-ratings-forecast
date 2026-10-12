"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { ask, type AskResponse } from "@/lib/api";
import NavBar from "@/components/NavBar";
import Icon from "@/components/Icon";

interface Message {
  role: "user" | "assistant";
  content: string;
  data?: AskResponse;
  isError?: boolean;
  timestamp: number;
}

const SUGGESTIONS = [
  "מה הצפי לקבינט שישי ביום שישי הבא?",
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
        content: `לא הצלחתי לקבל תשובה מהשרת (${msg}). אם לא נעשה שימוש באפליקציה ברבע השעה האחרונה, השרת מתעורר תוך חצי דקה. נסי שוב.`,
        isError: true,
        timestamp: Date.now(),
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }

  if (!email) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-canvas" role="status">
        <div className="text-center">
          <div className="inline-block w-10 h-10 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
          <p className="text-muted mt-3">טוען...</p>
        </div>
      </div>
    );
  }

  const showWelcome = messages.length === 0;

  return (
    <main className="min-h-dvh flex flex-col bg-canvas">
      <NavBar email={email} title="שאלה חופשית" />

      <div className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col">
        {showWelcome && (
          <div className="flex-1 flex flex-col justify-center pb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-50 text-brand-primary">
              <Icon name="message" size={24} />
            </div>
            <h2 className="text-2xl font-bold text-brand-dark mt-4">שאלי בעברית רגילה</h2>
            <p className="text-muted max-w-xl mt-2 leading-relaxed">
              כתבי תאריך, שעה ותרחיש, ותקבלי תחזית רייטינג עם טווח ביטחון. הגרסה הנוכחית עונה על ״קבינט שישי״ בלבד.
            </p>
            <p className="text-sm font-medium text-ink mt-8 mb-2">אפשר להתחיל מכאן:</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="card text-right p-4 text-sm text-ink leading-relaxed flex items-center justify-between gap-3 hover:border-brand-primary hover:shadow-card-hover transition-colors duration-150 cursor-pointer"
                >
                  <span>{s}</span>
                  <Icon name="arrowLeft" size={16} className="text-brand-primary" />
                </button>
              ))}
            </div>
          </div>
        )}

        {!showWelcome && (
          <div className="flex-1 space-y-4 mb-4 pb-4" aria-live="polite">
            {messages.map((m, i) => (
              <MessageBubble key={i} m={m} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="card p-2 flex gap-2 items-center sticky bottom-4"
        >
          <label htmlFor="question" className="sr-only">השאלה שלך</label>
          <input
            id="question"
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="למשל: מה הצפי לקבינט שישי בשישי הבא?"
            className="flex-1 min-w-0 min-h-[44px] px-3 rounded-lg border-0 focus:outline-none bg-transparent text-base"
            disabled={loading}
            autoFocus
          />
          <button type="submit" disabled={loading || !input.trim()} className="btn-primary">
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                שליחה
                <Icon name="arrowLeft" size={18} />
              </>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-muted mt-3">
          כל תחזית היא הערכה סטטיסטית, ומוצגת עם טווח ביטחון של 80%.
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
    <div className={`flex ${isUser ? "justify-start" : "justify-end"}`}>
      <div className="max-w-[85%]">
        <div className={`text-[11px] text-muted mb-1 ${isUser ? "text-right" : "text-left"}`}>
          {isUser ? "את" : "התחזית"} · <span className="num">{time}</span>
        </div>
        <div
          className={`rounded-xl px-4 py-3 ${
            isUser
              ? "bg-brand-dark text-white"
              : m.isError
                ? "bg-red-50 border border-red-200 text-red-800"
                : "bg-white border border-line shadow-card"
          }`}
          role={m.isError ? "alert" : undefined}
        >
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</div>

          {m.data?.prediction && (
            <div className="mt-3 pt-3 border-t border-line">
              <dl className="grid grid-cols-3 gap-2">
                <PredStat n={m.data.prediction.predicted_rating.toFixed(2)} label="רייטינג" primary />
                <PredStat n={m.data.prediction.estimated_households.toLocaleString("he-IL")} label="בתי אב" />
                <PredStat n={m.data.prediction.estimated_viewers.toLocaleString("he-IL")} label="צופים" />
              </dl>
              <div className="text-xs text-muted text-center mt-2">
                טווח 80%:{" "}
                <span className="font-bold num text-ink" dir="ltr">
                  {m.data.prediction.prediction_low.toFixed(2)} – {m.data.prediction.prediction_high.toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {m.data && m.data.confidence !== "high" && (
            <div className="mt-2 text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5 flex items-start gap-1.5">
              <Icon name="info" size={14} className="mt-0.5" />
              <span>
                לא בטוח שהבנתי את השאלה במלואה (ביטחון {m.data.confidence === "medium" ? "בינוני" : "נמוך"}).
                חישבתי לפי: {m.data.extracted.program_name ? `${m.data.extracted.program_name}, ` : ""}
                <span className="num" dir="ltr">{m.data.extracted.target_date}</span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PredStat({ n, label, primary }: { n: string; label: string; primary?: boolean }) {
  return (
    <div className={`rounded-lg p-2 text-center border ${primary ? "bg-blue-50 border-blue-100" : "bg-canvas border-line"}`}>
      <dt className="text-[11px] text-muted">{label}</dt>
      <dd className={`font-bold num ${primary ? "text-brand-primary text-lg" : "text-ink text-base"}`}>{n}</dd>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-end" role="status" aria-label="מחשב תשובה">
      <div className="bg-white border border-line shadow-card rounded-xl px-4 py-3 flex items-center gap-1">
        <span className="w-2 h-2 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-2 h-2 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-2 h-2 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}
