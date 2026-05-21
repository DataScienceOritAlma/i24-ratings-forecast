"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { createCheckoutSession } from "@/lib/api";
import NavBar from "@/components/NavBar";

export default function AccountPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-muted">טוען...</div>}>
      <AccountInner />
    </Suspense>
  );
}

interface Org { id: string; name: string; type: string; created_at: string }
interface Profile { full_name: string | null; role: string; organization_id: string }
interface Subscription {
  status: string;
  tier: string;
  trial_ends_at: string | null;
  current_period_end: string | null;
}

function AccountInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState<string | null>(null);
  const [org, setOrg] = useState<Org | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const [upgrading, setUpgrading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const successFlag = params.get("success") === "1";
  const canceledFlag = params.get("canceled") === "1";

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) { router.replace("/"); return; }
      const user = data.session.user;
      setEmail(user.email ?? null);
      setUserId(user.id);
      setCreatedAt(user.created_at);

      const { data: prof } = await supabase
        .from("profiles")
        .select("full_name, role, organization_id")
        .eq("id", user.id)
        .maybeSingle();

      if (prof) {
        setProfile(prof as Profile);
        const [{ data: o }, { data: s }] = await Promise.all([
          supabase.from("organizations").select("id, name, type, created_at").eq("id", prof.organization_id).maybeSingle(),
          supabase.from("subscriptions").select("status, tier, trial_ends_at, current_period_end").eq("organization_id", prof.organization_id).maybeSingle(),
        ]);
        if (o) setOrg(o as Org);
        if (s) setSub(s as Subscription);
      }

      const { count: c } = await supabase.from("predictions").select("*", { count: "exact", head: true });
      setCount(c ?? 0);
    });
  }, [router]);

  async function handleUpgrade() {
    if (!userId || !profile || !email) return;
    setError(null);
    setUpgrading(true);
    try {
      const r = await createCheckoutSession({
        user_id: userId,
        organization_id: profile.organization_id,
        email,
        return_url: window.location.origin + "/account",
      });
      window.location.href = r.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUpgrading(false);
    }
  }

  if (!email) return <div className="p-8 text-center text-muted">טוען...</div>;

  const isPro = sub && (sub.status === "active" || sub.status === "trialing") && (sub.tier === "pro" || sub.tier === "enterprise");

  return (
    <main className="min-h-screen">
      <NavBar email={email} title="חשבון" />

      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        {successFlag && (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-4 text-sm text-green-800">
            🎉 <strong>תודה!</strong> השדרוג ל-Pro התקבל. אם הסטטוס עוד לא מתעדכן — רענני בעוד כמה שניות (webhook).
          </div>
        )}
        {canceledFlag && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-4 text-sm text-yellow-800">
            השדרוג בוטל — לא חוייבת. תוכלי לנסות שוב מתי שתרצי.
          </div>
        )}

        <section className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-black text-brand-dark mb-4">👤 פרטי משתמש</h2>
          <dl className="space-y-3 text-sm">
            <Row label="אימייל" value={<span dir="ltr">{email}</span>} />
            <Row label="שם מלא" value={profile?.full_name ?? "—"} />
            <Row label="הצטרפת בתאריך" value={createdAt ? new Date(createdAt).toLocaleDateString("he-IL") : "—"} />
            <Row label="תפקיד בארגון" value={profile?.role === "owner" ? "בעל הארגון" : profile?.role ?? "—"} />
          </dl>
        </section>

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

        {/* Subscription */}
        {isPro ? (
          <section className="bg-gradient-to-br from-emerald-600 to-teal-600 text-white rounded-2xl shadow-card p-6">
            <div className="text-xs opacity-80 mb-1">תוכנית נוכחית</div>
            <div className="text-3xl font-black mb-2">
              ✅ {sub!.tier === "enterprise" ? "Enterprise" : "Pro"} · {sub!.status === "trialing" ? "Trial" : "פעיל"}
            </div>
            {sub!.current_period_end && (
              <p className="text-sm opacity-90">
                החיוב הבא: {new Date(sub!.current_period_end).toLocaleDateString("he-IL")}
              </p>
            )}
            {sub!.trial_ends_at && sub!.status === "trialing" && (
              <p className="text-sm opacity-90">
                Trial מסתיים: {new Date(sub!.trial_ends_at).toLocaleDateString("he-IL")} (אז יחויב ₪990)
              </p>
            )}
          </section>
        ) : (
          <section className="bg-gradient-to-br from-brand-dark to-brand-primary text-white rounded-2xl shadow-card p-6">
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <div className="text-xs opacity-80 mb-1">תוכנית נוכחית</div>
                <div className="text-3xl font-black mb-2">Free</div>
                <p className="text-sm opacity-90 mb-3">שדרוג ל-Pro = תחזיות ללא הגבלה + 14 יום Trial חינם</p>
                <ul className="text-xs space-y-1 opacity-80">
                  <li>✓ תחזיות ללא הגבלה</li>
                  <li>✓ היסטוריה מלאה</li>
                  <li>✓ אנליטיקה מתקדמת</li>
                  <li>✓ Trial של 14 יום — אפשר לבטל בכל רגע</li>
                </ul>
              </div>
              <button
                onClick={handleUpgrade}
                disabled={upgrading}
                className="px-5 py-3 rounded-xl bg-brand-accent hover:bg-orange-600 transition font-bold whitespace-nowrap shadow-lg disabled:opacity-50"
              >
                {upgrading ? "מפנה ל-Stripe..." : "🚀 שדרוג ל-Pro · ₪990/חודש"}
              </button>
            </div>
            {error && (
              <div className="mt-4 bg-red-500/20 border border-red-300/30 rounded-lg p-3 text-sm">
                {error}
                {error.includes("Stripe לא מוגדר") && (
                  <div className="mt-2 text-xs opacity-80">
                    ראו STRIPE_SETUP.md לשלבי הגדרה — דורש חשבון Stripe חינמי וכמה משתני סביבה.
                  </div>
                )}
              </div>
            )}
          </section>
        )}

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
