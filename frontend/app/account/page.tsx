"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { createCheckoutSession } from "@/lib/api";
import NavBar from "@/components/NavBar";
import Icon from "@/components/Icon";

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

  if (!email) return <div className="p-8 text-center text-muted" role="status">טוען...</div>;

  const isPro = sub && (sub.status === "active" || sub.status === "trialing") && (sub.tier === "pro" || sub.tier === "enterprise");

  return (
    <main className="min-h-dvh bg-canvas">
      <NavBar email={email} title="חשבון" />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {successFlag && (
          <div className="card border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 flex gap-2" role="status">
            <Icon name="check" size={18} />
            <span><strong>השדרוג ל-Pro התקבל, תודה.</strong> אם הסטטוס עוד לא התעדכן, רענני את הדף בעוד כמה שניות.</span>
          </div>
        )}
        {canceledFlag && (
          <div className="card border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 flex gap-2" role="status">
            <Icon name="info" size={18} />
            <span>השדרוג בוטל ולא חויבת. אפשר לנסות שוב מתי שתרצי.</span>
          </div>
        )}

        <section className="card p-5 sm:p-6" aria-labelledby="user-title">
          <h2 id="user-title" className="text-lg font-bold text-brand-dark mb-4 flex items-center gap-2">
            <Icon name="user" size={20} className="text-muted" />
            פרטי משתמש
          </h2>
          <dl className="text-sm">
            <Row label="אימייל" value={<span dir="ltr">{email}</span>} />
            <Row label="שם מלא" value={profile?.full_name ?? "—"} />
            <Row label="תאריך הצטרפות" value={createdAt ? new Date(createdAt).toLocaleDateString("he-IL") : "—"} />
            <Row label="תפקיד בארגון" value={profile?.role === "owner" ? "בעלים" : profile?.role ?? "—"} />
          </dl>
        </section>

        <section className="card p-5 sm:p-6" aria-labelledby="org-title">
          <h2 id="org-title" className="text-lg font-bold text-brand-dark mb-4 flex items-center gap-2">
            <Icon name="building" size={20} className="text-muted" />
            ארגון
          </h2>
          <dl className="text-sm">
            <Row label="שם" value={org?.name ?? "—"} />
            <Row label="סוג" value={
              org?.type === "individual" ? "אישי" :
              org?.type === "agency" ? "סוכנות מדיה" :
              org?.type === "channel" ? "ערוץ" :
              org?.type === "research" ? "יחידת מחקר" : org?.type ?? "—"
            } />
            <Row label="תחזיות שנוצרו" value={<span className="num">{(count ?? 0).toLocaleString("he-IL")}</span>} />
          </dl>
        </section>

        <section className={`card p-5 sm:p-6 ${isPro ? "border-emerald-300" : "border-brand-primary border-2"}`} aria-labelledby="plan-title">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h2 id="plan-title" className="text-sm font-medium text-muted">התוכנית הנוכחית</h2>
              {isPro ? (
                <>
                  <div className="text-2xl font-bold text-brand-dark mt-1 flex items-center gap-2 flex-wrap">
                    {sub!.tier === "enterprise" ? "Enterprise" : "Pro"}
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 font-bold">
                      <Icon name="check" size={12} />
                      {sub!.status === "trialing" ? "תקופת ניסיון" : "פעיל"}
                    </span>
                  </div>
                  {sub!.current_period_end && (
                    <p className="text-sm text-muted mt-2">
                      החיוב הבא: <span className="num text-ink">{new Date(sub!.current_period_end).toLocaleDateString("he-IL")}</span>
                    </p>
                  )}
                  {sub!.trial_ends_at && sub!.status === "trialing" && (
                    <p className="text-sm text-muted mt-1">
                      תקופת הניסיון מסתיימת ב-<span className="num text-ink">{new Date(sub!.trial_ends_at).toLocaleDateString("he-IL")}</span>, ואז יחויבו ₪990.
                    </p>
                  )}
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-brand-dark mt-1">Free</div>
                  <p className="text-sm text-muted mt-2">שדרוג ל-Pro כולל 14 יום ניסיון חינם, ואפשר לבטל בכל רגע.</p>
                  <ul className="text-sm space-y-1.5 mt-3">
                    {["תחזיות ללא הגבלה", "היסטוריה מלאה", "אנליטיקה מתקדמת"].map((f) => (
                      <li key={f} className="flex items-center gap-2">
                        <Icon name="check" size={16} className="text-brand-primary" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
            {!isPro && (
              <button onClick={handleUpgrade} disabled={upgrading} className="btn-primary whitespace-nowrap">
                {upgrading ? "מעבר ל-Stripe..." : "שדרוג ל-Pro · ₪990 לחודש"}
              </button>
            )}
          </div>
          {error && (
            <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-800 flex gap-2" role="alert">
              <Icon name="alert" size={18} />
              <span className="break-words">{error}</span>
            </div>
          )}
        </section>

        <section className="card p-5 sm:p-6" aria-labelledby="delete-title">
          <h2 id="delete-title" className="text-lg font-bold text-brand-dark">מחיקת חשבון</h2>
          <p className="text-sm text-muted mt-1">
            מחיקת החשבון מוחקת את כל היסטוריית התחזיות, ואי אפשר לשחזר אותה. האפשרות למחוק מכאן עדיין לא זמינה.
          </p>
          <button className="btn mt-4 text-sm border border-red-200 text-red-700 bg-white" disabled>
            מחיקת חשבון (בקרוב)
          </button>
        </section>
      </div>
    </main>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-2.5 border-b border-line last:border-b-0">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium text-ink text-left min-w-0 break-words">{value}</dd>
    </div>
  );
}
