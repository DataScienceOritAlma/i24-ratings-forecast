"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { predict, type PredictResponse } from "@/lib/api";
import NavBar from "@/components/NavBar";

export default function DashboardPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [programs, setPrograms] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) { router.replace("/"); return; }
      const user = data.session.user;
      setEmail(user.email ?? null);
      setUserId(user.id);

      const { data: prof } = await supabase
        .from("profiles")
        .select("organization_id")
        .eq("id", user.id)
        .maybeSingle();
      setOrgId(prof?.organization_id ?? null);

      // Load programs for autocomplete
      const { data: progs } = await supabase
        .from("programs")
        .select("name")
        .order("n_broadcasts", { ascending: false })
        .limit(200);
      if (progs) setPrograms(progs.map((p) => p.name as string));
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

      if (userId && orgId) {
        setSaving(true);
        try {
          const { data: prog } = await supabase
            .from("programs")
            .select("id")
            .eq("name", programName)
            .maybeSingle();

          await supabase.from("predictions").insert({
            organization_id: orgId,
            user_id: userId,
            program_id: prog?.id ?? null,
            program_name: programName,
            target_date: targetDate,
            target_start_time: startTime + ":00",
            target_end_time: endTime + ":00",
            scenario,
            predicted_rating: r.predicted_rating,
            prediction_low: r.prediction_low,
            prediction_high: r.prediction_high,
            estimated_households: r.estimated_households,
            estimated_viewers: r.estimated_viewers,
            model_version: r.model,
            uncertainty_source: r.uncertainty_source,
          });
        } catch (saveErr) {
          console.warn("Failed to save prediction history:", saveErr);
        } finally {
          setSaving(false);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  if (!email) return <div className="p-8 text-center text-muted">טוען...</div>;

  return (
    <main className="min-h-screen">
      <NavBar email={email} title="לוח חיזוי תחזיות" />

      <div className="max-w-5xl mx-auto px-6 py-8 grid md:grid-cols-2 gap-8">
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-xl font-black text-brand-dark mb-4">🎯 חיזוי חדש</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-bold mb-1">שם תוכנית</label>
              <input
                type="text"
                required
                list="programs-list"
                value={programName}
                onChange={(e) => setProgramName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-brand-primary focus:outline-none"
                placeholder="התחילי להקליד..."
              />
              <datalist id="programs-list">
                {programs.map((p) => (
                  <option key={p} value={p} />
                ))}
              </datalist>
              <p className="text-xs text-muted mt-1">
                {programs.length > 0
                  ? `${programs.length} תוכניות בקטלוג — הקלידי וקבלי השלמה אוטומטית`
                  : "טוען קטלוג..."}
              </p>
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

        <section>
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-sm text-red-700">
              <strong>שגיאה:</strong> {error}
              <div className="mt-2 text-xs text-red-600">
                ודאי שה-Backend רץ ב-localhost:8000
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
                טווח 80%:{" "}
                <span className="font-bold tabular-nums">{result.prediction_low.toFixed(2)}</span>
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

              <div className="mt-4 text-xs opacity-70 border-t border-white/20 pt-3 flex justify-between">
                <span>מודל: {result.model}</span>
                <span>{saving ? "שומר..." : "נשמר בהיסטוריה ✓"}</span>
              </div>
            </div>
          )}

          {!error && !result && (
            <div className="bg-white rounded-2xl shadow-card p-6 text-center text-muted">
              <div className="text-4xl mb-3">📊</div>
              <p>מלאי את הטופס ולחצי &quot;חשב תחזית&quot; כדי לראות את התוצאה.</p>
              <p className="text-xs mt-3">או נסי את הצ&apos;אט החכם — &quot;💬 שאל&quot; בתפריט למעלה.</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
