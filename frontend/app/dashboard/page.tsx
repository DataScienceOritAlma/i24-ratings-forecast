"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { predict, type PredictResponse } from "@/lib/api";
import NavBar from "@/components/NavBar";
import Icon, { type IconName } from "@/components/Icon";

type Scenario = "routine" | "special_event";

const DATE_SHORTCUTS = [
  { label: "היום", days: 0 },
  { label: "מחר", days: 1 },
  { label: "בעוד שבוע", days: 7 },
  { label: "בעוד חודש", days: 30 },
];

const SCENARIOS: { value: Scenario; label: string; hint: string; icon: IconName }[] = [
  { value: "routine", label: "שגרה", hint: "שבוע רגיל, בלי אירוע חריג", icon: "calendar" },
  { value: "special_event", label: "אירוע ביטחוני", hint: "הסלמה או אירוע מתפתח", icon: "alert" },
];

export default function DashboardPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [programAvg, setProgramAvg] = useState<number | null>(null);

  const [programName] = useState("קבינט שישי");
  const [targetDate, setTargetDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 10);
  });
  const [startTime, setStartTime] = useState("19:50");
  const [endTime, setEndTime] = useState("22:00");
  const [scenario, setScenario] = useState<Scenario>("routine");
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

  async function runPrediction() {
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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    runPrediction();
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

  const vsAvg = result && programAvg != null
    ? result.predicted_rating - programAvg
    : null;

  return (
    <main className="min-h-dvh bg-canvas">
      <NavBar email={email} title="לוח חיזוי תחזיות" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="grid lg:grid-cols-5 gap-6 items-start">

          {/* Form (3/5) */}
          <section className="lg:col-span-3 card" aria-labelledby="form-title">
            <div className="px-5 sm:px-6 py-4 border-b border-line">
              <h2 id="form-title" className="text-lg font-bold text-brand-dark">חיזוי חדש</h2>
              <p className="text-sm text-muted mt-0.5">ארבעה פרטים על השידור, והתחזית מוכנה תוך שנייה.</p>
            </div>

            <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-6">
              <div>
                <label htmlFor="program" className="label">תוכנית</label>
                <input id="program" type="text" readOnly value={programName} className="field" aria-describedby="program-help" />
                <p id="program-help" className="text-xs text-muted mt-1.5">
                  הגרסה הנוכחית חוזה את ״קבינט שישי״ בלבד.
                  {programAvg != null && (
                    <> ממוצע היסטורי: <strong className="text-ink num">{programAvg.toFixed(2)}</strong>.</>
                  )}
                </p>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="date" className="label">תאריך השידור</label>
                  <input
                    id="date"
                    type="date"
                    required
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="field"
                  />
                  <div className="flex gap-2 mt-2 flex-wrap">
                    {DATE_SHORTCUTS.map((s) => (
                      <button
                        key={s.label}
                        type="button"
                        onClick={() => {
                          const d = new Date();
                          d.setDate(d.getDate() + s.days);
                          setTargetDate(d.toISOString().slice(0, 10));
                        }}
                        className="text-xs min-h-[36px] px-3 rounded-full border border-line bg-white text-muted hover:border-brand-primary hover:text-brand-primary transition-colors duration-150 cursor-pointer"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label htmlFor="status" className="label">סוג השידור</label>
                  <select
                    id="status"
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="field"
                  >
                    <option>שידור חי</option>
                    <option>שידור חוזר</option>
                    <option>לקט</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="start" className="label">שעת התחלה</label>
                  <input
                    id="start"
                    type="time"
                    required
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label htmlFor="end" className="label">שעת סיום</label>
                  <input
                    id="end"
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="field"
                  />
                </div>
              </div>

              <fieldset>
                <legend className="label">תרחיש</legend>
                <div className="grid sm:grid-cols-2 gap-3">
                  {SCENARIOS.map((s) => {
                    const checked = scenario === s.value;
                    const tone = s.value === "special_event"
                      ? "peer-checked:border-brand-accent peer-checked:bg-orange-50 peer-checked:text-brand-accent"
                      : "peer-checked:border-brand-primary peer-checked:bg-blue-50 peer-checked:text-brand-primary";
                    return (
                      <label key={s.value} className="cursor-pointer">
                        <input
                          type="radio"
                          name="scenario"
                          value={s.value}
                          checked={checked}
                          onChange={() => setScenario(s.value)}
                          className="sr-only peer"
                        />
                        <span
                          className={`flex items-center gap-3 min-h-[60px] px-4 py-3 rounded-lg border-2 border-line bg-white text-muted transition-colors duration-150 hover:border-slate-300 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-primary/40 ${tone}`}
                        >
                          <Icon name={s.icon} size={22} />
                          <span>
                            <span className="block font-bold text-ink">{s.label}</span>
                            <span className="block text-xs text-muted">{s.hint}</span>
                          </span>
                          {checked && <Icon name="check" size={18} className="ms-auto" />}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>

              <button type="submit" disabled={loading} className="btn-primary w-full text-base">
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    מחשב...
                  </>
                ) : (
                  "חשב תחזית"
                )}
              </button>
            </form>
          </section>

          {/* Result (2/5) */}
          <section className="lg:col-span-2 space-y-4" aria-live="polite" aria-label="תוצאת החיזוי">
            {error && (
              <div className="card border-red-200 bg-red-50 p-5 text-sm text-red-800" role="alert">
                <div className="font-bold mb-1 flex items-center gap-2">
                  <Icon name="alert" size={18} />
                  החיזוי לא הצליח
                </div>
                <div className="break-words">{error}</div>
                {error.toLowerCase().includes("failed to fetch") && (
                  <p className="mt-3 text-xs leading-relaxed">
                    השרת נרדם אחרי 15 דקות בלי פעילות, והקריאה הראשונה אחרי הפסקה לוקחת 30 עד 60 שניות.
                    נסי שוב בעוד חצי דקה. הקריאות הבאות יהיו מיידיות.
                  </p>
                )}
                <button onClick={runPrediction} className="btn mt-3 min-h-[40px] px-4 text-sm bg-red-700 text-white hover:bg-red-800">
                  <Icon name="refresh" size={16} />
                  נסי שוב
                </button>
              </div>
            )}

            {loading && !result && (
              <div className="card p-6" aria-hidden="true">
                <div className="h-4 w-32 rounded bg-slate-200 animate-pulse" />
                <div className="h-14 w-40 rounded bg-slate-200 animate-pulse mt-3" />
                <div className="h-3 w-full rounded bg-slate-200 animate-pulse mt-8" />
                <div className="grid grid-cols-2 gap-3 mt-6">
                  <div className="h-16 rounded-lg bg-slate-100 animate-pulse" />
                  <div className="h-16 rounded-lg bg-slate-100 animate-pulse" />
                </div>
              </div>
            )}

            {result && (
              <article className="card overflow-hidden">
                <div className="p-5 sm:p-6">
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-sm font-medium text-muted">תחזית רייטינג מותאם</h2>
                    {vsAvg != null && (
                      <span
                        className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full font-bold whitespace-nowrap ${
                          vsAvg >= 0 ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"
                        }`}
                      >
                        <Icon name={vsAvg >= 0 ? "trendingUp" : "trendingDown"} size={14} />
                        <span className="num">{Math.abs(vsAvg).toFixed(2)}</span>
                        {vsAvg >= 0 ? "מעל הממוצע" : "מתחת לממוצע"}
                      </span>
                    )}
                  </div>

                  <div className="text-6xl font-bold text-brand-dark num leading-none mt-2">
                    {result.predicted_rating.toFixed(2)}
                  </div>

                  {result.predicted_rating_raw != null && (
                    <p className="mt-2 text-xs text-muted">
                      רייטינג גולמי משוער: <strong className="text-ink num">{result.predicted_rating_raw.toFixed(2)}</strong>
                      {result.reception_pct_used != null && (
                        <> · קליטת פאנל <span className="num">{Math.round(result.reception_pct_used * 100)}%</span></>
                      )}
                    </p>
                  )}

                  <RangeBar
                    low={result.prediction_low}
                    high={result.prediction_high}
                    point={result.predicted_rating}
                    avg={programAvg}
                  />

                  <dl className="grid grid-cols-2 gap-3 mt-6">
                    <div className="rounded-lg bg-canvas border border-line p-3">
                      <dt className="text-xs text-muted">בתי אב</dt>
                      <dd className="text-xl font-bold text-ink num mt-0.5">
                        {result.estimated_households.toLocaleString("he-IL")}
                      </dd>
                    </div>
                    <div className="rounded-lg bg-canvas border border-line p-3">
                      <dt className="text-xs text-muted">צופים</dt>
                      <dd className="text-xl font-bold text-ink num mt-0.5">
                        {result.estimated_viewers.toLocaleString("he-IL")}
                      </dd>
                    </div>
                  </dl>

                  <div className="space-y-3 mt-5 empty:hidden">
                    {scenario === "special_event" && String(result.metadata?.scenario_effective) === "routine" && (
                      <Callout tone="info" title="אין אירוע ביטחוני פעיל בתאריך הזה">
                        בחרת ״אירוע ביטחוני״, אבל אין אירוע פעיל ב-<span className="num" dir="ltr">{targetDate}</span>, ולכן התחזית זהה לשגרה.
                        כדי לראות תרחיש הסלמה, בחרי תאריך בתוך חלון אירוע ידוע (למשל <span className="num" dir="ltr">2026-03-13</span>).
                      </Callout>
                    )}
                    {result.reliability === "cold_start" && (
                      <Callout tone="warn" title="אי-ודאות גבוהה: תוכנית חדשה">
                        יש רק <span className="num">{result.n_historical_broadcasts ?? 0}</span> שידורים היסטוריים, והמודל עוד לא מכיר את התוכנית מספיק. הטווח רחב בכוונה.
                      </Callout>
                    )}
                    {result.reliability === "medium" && (
                      <Callout tone="warn" title="אמינות בינונית">
                        התחזית נשענת על <span className="num">{result.n_historical_broadcasts}</span> שידורים בלבד.
                      </Callout>
                    )}
                  </div>

                  {result.explanation && (
                    <div className="mt-5 pt-5 border-t border-line">
                      <h3 className="text-xs font-bold text-muted mb-1.5 flex items-center gap-1.5">
                        <Icon name="lightbulb" size={14} />
                        למה זו התחזית
                      </h3>
                      <p className="text-sm leading-relaxed text-ink">{result.explanation}</p>
                    </div>
                  )}
                </div>

                <footer className="px-5 sm:px-6 py-3 bg-canvas border-t border-line text-xs text-muted flex justify-between gap-3">
                  <span dir="ltr" className="truncate">{result.model}</span>
                  <span className="inline-flex items-center gap-1 whitespace-nowrap">
                    {saving ? "שומר..." : (<><Icon name="check" size={14} /> נשמר בהיסטוריה</>)}
                  </span>
                </footer>
              </article>
            )}

            {!error && !result && !loading && (
              <div className="card p-6 text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-50 text-brand-primary">
                  <Icon name="chart" size={24} />
                </div>
                <h2 className="font-bold text-brand-dark mt-3">התחזית תופיע כאן</h2>
                <p className="text-sm text-muted mt-1">
                  מלאי את הטופס ולחצי ״חשב תחזית״.
                </p>
                <Link href="/chat" className="btn-quiet mt-3 text-sm text-brand-primary">
                  או שאלי בעברית חופשית
                  <Icon name="arrowLeft" size={16} />
                </Link>
              </div>
            )}

            <Callout tone="tip" title="תכנון תרחישים">
              בחרי ״אירוע ביטחוני״ כדי לראות את הקפיצה הצפויה ברייטינג בזמן הסלמה, והשווי אותה לתחזית השגרה.
            </Callout>
          </section>
        </div>
      </div>
    </main>
  );
}

// 80% interval on a numeric scale. Numeric axes read left-to-right even in a
// Hebrew interface, so the bar is laid out LTR.
function RangeBar({ low, high, point, avg }: { low: number; high: number; point: number; avg: number | null }) {
  const max = Math.max(5, Math.ceil(Math.max(high, avg ?? 0) * 1.15));
  const pct = (v: number) => Math.max(0, Math.min(100, (v / max) * 100));

  return (
    <div className="mt-6">
      <div className="flex items-baseline justify-between text-xs mb-2">
        <span className="text-muted">טווח ביטחון של 80%</span>
        <span className="num font-bold text-ink" dir="ltr">
          {low.toFixed(2)} – {high.toFixed(2)}
        </span>
      </div>

      <div
        dir="ltr"
        className="relative h-8"
        role="img"
        aria-label={`תחזית ${point.toFixed(2)}, בטווח של ${low.toFixed(2)} עד ${high.toFixed(2)}${avg != null ? `, ממוצע היסטורי ${avg.toFixed(2)}` : ""}`}
      >
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 rounded-full bg-slate-200" />
        <div
          className="absolute top-1/2 -translate-y-1/2 h-2 rounded-full bg-brand-primary/35"
          style={{ left: `${pct(low)}%`, width: `${Math.max(0, pct(high) - pct(low))}%` }}
        />
        {avg != null && (
          <div
            className="absolute top-1 bottom-1 w-0 border-l-2 border-dashed border-slate-500"
            style={{ left: `${pct(avg)}%` }}
          />
        )}
        <div
          className="absolute top-1/2 w-4 h-4 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-dark ring-2 ring-white"
          style={{ left: `${pct(point)}%` }}
        />
      </div>

      <div dir="ltr" className="flex justify-between text-[11px] text-muted num mt-1">
        <span>0</span>
        <span>{max / 2}</span>
        <span>{max}</span>
      </div>

      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted mt-2">
        <li className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-brand-dark" aria-hidden="true" /> תחזית
        </li>
        <li className="inline-flex items-center gap-1.5">
          <span className="w-4 h-2 rounded-full bg-brand-primary/35" aria-hidden="true" /> טווח 80%
        </li>
        {avg != null && (
          <li className="inline-flex items-center gap-1.5">
            <span className="w-0 h-3 border-l-2 border-dashed border-slate-500" aria-hidden="true" /> ממוצע היסטורי
          </li>
        )}
      </ul>
    </div>
  );
}

const CALLOUT_TONES = {
  info: { box: "bg-blue-50 border-blue-200 text-blue-900", icon: "info" },
  warn: { box: "bg-amber-50 border-amber-200 text-amber-900", icon: "alert" },
  tip: { box: "bg-white border-line text-ink", icon: "lightbulb" },
} as const;

function Callout({ tone, title, children }: { tone: keyof typeof CALLOUT_TONES; title: string; children: React.ReactNode }) {
  const t = CALLOUT_TONES[tone];
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm leading-relaxed ${t.box}`}>
      <div className="font-bold flex items-center gap-2">
        <Icon name={t.icon} size={16} />
        {title}
      </div>
      <div className="mt-1 opacity-90">{children}</div>
    </div>
  );
}
