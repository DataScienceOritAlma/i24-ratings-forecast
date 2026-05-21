"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { predict, type PredictResponse } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // form
  const [programName, setProgramName] = useState("קבינט שישי");
  const [targetDate, setTargetDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 10);
  });
  const [startTime, setStartTime] = useState("19:50");
  const [endTime, setEndTime] = useState("22:00");
  const [scenario, setScenario] = useState<"routine" | "special_event">("routine");
  const [status, setStatus] = useState("שידור חי");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        router.replace("/");
        return;
      }
      setEmail(data.session.user.email ?? null);
    });
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const r = await predict({
        program_name: programName,
        target_date: targetDate,
        start_time: startTime + ":00",
        end_time: endTime + ":00",
        scenario,
        status,
      });
      setResult(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.replace("/");
  }

  if (!email) {
    return <div className="p-8 text-center text-muted">טוען...</div>;
  }

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="bg-gradient-to-br from-brand-dark to-brand-primary text-white py-6 shadow-lg">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between">
          <div>
            <div className="text-xs opacity-80">i24 Ratings Forecast</div>
            <h1 className="text-2xl font-black">לוח חיזוי תחזיות</h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="opacity-90" dir="ltr">{email}</span>
            <button
              onClick={handleSignOut}
              className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition"
            >
              יציאה
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8 grid md:grid-cols-2 gap-8">
        {/* Form */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-xl font-black text-brand-dark mb-4">🎯 חיזוי חדש</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-bold mb-1">שם תוכנית</label>
              <input
                type="text"
                required
                value={programName}
                onChange={(e) => setProgramName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-brand-primary focus:outline-none"
              />
              <p className="text-xs text-muted mt-1">לדוגמה: קבינט שישי · חדר החדשות איי 24</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-bold mb-1">תאריך</label>
                <input
                  type="date"
                  required
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200"
                />
              </div>
              <div>
                <label className="block text-sm font-bold mb-1">סטטוס</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200"
                >
                  <option>שידור חי</option>
                  <option>שידור חוזר</option>
                  <option>לקט</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-bold mb-1">שעת התחלה</label>
                <input
                  type="time"
                  required
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200"
                />
              </div>
              <div>
                <label className="block text-sm font-bold mb-1">שעת סיום</label>
                <input
                  type="time"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold mb-2">תרחיש</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setScenario("routine")}
                  className={`flex-1 py-2 rounded-lg font-bold transition ${
                    scenario === "routine"
                      ? "bg-brand-primary text-white"
                      : "bg-slate-100 text-muted"
                  }`}
                >
                  שגרה
                </button>
                <button
                  type="button"
                  onClick={() => setScenario("special_event")}
                  className={`flex-1 py-2 rounded-lg font-bold transition ${
                    scenario === "special_event"
                      ? "bg-brand-accent text-white"
                      : "bg-slate-100 text-muted"
                  }`}
                >
                  אירוע מיוחד
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-brand-primary text-white font-bold hover:bg-brand-dark transition disabled:opacity-50"
            >
              {loading ? "מחשב..." : "🚀 חשב תחזית"}
            </button>
          </form>
        </section>

        {/* Result */}
        <section>
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-sm text-red-700">
              <strong>שגיאה:</strong> {error}
              <div className="mt-2 text-xs text-red-600">
                ודאי שה-Backend רץ ב-localhost:8000 (cd backend && py -3 -m uvicorn main:app)
              </div>
            </div>
          )}

          {result && (
            <div className="bg-gradient-to-br from-brand-dark to-brand-primary text-white rounded-2xl shadow-card p-6">
              <div className="text-xs opacity-80 mb-1">תחזית רייטינג</div>
              <div className="text-6xl font-black mb-2 tabular-nums">
                {result.predicted_rating.toFixed(2)}
              </div>
              <div className="text-sm opacity-90 mb-4">
                טווח 80%: <span className="font-bold tabular-nums">{result.prediction_low.toFixed(2)}</span>
                {" — "}
                <span className="font-bold tabular-nums">{result.prediction_high.toFixed(2)}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 mt-6">
                <div className="bg-white/10 rounded-xl p-3 text-center">
                  <div className="text-2xl font-black tabular-nums">
                    {result.estimated_households.toLocaleString("he-IL")}
                  </div>
                  <div className="text-xs opacity-80">בתי-אב</div>
                </div>
                <div className="bg-white/10 rounded-xl p-3 text-center">
                  <div className="text-2xl font-black tabular-nums">
                    {result.estimated_viewers.toLocaleString("he-IL")}
                  </div>
                  <div className="text-xs opacity-80">צופים מוערכים</div>
                </div>
              </div>

              <div className="mt-4 text-xs opacity-70 border-t border-white/20 pt-3">
                מודל: {result.model} · מקור-אי-ודאות: {result.uncertainty_source}
              </div>
            </div>
          )}

          {!error && !result && (
            <div className="bg-white rounded-2xl shadow-card p-6 text-center text-muted">
              <div className="text-4xl mb-3">📊</div>
              <p>מלאי את הטופס ולחצי "חשב תחזית" כדי לראות את התוצאה.</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
