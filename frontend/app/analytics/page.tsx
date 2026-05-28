"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";
import { Skeleton } from "@/components/Skeleton";

interface RecentRow {
  program_name: string | null;
  predicted_rating: number;
  scenario: string;
  created_at: string;
}

export default function AnalyticsPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [stats, setStats] = useState<{
    total: number; thisWeek: number; routine: number; special: number;
  } | null>(null);
  const [rows, setRows] = useState<RecentRow[] | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) { router.replace("/"); return; }
      setEmail(data.session.user.email ?? null);

      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const fourteenDaysAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString();
      const [
        { count: total },
        { count: thisWeek },
        { count: routine },
        { count: special },
        { data: recent },
      ] = await Promise.all([
        supabase.from("predictions").select("*", { count: "exact", head: true }),
        supabase.from("predictions").select("*", { count: "exact", head: true }).gte("created_at", sevenDaysAgo),
        supabase.from("predictions").select("*", { count: "exact", head: true }).eq("scenario", "routine"),
        supabase.from("predictions").select("*", { count: "exact", head: true }).eq("scenario", "special_event"),
        supabase.from("predictions")
          .select("program_name, predicted_rating, scenario, created_at")
          .gte("created_at", fourteenDaysAgo)
          .order("created_at", { ascending: false })
          .limit(500),
      ]);
      setStats({
        total: total ?? 0,
        thisWeek: thisWeek ?? 0,
        routine: routine ?? 0,
        special: special ?? 0,
      });
      setRows((recent ?? []) as unknown as RecentRow[]);
    });
  }, [router]);

  // Daily activity for sparkline (last 14 days)
  const activity = useMemo(() => {
    if (!rows) return null;
    const days: { date: string; label: string; count: number }[] = [];
    for (let i = 13; i >= 0; i--) {
      const d = new Date();
      d.setHours(0, 0, 0, 0);
      d.setDate(d.getDate() - i);
      const iso = d.toISOString().slice(0, 10);
      days.push({
        date: iso,
        label: d.toLocaleDateString("he-IL", { day: "numeric", month: "numeric" }),
        count: 0,
      });
    }
    rows.forEach((r) => {
      const iso = r.created_at.slice(0, 10);
      const day = days.find((d) => d.date === iso);
      if (day) day.count += 1;
    });
    return days;
  }, [rows]);

  // Top-5 most predicted programs
  const topPrograms = useMemo(() => {
    if (!rows) return null;
    const counts: Record<string, number> = {};
    rows.forEach((r) => {
      const k = r.program_name ?? "—";
      counts[k] = (counts[k] ?? 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({ name, count }));
  }, [rows]);

  // Average predicted rating
  const avgRating = useMemo(() => {
    if (!rows || rows.length === 0) return null;
    const sum = rows.reduce((a, b) => a + Number(b.predicted_rating), 0);
    return sum / rows.length;
  }, [rows]);

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
      <NavBar email={email} title="אנליטיקה" />

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* My stats */}
        <section>
          <h2 className="text-lg font-black text-brand-dark mb-3 flex items-center gap-2">
            <span>📈</span> השימוש שלי
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {stats === null ? (
              Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-24 rounded-2xl" />
              ))
            ) : (
              <>
                <Stat n={stats.total} label="סה״כ תחזיות" icon="📊" />
                <Stat n={stats.thisWeek} label="השבוע" icon="📅" highlight />
                <Stat n={stats.routine} label="שגרה" icon="🕐" />
                <Stat n={stats.special} label="אירועים ביטחוניים" icon="🚨" />
              </>
            )}
          </div>
        </section>

        {/* Activity sparkline */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-lg font-black text-brand-dark flex items-center gap-2">
              <span>📊</span> פעילות ב-14 הימים האחרונים
            </h2>
            {avgRating != null && (
              <div className="text-sm text-muted">
                ממוצע: <span className="font-black text-brand-primary tabular-nums">{avgRating.toFixed(2)}</span>
              </div>
            )}
          </div>
          {activity === null ? (
            <Skeleton className="h-32 rounded-xl" />
          ) : (
            <Sparkline activity={activity} />
          )}
        </section>

        {/* Top programs */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-black text-brand-dark mb-1 flex items-center gap-2">
            <span>⭐</span> 5 התוכניות שאת חוזה הכי הרבה
          </h2>
          <p className="text-sm text-muted mb-4">מתוך 14 הימים האחרונים</p>
          {topPrograms === null ? (
            <Skeleton className="h-40 rounded-xl" />
          ) : topPrograms.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">עדיין אין מספיק נתונים</p>
          ) : (
            <div className="space-y-2">
              {topPrograms.map((p, i) => {
                const maxCount = topPrograms[0].count;
                const pct = (p.count / maxCount) * 100;
                return (
                  <div key={p.name} className="flex items-center gap-3">
                    <div className="w-6 text-center text-sm font-black text-muted tabular-nums">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between mb-1 gap-2">
                        <div className="text-sm font-bold text-ink truncate" title={p.name}>{p.name}</div>
                        <div className="text-xs text-muted tabular-nums flex-shrink-0">
                          {p.count} תחזיות
                        </div>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-l from-brand-primary to-brand-light rounded-full transition-all duration-700"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Model performance — static from RETROSPECTIVE.md */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-black text-brand-dark mb-1 flex items-center gap-2">
            <span>🎯</span> ביצועי המודל
          </h2>
          <p className="text-sm text-muted mb-5">
            נמדד על 1,957 שידורים שהמודל לא ראה (סט בחינה, פברואר→אפריל 2026)
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <BigStat value="0.263" label="MAE" sub="טעות ממוצעת" />
            <BigStat value="0.603" label="R²" sub="60% מוסבר" />
            <BigStat value="57%" label="±0.2" sub="קרוב לאמת" />
            <BigStat value="87%" label="±0.5" sub="טווח רחב" />
          </div>
        </section>

        {/* Per-segment */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-black text-brand-dark mb-1 flex items-center gap-2">
            <span>🔍</span> איפה המודל חזק / חלש
          </h2>
          <p className="text-sm text-muted mb-5">MAE לפי סטטוס תוכנית (נמוך יותר = מדויק יותר)</p>
          <div className="space-y-3">
            <SegBar label="שידור חוזר" mae={0.193} maxMae={0.40} note="🟢 הכי מדויק" />
            <SegBar label="לקט" mae={0.221} maxMae={0.40} />
            <SegBar label="שידור חי" mae={0.309} maxMae={0.40} note="קהל תנודתי" />
            <SegBar label="מיוחד / מבזק" mae={0.339} maxMae={0.40} note="🔴 הכי קשה" />
          </div>
        </section>

        {/* Insight callout */}
        <section className="bg-gradient-to-br from-brand-dark to-brand-primary text-white rounded-2xl shadow-card p-6">
          <div className="text-xs opacity-80 mb-1">תובנה</div>
          <h3 className="text-xl font-black mb-2">תקרת המודל היא drift של אירועים בלתי-צפויים</h3>
          <p className="text-sm opacity-90 leading-relaxed">
            המודל נכשל בעיקר באירועי ברייקינג ביטחוניים (שאגת הארי, מתקפה איראנית) — אירועים שאף מודל
            היסטורי לא יכול לחזות. ב-87% מהמקרים הרגילים — הטעות בטווח של ±0.5 נקודות רייטינג.
          </p>
        </section>
      </div>
    </main>
  );
}

function Stat({ n, label, highlight, icon }: { n: number; label: string; highlight?: boolean; icon: string }) {
  return (
    <div className={`rounded-2xl p-4 shadow-card transition hover:shadow-lg ${
      highlight ? "bg-gradient-to-br from-brand-accent to-orange-500 text-white" : "bg-white"
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className={`text-3xl font-black tabular-nums ${highlight ? "" : "text-brand-primary"}`}>
            {n.toLocaleString("he-IL")}
          </div>
          <div className={`text-xs mt-0.5 ${highlight ? "text-white/90" : "text-muted"}`}>{label}</div>
        </div>
        <div className="text-2xl opacity-80">{icon}</div>
      </div>
    </div>
  );
}

function BigStat({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div className="bg-slate-50 rounded-xl p-4 transition hover:bg-slate-100">
      <div className="text-3xl font-black tabular-nums text-brand-primary">{value}</div>
      <div className="text-sm font-bold text-ink mt-1">{label}</div>
      <div className="text-xs text-muted">{sub}</div>
    </div>
  );
}

function SegBar({ label, mae, maxMae, note }: { label: string; mae: number; maxMae: number; note?: string }) {
  const pct = (mae / maxMae) * 100;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="font-bold">{label}</span>
        <span className="tabular-nums">{mae.toFixed(3)} {note && <span className="text-muted text-xs">· {note}</span>}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-l from-brand-primary to-brand-light rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function Sparkline({ activity }: { activity: { date: string; label: string; count: number }[] }) {
  const max = Math.max(1, ...activity.map((d) => d.count));
  const W = 700;
  const H = 120;
  const padL = 30;
  const padR = 10;
  const padT = 10;
  const padB = 24;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const stepX = activity.length > 1 ? innerW / (activity.length - 1) : 0;

  const points = activity.map((d, i) => {
    const x = padL + i * stepX;
    const y = padT + innerH - (d.count / max) * innerH;
    return { x, y, ...d };
  });

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");
  const area = `${path} L ${points[points.length - 1].x.toFixed(1)} ${(padT + innerH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padT + innerH).toFixed(1)} Z`;

  const total = activity.reduce((s, d) => s + d.count, 0);

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-32" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1E5DB8" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#1E5DB8" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Y axis grid */}
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <line
            key={f}
            x1={padL}
            x2={W - padR}
            y1={padT + innerH * (1 - f)}
            y2={padT + innerH * (1 - f)}
            stroke="#e2e8f0"
            strokeWidth={1}
            strokeDasharray="2 4"
          />
        ))}
        {/* Area fill */}
        <path d={area} fill="url(#sparkGrad)" />
        {/* Line */}
        <path d={path} fill="none" stroke="#1E5DB8" strokeWidth={2.5} strokeLinejoin="round" />
        {/* Points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r={p.count > 0 ? 4 : 2.5}
              fill={p.count > 0 ? "#FF6B35" : "#cbd5e1"}
              stroke="white"
              strokeWidth={2}
            />
            <title>{`${p.label}: ${p.count} תחזיות`}</title>
          </g>
        ))}
        {/* X labels: first / middle / last */}
        {[0, Math.floor(points.length / 2), points.length - 1].map((i) => (
          <text
            key={i}
            x={points[i].x}
            y={H - 6}
            textAnchor="middle"
            fontSize={11}
            fill="#64748b"
          >
            {points[i].label}
          </text>
        ))}
        {/* Y max label */}
        <text x={padL - 5} y={padT + 4} textAnchor="end" fontSize={10} fill="#94a3b8" className="tabular-nums">
          {max}
        </text>
      </svg>
      <div className="text-xs text-muted text-center mt-1">
        סה״כ {total.toLocaleString("he-IL")} תחזיות ב-14 ימים · שיא יומי: {max}
      </div>
    </div>
  );
}
