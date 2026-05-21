"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";

export default function AnalyticsPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [stats, setStats] = useState<{ total: number; thisWeek: number; routine: number; special: number } | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) { router.replace("/"); return; }
      setEmail(data.session.user.email ?? null);

      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const [{ count: total }, { count: thisWeek }, { count: routine }, { count: special }] = await Promise.all([
        supabase.from("predictions").select("*", { count: "exact", head: true }),
        supabase.from("predictions").select("*", { count: "exact", head: true }).gte("created_at", sevenDaysAgo),
        supabase.from("predictions").select("*", { count: "exact", head: true }).eq("scenario", "routine"),
        supabase.from("predictions").select("*", { count: "exact", head: true }).eq("scenario", "special_event"),
      ]);
      setStats({
        total: total ?? 0,
        thisWeek: thisWeek ?? 0,
        routine: routine ?? 0,
        special: special ?? 0,
      });
    });
  }, [router]);

  if (!email) return <div className="p-8 text-center text-muted">טוען...</div>;

  return (
    <main className="min-h-screen">
      <NavBar email={email} title="אנליטיקה" />

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* My stats */}
        <section>
          <h2 className="text-lg font-black text-brand-dark mb-3">📈 השימוש שלי</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat n={stats?.total ?? 0} label="סה״כ תחזיות" />
            <Stat n={stats?.thisWeek ?? 0} label="השבוע" highlight />
            <Stat n={stats?.routine ?? 0} label="שגרה" />
            <Stat n={stats?.special ?? 0} label="אירועים מיוחדים" />
          </div>
        </section>

        {/* Model performance — static from RETROSPECTIVE.md */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-black text-brand-dark mb-1">🎯 ביצועי המודל</h2>
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
          <h2 className="text-lg font-black text-brand-dark mb-1">🔍 איפה המודל חזק / חלש</h2>
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

function Stat({ n, label, highlight }: { n: number; label: string; highlight?: boolean }) {
  return (
    <div className={`rounded-2xl p-4 shadow-card ${highlight ? "bg-brand-accent text-white" : "bg-white"}`}>
      <div className={`text-3xl font-black tabular-nums ${highlight ? "" : "text-brand-primary"}`}>
        {n.toLocaleString("he-IL")}
      </div>
      <div className={`text-xs mt-1 ${highlight ? "text-white/90" : "text-muted"}`}>{label}</div>
    </div>
  );
}

function BigStat({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div className="bg-slate-50 rounded-xl p-4">
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
          className="h-full bg-brand-primary rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
