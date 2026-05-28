"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";
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

  return (
    <main className="min-h-screen bg-slate-50">
      <NavBar email={email} title="היסטוריית תחזיות" />

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-sm text-red-700">
            <strong>שגיאה בטעינת היסטוריה:</strong> {error}
          </div>
        )}

        {predictions === null && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-white rounded-2xl shadow-card p-4 h-20 animate-pulse" />
              ))}
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <PredictionCardSkeleton key={i} />
              ))}
            </div>
          </>
        )}

        {predictions && predictions.length === 0 && (
          <div className="bg-white rounded-2xl shadow-card p-10 text-center">
            <div className="text-5xl mb-4">📊</div>
            <h2 className="text-xl font-black text-brand-dark mb-2">
              עדיין אין תחזיות
            </h2>
            <p className="text-muted mb-6">
              צרי את התחזית הראשונה שלך בלוח החיזוי, והיא תופיע כאן.
            </p>
            <Link
              href="/dashboard"
              className="inline-block px-5 py-2.5 rounded-xl bg-brand-primary text-white font-bold hover:bg-brand-dark transition"
            >
              🎯 לחיזוי הראשון
            </Link>
          </div>
        )}

        {predictions && predictions.length > 0 && (
          <>
            {/* Summary KPIs */}
            <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <SummaryCard label="סך תחזיות" value={summary.total.toString()} icon="📊" />
              <SummaryCard
                label="רייטינג ממוצע"
                value={summary.avgRating.toFixed(2)}
                icon="🎯"
                accent
              />
              <SummaryCard
                label="הכי נחזית"
                value={summary.topProgram}
                icon="⭐"
                smallValue
              />
              <SummaryCard
                label="אירועים ביטחוניים"
                value={summary.specialCount.toString()}
                icon="🚨"
              />
            </section>

            {/* Filters */}
            <section className="bg-white rounded-2xl shadow-card p-4 flex flex-wrap gap-3 items-center">
              <div className="flex-1 min-w-[200px] relative">
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted">🔍</span>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="חפשי לפי שם תוכנית..."
                  className="w-full px-4 py-2 pr-10 rounded-xl border border-slate-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/10 focus:outline-none transition"
                />
              </div>
              <div className="flex gap-1.5 p-1 bg-slate-100 rounded-xl">
                {([
                  { k: "all", label: "הכל" },
                  { k: "routine", label: "שגרה" },
                  { k: "special_event", label: "אירועים" },
                ] as const).map((f) => (
                  <button
                    key={f.k}
                    onClick={() => setFilter(f.k)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-bold transition ${
                      filter === f.k
                        ? "bg-white text-brand-dark shadow-sm"
                        : "text-muted hover:text-ink"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </section>

            {/* Cards grid */}
            {filtered && filtered.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-card p-10 text-center text-muted">
                <div className="text-3xl mb-2">🔎</div>
                לא נמצאו תוצאות עבור הסינון הנוכחי.
              </div>
            ) : (
              <>
                <p className="text-sm text-muted">
                  מציג {filtered?.length ?? 0} מתוך {predictions.length}
                </p>
                <div className="grid sm:grid-cols-2 gap-4">
                  {filtered?.map((p) => <PredictionCard key={p.id} p={p} />)}
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
  label, value, icon, accent, smallValue,
}: { label: string; value: string; icon: string; accent?: boolean; smallValue?: boolean }) {
  return (
    <div
      className={`rounded-2xl p-4 shadow-card transition hover:shadow-lg ${
        accent ? "bg-gradient-to-br from-brand-primary to-brand-dark text-white" : "bg-white"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div
            className={`font-black tabular-nums ${
              smallValue ? "text-base truncate" : "text-2xl"
            } ${accent ? "" : "text-brand-dark"}`}
            title={smallValue ? value : undefined}
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

function PredictionCard({ p }: { p: Prediction }) {
  const ratingScale = 5;
  const lowPct = Math.max(0, Math.min(100, (p.prediction_low / ratingScale) * 100));
  const highPct = Math.max(0, Math.min(100, (p.prediction_high / ratingScale) * 100));
  const midPct = Math.max(0, Math.min(100, (p.predicted_rating / ratingScale) * 100));

  return (
    <article className="bg-white rounded-2xl shadow-card p-5 hover:shadow-card-hover transition border border-transparent hover:border-brand-primary/20">
      <div className="flex items-start justify-between mb-3 gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-black text-brand-dark truncate" title={p.program_name ?? ""}>
            {p.program_name ?? "—"}
          </h3>
          <div className="text-xs text-muted mt-0.5">
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
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-brand-accent text-white font-bold whitespace-nowrap">
            🚨 ביטחוני
          </span>
        )}
      </div>

      <div className="text-4xl font-black text-brand-primary tabular-nums mb-1 leading-none">
        {p.predicted_rating.toFixed(2)}
      </div>
      <div className="text-xs text-muted mb-2">
        טווח 80%:{" "}
        <span className="tabular-nums font-bold text-ink">
          {p.prediction_low.toFixed(2)}–{p.prediction_high.toFixed(2)}
        </span>
      </div>

      <div className="relative h-2 bg-slate-100 rounded-full overflow-hidden mb-4">
        <div
          className="absolute h-full bg-gradient-to-l from-brand-accent/30 to-brand-primary/30 rounded-full"
          style={{ insetInlineStart: `${lowPct}%`, width: `${Math.max(0, highPct - lowPct)}%` }}
        />
        <div
          className="absolute top-1/2 w-1 h-3.5 bg-brand-primary rounded-full -translate-y-1/2"
          style={{ insetInlineStart: `${midPct}%`, transform: "translate(50%, -50%)" }}
        />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-slate-50 rounded-lg p-2 text-center">
          <div className="font-black text-ink tabular-nums">
            {p.estimated_households.toLocaleString("he-IL")}
          </div>
          <div className="text-muted">בתי-אב</div>
        </div>
        <div className="bg-slate-50 rounded-lg p-2 text-center">
          <div className="font-black text-ink tabular-nums">
            {p.estimated_viewers.toLocaleString("he-IL")}
          </div>
          <div className="text-muted">צופים</div>
        </div>
      </div>

      <div className="text-[10px] text-muted mt-3 pt-3 border-t border-slate-100">
        {new Date(p.created_at).toLocaleString("he-IL")}
      </div>
    </article>
  );
}
