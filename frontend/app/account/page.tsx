"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";

interface Org { id: string; name: string; type: string; created_at: string }
interface Profile { full_name: string | null; role: string }

export default function AccountPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState<string | null>(null);
  const [org, setOrg] = useState<Org | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) { router.replace("/"); return; }
      const user = data.session.user;
      setEmail(user.email ?? null);
      setCreatedAt(user.created_at);

      const { data: prof } = await supabase
        .from("profiles")
        .select("full_name, role, organization_id")
        .eq("id", user.id)
        .maybeSingle();

      if (prof) {
        setProfile({ full_name: prof.full_name, role: prof.role });
        const { data: o } = await supabase
          .from("organizations")
          .select("id, name, type, created_at")
          .eq("id", prof.organization_id)
          .maybeSingle();
        if (o) setOrg(o as Org);
      }

      const { count: c } = await supabase
        .from("predictions")
        .select("*", { count: "exact", head: true });
      setCount(c ?? 0);
    });
  }, [router]);

  if (!email) return <div className="p-8 text-center text-muted">טוען...</div>;

  return (
    <main className="min-h-screen">
      <NavBar email={email} title="חשבון" />

      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        {/* User info card */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-black text-brand-dark mb-4">👤 פרטי משתמש</h2>
          <dl className="space-y-3 text-sm">
            <Row label="אימייל" value={<span dir="ltr">{email}</span>} />
            <Row label="שם מלא" value={profile?.full_name ?? "—"} />
            <Row label="הצטרפת בתאריך" value={createdAt ? new Date(createdAt).toLocaleDateString("he-IL") : "—"} />
            <Row label="תפקיד בארגון" value={profile?.role === "owner" ? "בעל הארגון" : profile?.role ?? "—"} />
          </dl>
        </section>

        {/* Organization card */}
        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-black text-brand-dark mb-4">🏢 ארגון</h2>
          <dl className="space-y-3 text-sm">
            <Row label="שם" value={org?.name ?? "—"} />
            <Row label="סוג" value={
              org?.type === "individual" ? "אישי" :
              org?.type === "agency" ? "סוכנות מדיה" :
              org?.type === "channel" ? "ערוץ" :
              org?.type === "research" ? "יחידת מחקר" : org?.type ?? "—"
            } />
            <Row label="תחזיות שיצרתי" value={`${count ?? 0}`} />
          </dl>
        </section>

        {/* Subscription card */}
        <section className="bg-gradient-to-br from-brand-dark to-brand-primary text-white rounded-2xl shadow-card p-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="text-xs opacity-80 mb-1">תוכנית נוכחית</div>
              <div className="text-3xl font-black mb-2">Trial — 14 יום</div>
              <p className="text-sm opacity-90 mb-3">גישה מלאה לכל הפיצ&apos;רים. אחרי 14 יום — שדרוג ל-Pro.</p>
              <ul className="text-xs space-y-1 opacity-80">
                <li>✓ תחזיות ללא הגבלה</li>
                <li>✓ היסטוריה מלאה</li>
                <li>✓ אנליטיקה</li>
              </ul>
            </div>
            <button
              className="px-5 py-3 rounded-xl bg-brand-accent hover:bg-orange-600 transition font-bold whitespace-nowrap shadow-lg"
              onClick={() => alert("שדרוג ל-Pro — Stripe Checkout (יוטמע בשלב 4)")}
            >
              🚀 שדרוג ל-Pro · ₪990/חודש
            </button>
          </div>
        </section>

        {/* Danger zone */}
        <section className="bg-white rounded-2xl shadow-card p-6 border border-red-100">
          <h2 className="text-lg font-black text-red-700 mb-2">⚠️ פעולות מסוכנות</h2>
          <p className="text-sm text-muted mb-3">
            ביטול חשבון מוחק את כל ההיסטוריה שלך — אין דרך לשחזר.
          </p>
          <button
            className="px-4 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition text-sm font-bold"
            onClick={() => alert("מחיקת חשבון תתווסף בעתיד — נדרש אישור משתמש")}
          >
            מחיקת חשבון
          </button>
        </section>
      </div>
    </main>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-slate-100 pb-2">
      <dt className="text-muted">{label}</dt>
      <dd className="font-bold text-ink">{value}</dd>
    </div>
  );
}
