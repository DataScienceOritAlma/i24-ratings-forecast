"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { predict, type PredictResponse } from "@/lib/api";
import NavBar from "@/components/NavBar";

interface RecentPrediction {
  id: string;
  program_name: string;
  target_date: string;
  predicted_rating: number;
  created_at: string;
}

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
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [weekCount, setWeekCount] = useState<number | null>(null);
  const [recent, setRecent] = useState<RecentPrediction[]>([]);
  const [programAvg, setProgramAvg] = useState<number | null>(null);

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

      const { data: progs } = await supabase
        .from("programs")
        .select("name")
        .order("n_broadcasts", { ascending: false })
        .limit(200);
      if (progs) setPrograms(progs.map((p) => p.name as string));

      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const [{ count: total }, { count: week }, { data: latest }] = await Promise.all([
        supabase.from("predictions").select("*", { count: "exact", head: true }),
        supabase.from("predictions").select("*", { count: "exact", head: true }).gte("created_at", sevenDaysAgo),
        supabase.from("predictions")
          .select("id, program_name, target_date, predicted_rating, created_at")
          .order("created_at", { ascending: false })
          .limit(5),
      ]);
      setTotalCount(total ?? 0);
      setWeekCount(week ?? 0);
      setRecent((latest ?? []) as unknown as RecentPrediction[]);
    });
  }, [router]);

  // Lookup historical average for selected program (silently — for context badge)
  useEffect(() => {
    if (!programName) { setProgramAvg(null); return; }
    let cancelled = false;
    supabase
      .from("broadcasts")
      .select("rating")
      .eq("program_name", programName)
      .not("rating", "is", null)
      .limit(500)
      .then(({ data }) => {
        if (cancelled) return;
        if (!data || data.length === 0) { setProgramAvg(null); return; }
        const ratings = data.map((r) => Number(r.rating)).filter((n) => !isNaN(n));
        if (ratings.length === 0) { setProgramAvg(null); return; }
        const avg = ratings.reduce((a, b) => a + b, 0) / ratings.length;
        setProgramAvg(avg);
      });
    return () => { cancelled = true; };
  }, [programName]);

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

          // Refresh recents
          const { data: latest } = await supabase
            .from("predictions")
            .select("id, program_name, target_date, predicted_rating, created_at")
            .order("created_at", { ascending: false })
            .limit(5);
          setRecent((latest ?? []) as unknown as RecentPrediction[]);
          setTotalCount((prev) => (prev ?? 0) + 1);
          setWeekCount((prev) => (prev ?? 0) + 1);
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

  // Helpers for result card visualization
  const ratingScale = 5; // i24 ratings typically 0-3, scale to 5 for safe vis
  const lowPct = result ? Math.max(0, Math.min(100, (result.prediction_low / ratingScale) * 100)) : 0;
  const highPct = result ? Math.max(0, Math.min(100, (result.prediction_high / ratingScale) * 100)) : 0;
  const midPct = result ? Math.max(0, Math.min(100, (result.predicted_rating / ratingScale) * 100)) : 0;

  const vsAvg = result && programAvg != null
    ? result.predicted_rating - programAvg
    : null;

  return (
    <main className="min-h-screen bg-slate-50">
      <NavBar email={email} title="לוח חיזוי תחזיות" />

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* KPI strip */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard
            icon="📊"
            value={totalCount === null ? "—" : totalCount.toLocaleString("he-IL")}
            label="סך תחזיות"
          />
          <KpiCard
            icon="📅"
            value={weekCount === null ? "—" : weekCount.toLocaleString("he-IL")}
            label="השבוע"
            accent
          />
          <KpiCard
            icon="🎯"
            value="0.263"
            label="MAE · דיוק המודל"
          />
          <KpiCard
            icon="✅"
            value="87%"
            label="בטווח ±0.5"
          />
        </section>

        {/* Main: form + result */}
        <div className="grid md:grid-cols-5 gap-6">
          {/* Form (3/5) */}
          <section className="md:col-span-3 bg-white rounded-2xl shadow-card overflow-hidden">
            <div className="bg-gradient-to-l from-brand-primary/5 to-transparent px-6 py-4 border-b border-slate-100">
              <h2 className="text-lg font-black text-brand-dark flex items-center gap-2">
                <span className="text-2xl">🎯</span>
                חיזוי חדש
              </h2>
              <p className="text-xs text-muted mt-0.5">מלאי את הפרטים ולחצי &quot;חשב&quot; — תוצאה תוך שנייה</p>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-bold mb-1 text-ink">
                  שם תוכנית
                  {programAvg != null && (
                    <span className="text-xs text-muted font-normal mr-2">
                      · ממוצע היסטורי: <strong className="text-brand-primary tabular-nums">{programAvg.toFixed(2)}</strong>
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  required
                  list="programs-list"
                  value={programName}
                  onChange={(e) => setProgramName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/10 focus:outline-none transition"
                  placeholder="התחילי להקליד..."
                />
                <datalist id="programs-list">
                  {programs.map((p) => (
                    <option key={p} value={p} />
                  ))}
                </datalist>
                <p className="text-xs text-muted mt-1">
                  {programs.length > 0
                    ? `${programs.length} תוכניות בקטלוג — הקלידי לקבלת השלמה`
                    : "טוען קטלוג..."}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-bold mb-1 text-ink">תאריך</label>
                  <input
                    type="date"
                    required
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/10 focus:outline-none transition"
                  />
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    {[
                      { label: "היום", days: 0 },
                      { label: "מחר", days: 1 },
                      { label: "שבוע", days: 7 },
                      { label: "חודש", days: 30 },
                    ].map((s) => (
                      <button
                        key={s.label}
                        type="button"
                        onClick={() => {
                          const d = new Date();
                          d.setDate(d.getDate() + s.days);
                          setTargetDate(d.toISOString().slice(0, 10));
                        }}
                        className="text-xs px-2 py-0.5 rounded-full bg-slate-100 hover:bg-brand-primary hover:text-white transition text-muted"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1 text-ink">סטטוס</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/10 focus:outline-none transition bg-white"
                  >
                    <option>שידור חי</option>
                    <option>שידור חוזר</option>
                    <option>לקט</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-bold mb-1 text-ink">שעת התחלה</label>
                  <input
                    type="time"
                    required
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/10 focus:outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1 text-ink">שעת סיום</label>
                  <input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/10 focus:outline-none transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold mb-2 text-ink">תרחיש</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setScenario("routine")}
                    className={`py-3 rounded-xl font-bold transition border-2 ${
                      scenario === "routine"
                        ? "bg-brand-primary text-white border-brand-primary shadow-md"
                        : "bg-slate-50 text-muted border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="text-lg leading-none">📅</div>
                    <div className="text-sm mt-1">שגרה</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setScenario("special_event")}
                    className={`py-3 rounded-xl font-bold transition border-2 ${
                      scenario === "special_event"
                        ? "bg-brand-accent text-white border-brand-accent shadow-md"
                        : "bg-slate-50 text-muted border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="text-lg leading-none">🚨</div>
                    <div className="text-sm mt-1">אירוע ביטחוני</div>
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 rounded-xl bg-gradient-to-l from-brand-primary to-brand-dark text-white font-bold text-lg hover:shadow-lg hover:shadow-brand-primary/30 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    מחשב...
                  </span>
                ) : (
                  "🚀 חשב תחזית"
                )}
              </button>
            </form>
          </section>

          {/* Result (2/5) */}
          <section className="md:col-span-2 space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-5 text-sm text-red-700">
                <div className="font-bold mb-1">⚠️ שגיאה</div>
                <div>{error}</div>
                <div className="mt-2 text-xs text-red-600">
                  ודאי שה-Backend רץ ב-localhost:8000
                </div>
              </div>
            )}

            {result && (
              <div className="bg-gradient-to-br from-brand-dark via-brand-primary to-brand-light text-white rounded-2xl shadow-card p-6 relative overflow-hidden">
                <div className="absolute inset-0 opacity-20" style={{
                  background: "radial-gradient(circle at 80% 0%, rgba(255,107,53,0.5) 0%, transparent 50%)"
                }} />
                <div className="relative">
                  <div className="flex items-start justify-between mb-1">
                    <div className="text-xs opacity-80">תחזית רייטינג מותאם</div>
                    {vsAvg != null && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                          vsAvg >= 0 ? "bg-green-400/20 text-green-100" : "bg-red-400/20 text-red-100"
                        }`}
                      >
                        {vsAvg >= 0 ? "↑" : "↓"} {Math.abs(vsAvg).toFixed(2)} מהממוצע
                      </span>
                    )}
                  </div>
                  <div className="text-6xl font-black tabular-nums leading-none">
                    {result.predicted_rating.toFixed(2)}
                  </div>

                  {result.predicted_rating_raw != null && (
                    <div className="mt-2 text-xs opacity-80 flex items-center gap-1.5">
                      <span>גולמי משוער:</span>
                      <span className="font-bold tabular-nums">{result.predicted_rating_raw.toFixed(2)}</span>
                      {result.reception_pct_used != null && (
                        <span className="opacity-70">
                          · קליטת פאנל {Math.round(result.reception_pct_used * 100)}%
                        </span>
                      )}
                    </div>
                  )}

                  {/* Confidence visualization */}
                  <div className="mt-5">
                    <div className="flex items-center justify-between text-xs opacity-80 mb-1.5">
                      <span>טווח 80% ביטחון</span>
                      <span className="tabular-nums">
                        {result.prediction_low.toFixed(2)} — {result.prediction_high.toFixed(2)}
                      </span>
                    </div>
                    <div className="relative h-3 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="absolute h-full bg-gradient-to-l from-brand-accent/40 to-white/30 rounded-full"
                        style={{ insetInlineStart: `${lowPct}%`, width: `${Math.max(0, highPct - lowPct)}%` }}
                      />
                      <div
                        className="absolute top-1/2 -translate-y-1/2 w-1 h-5 bg-white shadow-lg rounded-full"
                        style={{ insetInlineStart: `${midPct}%`, transform: "translate(50%, -50%)" }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] opacity-60 mt-1 tabular-nums">
                      <span>0</span>
                      <span>{ratingScale}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mt-5">
                    <div className="bg-white/10 backdrop-blur rounded-xl p-3 text-center">
                      <div className="text-2xl font-black tabular-nums">
                        {result.estimated_households.toLocaleString("he-IL")}
                      </div>
                      <div className="text-xs opacity-80">בתי-אב</div>
                    </div>
                    <div className="bg-white/10 backdrop-blur rounded-xl p-3 text-center">
                      <div className="text-2xl font-black tabular-nums">
                        {result.estimated_viewers.toLocaleString("he-IL")}
                      </div>
                      <div className="text-xs opacity-80">צופים</div>
                    </div>
                  </div>

                  <div className="mt-4 text-xs opacity-70 border-t border-white/20 pt-3 flex justify-between">
                    <span>{result.model}</span>
                    <span>{saving ? "שומר..." : "נשמר ✓"}</span>
                  </div>
                </div>
              </div>
            )}

            {!error && !result && (
              <div className="bg-white rounded-2xl shadow-card p-6 text-center">
                <div className="text-5xl mb-3">📊</div>
                <h3 className="font-black text-brand-dark mb-1">מוכן לחיזוי</h3>
                <p className="text-sm text-muted">
                  מלאי את הטופס ולחצי &quot;חשב תחזית&quot; כדי לראות את התוצאה.
                </p>
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <Link
                    href="/chat"
                    className="text-sm text-brand-primary hover:text-brand-dark font-bold inline-flex items-center gap-1"
                  >
                    💬 או נסי לשאול בעברית טבעית ←
                  </Link>
                </div>
              </div>
            )}

            {/* Tip card */}
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-sm">
              <div className="font-bold text-amber-900 mb-1 flex items-center gap-1.5">
                <span>💡</span> טיפ
              </div>
              <p className="text-amber-800 leading-relaxed">
                לתכנון תרחישים — קבעי &quot;אירוע ביטחוני&quot; כדי לראות את הקפיצה הצפויה ברייטינג בזמן הסלמה.
              </p>
            </div>
          </section>
        </div>

        {/* Recent predictions strip */}
        {recent.length > 0 && (
          <section className="bg-white rounded-2xl shadow-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-black text-brand-dark flex items-center gap-2">
                <span>📚</span> תחזיות אחרונות
              </h3>
              <Link
                href="/history"
                className="text-sm text-brand-primary hover:text-brand-dark font-bold"
              >
                כל ההיסטוריה ←
              </Link>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {recent.map((p) => (
                <div
                  key={p.id}
                  className="bg-slate-50 hover:bg-slate-100 rounded-xl p-3 transition cursor-default"
                >
                  <div className="text-xs text-muted mb-1 truncate" title={p.program_name}>
                    {p.program_name}
                  </div>
                  <div className="text-2xl font-black text-brand-dark tabular-nums">
                    {Number(p.predicted_rating).toFixed(2)}
                  </div>
                  <div className="text-xs text-muted mt-1">
                    {new Date(p.target_date).toLocaleDateString("he-IL", {
                      day: "numeric",
                      month: "short",
                    })}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function KpiCard({
  icon, value, label, accent,
}: { icon: string; value: string; label: string; accent?: boolean }) {
  return (
    <div
      className={`rounded-2xl p-4 shadow-card transition hover:shadow-lg ${
        accent
          ? "bg-gradient-to-br from-brand-accent to-orange-500 text-white"
          : "bg-white"
      }`}
    >
      <div className="flex items-start justify-between">
        <div>
          <div
            className={`text-2xl font-black tabular-nums ${
              accent ? "" : "text-brand-dark"
            }`}
          >
            {value}
          </div>
          <div className={`text-xs mt-0.5 ${accent ? "text-white/90" : "text-muted"}`}>
            {label}
          </div>
        </div>
        <div className="text-2xl opacity-80">{icon}</div>
      </div>
    </div>
  );
}
