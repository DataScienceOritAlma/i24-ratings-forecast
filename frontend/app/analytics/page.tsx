"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";
import { Skeleton } from "@/components/Skeleton";
import Icon, { type IconName } from "@/components/Icon";

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
      <NavBar email={email} title="אנליטיקה" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        <section aria-labelledby="usage-title">
          <h2 id="usage-title" className="text-lg font-bold text-brand-dark mb-3">השימוש שלי</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {stats === null ? (
              Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-24 rounded-xl" />
              ))
            ) : (
              <>
                <Stat n={stats.total} label="סך התחזיות" icon="history" />
                <Stat n={stats.thisWeek} label="בשבוע האחרון" icon="calendar" />
                <Stat n={stats.routine} label="תרחישי שגרה" icon="target" />
                <Stat n={stats.special} label="תרחישי אירוע ביטחוני" icon="alert" />
              </>
            )}
          </div>
        </section>

        <section className="card p-5 sm:p-6" aria-labelledby="activity-title">
          <div className="flex items-baseline justify-between gap-3 mb-4 flex-wrap">
            <h2 id="activity-title" className="text-lg font-bold text-brand-dark">תחזיות ליום, 14 הימים האחרונים</h2>
            {avgRating != null && (
              <div className="text-sm text-muted">
                רייטינג חזוי ממוצע: <span className="font-bold text-ink num">{avgRating.toFixed(2)}</span>
              </div>
            )}
          </div>
          {activity === null ? (
            <Skeleton className="h-32 rounded-lg" />
          ) : activity.every((d) => d.count === 0) ? (
            <p className="text-sm text-muted text-center py-8">לא נוצרו תחזיות ב-14 הימים האחרונים.</p>
          ) : (
            <Sparkline activity={activity} />
          )}
        </section>

        <section className="card p-5 sm:p-6" aria-labelledby="top-title">
          <h2 id="top-title" className="text-lg font-bold text-brand-dark">התוכניות שנחזו הכי הרבה</h2>
          <p className="text-sm text-muted mt-0.5 mb-4">14 הימים האחרונים</p>
          {topPrograms === null ? (
            <Skeleton className="h-40 rounded-lg" />
          ) : topPrograms.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">עדיין אין מספיק נתונים.</p>
          ) : (
            <ol className="space-y-3">
              {topPrograms.map((p, i) => {
                const maxCount = topPrograms[0].count;
                const pct = (p.count / maxCount) * 100;
                return (
                  <li key={p.name} className="flex items-center gap-3">
                    <div className="w-6 text-center text-sm font-bold text-muted num">{i + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between mb-1 gap-2">
                        <div className="text-sm font-bold text-ink truncate" title={p.name}>{p.name}</div>
                        <div className="text-xs text-muted num flex-shrink-0">{p.count} תחזיות</div>
                      </div>
                      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div className="h-full bg-brand-primary rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      </div>
    </main>
  );
}

function Stat({ n, label, icon }: { n: number; label: string; icon: IconName }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-2 text-muted">
        <div className="text-xs">{label}</div>
        <Icon name={icon} size={16} />
      </div>
      <div className="text-3xl font-bold text-brand-dark num mt-1">{n.toLocaleString("he-IL")}</div>
    </div>
  );
}

function Sparkline({ activity }: { activity: { date: string; label: string; count: number }[] }) {
  const max = Math.max(1, ...activity.map((d) => d.count));
  const W = 700;
  const H = 130;
  const padL = 30;
  const padR = 12;
  const padT = 12;
  const padB = 26;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const stepX = activity.length > 1 ? innerW / (activity.length - 1) : 0;

  const points = activity.map((d, i) => ({
    x: padL + i * stepX,
    y: padT + innerH - (d.count / max) * innerH,
    ...d,
  }));

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");
  const area = `${path} L ${points[points.length - 1].x.toFixed(1)} ${(padT + innerH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padT + innerH).toFixed(1)} Z`;

  const total = activity.reduce((s, d) => s + d.count, 0);

  return (
    <div>
      {/* Time runs left to right, as on any chart */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-36"
        role="img"
        aria-label={`${total} תחזיות ב-14 הימים האחרונים, שיא יומי ${max}`}
      >
        {[0.5, 1].map((f) => (
          <line
            key={f}
            x1={padL}
            x2={W - padR}
            y1={padT + innerH * (1 - f)}
            y2={padT + innerH * (1 - f)}
            stroke="#E1E7EF"
            strokeWidth={1}
          />
        ))}
        <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="#CBD5E1" strokeWidth={1} />
        <path d={area} fill="#1E5DB8" fillOpacity={0.08} />
        <path d={path} fill="none" stroke="#1E5DB8" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={p.count > 0 ? 4 : 2.5} fill={p.count > 0 ? "#0A2540" : "#CBD5E1"} stroke="white" strokeWidth={2} />
            <title>{`${p.label}: ${p.count} תחזיות`}</title>
          </g>
        ))}
        {[0, Math.floor(points.length / 2), points.length - 1].map((i) => (
          <text key={i} x={points[i].x} y={H - 6} textAnchor="middle" fontSize={11} fill="#55657A">
            {points[i].label}
          </text>
        ))}
        <text x={padL - 6} y={padT + 4} textAnchor="end" fontSize={11} fill="#55657A">{max}</text>
        <text x={padL - 6} y={padT + innerH + 4} textAnchor="end" fontSize={11} fill="#55657A">0</text>
      </svg>
      <p className="text-xs text-muted text-center mt-1">
        סך הכול <span className="num">{total.toLocaleString("he-IL")}</span> תחזיות ב-14 ימים · שיא יומי: <span className="num">{max}</span>
      </p>
    </div>
  );
}
