"use client";

import { useState, useEffect } from "react";
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

  if (!email) return <div className="p-8 text-center text-muted">טוען...</div>;

  return (
    <main className="min-h-screen">
      <NavBar email={email} title="היסטוריית תחזיות" />

      <div className="max-w-5xl mx-auto px-6 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-sm text-red-700 mb-6">
            <strong>שגיאה בטעינת היסטוריה:</strong> {error}
          </div>
        )}

        {predictions === null && (
          <div className="grid sm:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <PredictionCardSkeleton key={i} />
            ))}
          </div>
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
            <p className="text-sm text-muted mb-4">
              {predictions.length} תחזיות (מהאחרונה לישנה)
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              {predictions.map((p) => (
                <article
                  key={p.id}
                  className="bg-white rounded-2xl shadow-card p-5 hover:shadow-card-hover transition"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-black text-brand-dark">
                        {p.program_name ?? "—"}
                      </h3>
                      <div className="text-xs text-muted mt-0.5">
                        {p.target_date}
                        {p.target_start_time && ` · ${p.target_start_time.slice(0, 5)}`}
                        {p.target_end_time && `–${p.target_end_time.slice(0, 5)}`}
                      </div>
                    </div>
                    {p.scenario === "special_event" && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-brand-accent text-white font-bold">
                        אירוע מיוחד
                      </span>
                    )}
                  </div>

                  <div className="text-4xl font-black text-brand-primary tabular-nums mb-1">
                    {p.predicted_rating.toFixed(2)}
                  </div>
                  <div className="text-xs text-muted mb-3">
                    טווח 80%:{" "}
                    <span className="tabular-nums">
                      {p.prediction_low.toFixed(2)}–{p.prediction_high.toFixed(2)}
                    </span>
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
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
