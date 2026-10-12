"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";
import Icon, { type IconName } from "@/components/Icon";
import RangeBar, { rangeScaleMax } from "@/components/RangeBar";
import { PredictionCardSkeleton } from "@/components/Skeleton";

interface Prediction {
  id: string;
  program_name: string | null;
  target_date: string;
  target_start_time: string | null;
  target_end_time: string | null;
  scenario: string;
  predicted_rating: number;
  prediction_low: number;
  prediction_high: number;
  estimated_households: number;
  estimated_viewers: number;
  model_version: string;
  uncertainty_source: string | null;
  created_at: string;
}

const FILTERS = [
  { k: "all", label: "הכול" },
  { k: "routine", label: "שגרה" },
  { k: "special_event", label: "אירועים" },
] as const;

export default function HistoryPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<Prediction[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "routine" | "special_event">("all");

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) {
        router.replace("/");
        return;
      }
      setEmail(data.session.user.email ?? null);

      const { data: rows, error: err } = await supabase
        .from("predictions")
        .select(
          "id, program_name, target_date, target_start_time, target_end_time, scenario, " +
            "predicted_rating, prediction_low, prediction_high, " +
            "estimated_households, estimated_viewers, model_version, " +
            "uncertainty_source, created_at",
        )
        .order("created_at", { ascending: false })
        .limit(100);

      if (err) {
        setError(err.message);
        setPredictions([]);
      } else {
        setPredictions((rows ?? []) as unknown as Prediction[]);
      }
    });
  }, [router]);

  const filtered = useMemo(() => {
    if (!predictions) return null;
    const q = search.trim().toLowerCase();
    return predictions.filter((p) => {
      if (filter !== "all" && p.scenario !== filter) return false;
      if (q && !(p.program_name ?? "").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [predictions, search, filter]);

  const summary = useMemo(() => {
    if (!predictions || predictions.length === 0) {
      return { total: 0, avgRating: 0, topProgram: "—", specialCount: 0 };
    }
    const ratings = predictions.map((p) => p.predicted_rating);
    const avg = ratings.reduce((a, b) => a + b, 0) / ratings.length;
    const counts: Record<string, number> = {};
    predictions.forEach((p) => {
      const k = p.program_name ?? "—";
      counts[k] = (counts[k] ?? 0) + 1;
    });
    const topProgram = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";
    const specialCount = predictions.filter((p) => p.scenario === "special_event").length;
    return { total: predictions.length, avgRating: avg, topProgram, specialCount };
  }, [predictions]);

  // One scale for every card, so the bars are comparable down the page.
  const scaleMax = useMemo(
    () => rangeScaleMax(...(predictions ?? []).map((p) => p.prediction_high)),
    [predictions],
  );

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

  return (
    <main className="min-h-dvh bg-canvas">
      <NavBar email={email} title="היסטוריית תחזיות" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {error && (
          <div className="card border-red-200 bg-red-50 p-4 text-sm text-red-800 flex gap-2" role="alert">
            <Icon name="alert" size={18} />
            <span><strong>ההיסטוריה לא נטענה.</strong> {error}</span>
          </div>
        )}

        {predictions === null && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="card p-4 h-20 animate-pulse" />
              ))}
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <PredictionCardSkeleton key={i} />
              ))}
            </div>
          </>
        )}

        {predictions && predictions.length === 0 && !error && (
          <div className="card p-10 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-50 text-brand-primary">
              <Icon name="history" size={24} />
            </div>
            <h2 className="text-xl font-bold text-brand-dark mt-4">עדיין אין תחזיות</h2>
            <p className="text-muted mt-1 mb-6">
              כל תחזית שתחשבי בלוח החיזוי נשמרת כאן אוטומטית.
            </p>
            <Link href="/dashboard" className="btn-primary">
              לחיזוי הראשון
              <Icon name="arrowLeft" size={18} />
            </Link>
          </div>
        )}

        {predictions && predictions.length > 0 && (
          <>
            <section aria-label="סיכום" className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <SummaryCard label="סך התחזיות" value={summary.total.toLocaleString("he-IL")} icon="history" />
              <SummaryCard label="רייטינג חזוי ממוצע" value={summary.avgRating.toFixed(2)} icon="target" />
              <SummaryCard label="התוכנית הנחזית ביותר" value={summary.topProgram} icon="chart" smallValue />
              <SummaryCard label="תרחישי אירוע ביטחוני" value={summary.specialCount.toLocaleString("he-IL")} icon="alert" />
            </section>

            <section aria-label="סינון" className="card p-3 flex flex-wrap gap-3 items-center">
              <div className="flex-1 min-w-[200px] relative">
                <label htmlFor="search" className="sr-only">חיפוש לפי שם תוכנית</label>
                <Icon name="search" size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
                <input
                  id="search"
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="חיפוש לפי שם תוכנית"
                  className="field pr-10"
                />
              </div>
              <div className="flex gap-1 p-1 bg-slate-100 rounded-lg" role="group" aria-label="סינון לפי תרחיש">
                {FILTERS.map((f) => (
                  <button
                    key={f.k}
                    onClick={() => setFilter(f.k)}
                    aria-pressed={filter === f.k}
                    className={`min-h-[36px] px-3 rounded-md text-sm font-bold transition-colors duration-150 cursor-pointer ${
                      filter === f.k ? "bg-white text-brand-dark shadow-card" : "text-muted hover:text-brand-dark"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </section>

            {filtered && filtered.length === 0 ? (
              <div className="card p-10 text-center text-muted">
                <p>אין תחזיות שמתאימות לסינון הזה.</p>
                <button onClick={() => { setSearch(""); setFilter("all"); }} className="btn-secondary mt-4 text-sm">
                  ניקוי הסינון
                </button>
              </div>
            ) : (
              <>
                <p className="text-sm text-muted" aria-live="polite">
                  מוצגות <span className="num">{filtered?.length ?? 0}</span> מתוך <span className="num">{predictions.length}</span>
                </p>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filtered?.map((p) => <PredictionCard key={p.id} p={p} scaleMax={scaleMax} />)}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}

function SummaryCard({
  label, value, icon, smallValue,
}: { label: string; value: string; icon: IconName; smallValue?: boolean }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-2 text-muted">
        <div className="text-xs">{label}</div>
        <Icon name={icon} size={16} />
      </div>
      <div
        className={`font-bold text-brand-dark num mt-1 ${smallValue ? "text-base truncate" : "text-2xl"}`}
        title={smallValue ? value : undefined}
      >
        {value}
      </div>
    </div>
  );
}

function PredictionCard({ p, scaleMax }: { p: Prediction; scaleMax: number }) {
  return (
    <article className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-bold text-brand-dark truncate" title={p.program_name ?? ""}>
            {p.program_name ?? "—"}
          </h3>
          <div className="text-xs text-muted mt-0.5 num">
            {new Date(p.target_date).toLocaleDateString("he-IL", {
              weekday: "short",
              day: "numeric",
              month: "short",
            })}
            {p.target_start_time && ` · ${p.target_start_time.slice(0, 5)}`}
            {p.target_end_time && `–${p.target_end_time.slice(0, 5)}`}
          </div>
        </div>
        {p.scenario === "special_event" && (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-orange-50 text-brand-accent border border-orange-200 font-bold whitespace-nowrap">
            <Icon name="alert" size={12} />
            אירוע ביטחוני
          </span>
        )}
      </div>

      <div className="flex items-baseline justify-between gap-3 mt-4">
        <div className="text-4xl font-bold text-brand-dark num leading-none">
          {p.predicted_rating.toFixed(2)}
        </div>
        <div className="text-xs text-muted">
          טווח 80%:{" "}
          <span className="num font-bold text-ink" dir="ltr">
            {p.prediction_low.toFixed(2)} – {p.prediction_high.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="mt-2">
        <RangeBar low={p.prediction_low} high={p.prediction_high} point={p.predicted_rating} max={scaleMax} compact />
      </div>

      <dl className="grid grid-cols-2 gap-2 text-xs mt-3">
        <div className="rounded-lg bg-canvas border border-line p-2">
          <dt className="text-muted">בתי אב</dt>
          <dd className="font-bold text-ink num">{p.estimated_households.toLocaleString("he-IL")}</dd>
        </div>
        <div className="rounded-lg bg-canvas border border-line p-2">
          <dt className="text-muted">צופים</dt>
          <dd className="font-bold text-ink num">{p.estimated_viewers.toLocaleString("he-IL")}</dd>
        </div>
      </dl>

      <div className="text-[11px] text-muted mt-3 pt-3 border-t border-line num">
        נוצרה ב-{new Date(p.created_at).toLocaleString("he-IL")}
      </div>
    </article>
  );
}
