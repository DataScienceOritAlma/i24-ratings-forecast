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
}

const SUGGESTIONS = [
  "מה הצפי לקבינט שישי ביום שישי הבא?",
  "כמה רייטינג יהיה לחדר החדשות מחר?",
  "מה התחזית לתוכנית 7 שרון גל בעוד שבוע?",
  "מה הצפי למהדורה המרכזית באירוע מיוחד?",
];

export default function ChatPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "שלום! אני אסיסטנט החיזוי של i24. שאלי אותי בעברית טבעית על תוכנית, ואחזיר לך תחזית רייטינג.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) { router.replace("/"); return; }
      setEmail(data.session.user.email ?? null);
    });
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const r = await ask({ question });
      setMessages((m) => [...m, { role: "assistant", content: r.answer, data: r }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setMessages((m) => [...m, {
        role: "assistant",
        content: `❌ שגיאה: ${msg}\n\nודאי שה-Backend רץ ב-localhost:8000`,
      }]);
    } finally {
      setLoading(false);
    }
  }

  if (!email) return <div className="p-8 text-center text-muted">טוען...</div>;

  return (
    <main className="min-h-screen flex flex-col">
      <NavBar email={email} title="שאל את האפליקציה" />

      <div className="flex-1 max-w-3xl w-full mx-auto px-4 py-6 flex flex-col">
        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto mb-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  m.role === "user"
                    ? "bg-brand-primary text-white"
                    : "bg-white shadow-card"
                }`}
              >
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {m.content}
                </div>
                {m.data?.prediction && (
                  <div className="mt-3 pt-3 border-t border-slate-200 grid grid-cols-3 gap-2 text-xs">
                    <Stat n={m.data.prediction.predicted_rating.toFixed(2)} label="רייטינג" />
                    <Stat n={`${m.data.prediction.estimated_households.toLocaleString("he-IL")}`} label="בתי-אב" />
                    <Stat n={`${m.data.prediction.estimated_viewers.toLocaleString("he-IL")}`} label="צופים" />
                  </div>
                )}
                {m.data && m.data.confidence !== "high" && (
                  <div className="mt-2 text-[10px] text-muted">
                    רמת ביטחון בפענוח: {m.data.confidence === "medium" ? "בינונית" : "נמוכה"} ·
                    זוהה: {m.data.extracted.program_name ?? "—"} · {m.data.extracted.target_date}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-end">
              <div className="bg-white shadow-card rounded-2xl px-4 py-3 text-sm text-muted">
                חושב...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {messages.length === 1 && (
          <div className="mb-4 flex flex-wrap gap-2 justify-end">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs px-3 py-1.5 bg-white rounded-full shadow-sm hover:shadow-card transition border border-slate-200"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="bg-white rounded-2xl shadow-card p-3 flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="שאלי בעברית — לדוגמה: 'מה הצפי לקבינט שישי בשישי הבא?'"
            className="flex-1 px-3 py-2 rounded-lg border-0 focus:outline-none"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-2 rounded-lg bg-brand-primary text-white font-bold hover:bg-brand-dark transition disabled:opacity-50"
          >
            שלחי ←
          </button>
        </form>
      </div>
    </main>
  );
}

function Stat({ n, label }: { n: string; label: string }) {
  return (
    <div className="bg-slate-50 rounded-lg p-2 text-center">
      <div className="font-black text-brand-primary text-base tabular-nums">{n}</div>
      <div className="text-[10px] text-muted">{label}</div>
    </div>
  );
}
