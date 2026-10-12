"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Icon, { type IconName } from "@/components/Icon";

const KPIS = [
  { n: "0.263", lbl: "MAE, שגיאה ממוצעת" },
  { n: "60%", lbl: "R², השונות המוסברת" },
  { n: "19", lbl: "מודלים בהשוואה" },
  { n: "10K", lbl: "שידורים באימון" },
];

const FEATURES: { icon: IconName; t: string; d: string }[] = [
  { icon: "target", t: "חיזוי מדויק", d: "MAE של 0.263 — טעות ממוצעת של פחות מ-7,000 בתי-אב. נבחר מתוך 19 מודלים שהושוו." },
  { icon: "message", t: "צ'אט בעברית טבעית", d: "שאלו ״מה הצפי לקבינט שישי בשישי הבא?״ וקבלו תשובה מפורטת עם רווח ביטחון." },
  { icon: "history", t: "היסטוריית תחזיות", d: "כל תחזית נשמרת. רואים איפה המודל צדק ואיפה לא, בשקיפות מלאה." },
  { icon: "chart", t: "אנליטיקה מתקדמת", d: "ביצועי מודל לפי סטטוס · זיהוי drift · 57% מהתחזיות בטווח ±0.2 מהאמת." },
  { icon: "shield", t: "אבטחה מלאה", d: "Row-Level Security פר-ארגון. הנתונים שלכם נראים רק לכם." },
  { icon: "flag", t: "מותאם לישראל", d: "חגים, אירועים ביטחוניים, ופאנל-נושם — נכלל אוטומטית בחיזוי." },
];

const STEPS = [
  { n: "1", t: "הרשמה", d: "מייל וסיסמה, בלי כרטיס אשראי. תוך 30 שניות אתם בפנים." },
  { n: "2", t: "שאלה", d: "בוחרים תוכנית, תאריך ושעה, או שואלים בעברית טבעית בצ'אט." },
  { n: "3", t: "תחזית", d: "רייטינג צפוי, טווח 80% והערכת בתי-אב וצופים, תוך שנייה." },
];

export default function LandingPage() {
  const router = useRouter();

  // אם משתמש כבר מחובר — להעביר לדשבורד
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/dashboard");
    });
  }, [router]);

  return (
    <main className="min-h-dvh bg-white">
      {/* Nav */}
      <nav aria-label="ניווט ראשי" className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-line">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <Link href="/" className="font-bold text-brand-dark tracking-tight" dir="ltr">
            i24 <span className="font-normal text-muted">Ratings Forecast</span>
          </Link>
          <div className="hidden md:flex items-center gap-1 text-sm">
            <a href="/about" className="btn-quiet">אודות</a>
            <a href="/about#stats" className="btn-quiet">מספרים</a>
            <a href="/about#tech" className="btn-quiet">טכנולוגיה</a>
            <a href="/infographic" className="btn-quiet">מקסם למדע</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login" className="btn-quiet text-sm">התחברות</Link>
            <Link href="/login?mode=signup" className="btn-primary text-sm">נסו חינם</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-brand-dark text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 md:py-24 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <p className="text-sm font-bold text-brand-accent-light">חינם ל-14 ימים · בלי כרטיס אשראי</p>
            <h1 className="text-4xl md:text-5xl font-bold leading-tight mt-4">
              תחזיות רייטינג טלוויזיה מבוססות מכונה לומדת
            </h1>
            <p className="text-lg text-white/80 mt-5 max-w-xl leading-relaxed">
              הפסיקו לנחש. חזו רייטינג של תוכניות עד <strong className="text-white">6 חודשים קדימה</strong>,
              עם רווח-ביטחון של 80%. מודל שאומן על 10,000 שידורים אמיתיים של i24 NEWS.
            </p>
            <div className="flex flex-wrap gap-3 mt-8">
              <Link href="/login?mode=signup" className="btn bg-white text-brand-dark hover:bg-slate-100 text-base px-6">
                נסו חינם 14 יום
                <Icon name="arrowLeft" size={18} />
              </Link>
              <Link href="#how-it-works" className="btn border border-white/30 text-white hover:bg-white/10 text-base px-6">
                איך זה עובד?
              </Link>
            </div>
          </div>

          {/* Product preview: the forecast card, as it appears in the app */}
          <div className="card text-ink p-6 max-w-md w-full mx-auto lg:mx-0 lg:justify-self-end" aria-hidden="true">
            <div className="flex items-start justify-between gap-3">
              <span className="text-sm font-medium text-muted">תחזית רייטינג מותאם</span>
              <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full font-bold bg-emerald-50 text-emerald-800">
                <Icon name="trendingUp" size={14} /> <span className="num">0.31</span> מעל הממוצע
              </span>
            </div>
            <div className="text-6xl font-bold text-brand-dark num leading-none mt-2">5.24</div>
            <div className="flex items-baseline justify-between text-xs mt-6 mb-2">
              <span className="text-muted">טווח ביטחון של 80%</span>
              <span className="num font-bold" dir="ltr">3.88 – 6.60</span>
            </div>
            <div dir="ltr" className="relative h-8">
              <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 rounded-full bg-slate-200" />
              <div className="absolute top-1/2 -translate-y-1/2 h-2 rounded-full bg-brand-primary/35" style={{ left: "48%", width: "34%" }} />
              <div className="absolute top-1/2 w-4 h-4 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-dark ring-2 ring-white" style={{ left: "65%" }} />
            </div>
            <p className="text-xs text-muted mt-4">דוגמה להמחשה. קבינט שישי, שידור חי.</p>
          </div>
        </div>

        {/* KPIs */}
        <div className="border-t border-white/10">
          <dl className="max-w-6xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
            {KPIS.map((k) => (
              <div key={k.lbl} className="flex flex-col-reverse">
                <dt className="text-sm text-white/70 mt-1">{k.lbl}</dt>
                <dd className="text-3xl font-bold num">{k.n}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 md:py-20 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl mb-10">
            <p className="eyebrow">יכולות</p>
            <h2 className="text-3xl md:text-4xl font-bold text-brand-dark mt-2">כל מה שצריך כדי לתכנן לוז חכם</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f) => (
              <article key={f.t} className="card p-6">
                <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50 text-brand-primary">
                  <Icon name={f.icon} size={20} />
                </div>
                <h3 className="text-lg font-bold text-brand-dark mt-4">{f.t}</h3>
                <p className="text-muted leading-relaxed mt-1.5">{f.d}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-16 md:py-20 px-4 sm:px-6 bg-canvas border-y border-line scroll-mt-16">
        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl mb-10">
            <p className="eyebrow">3 צעדים</p>
            <h2 className="text-3xl md:text-4xl font-bold text-brand-dark mt-2">איך זה עובד?</h2>
          </div>
          <ol className="grid md:grid-cols-3 gap-5">
            {STEPS.map((s) => (
              <li key={s.n} className="card p-6">
                <div className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-brand-dark text-white font-bold num">
                  {s.n}
                </div>
                <h3 className="text-lg font-bold text-brand-dark mt-4">{s.t}</h3>
                <p className="text-muted leading-relaxed mt-1.5">{s.d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-16 md:py-20 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl mb-10">
            <p className="eyebrow">תמחור</p>
            <h2 className="text-3xl md:text-4xl font-bold text-brand-dark mt-2">פשוט. הוגן.</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-5 items-start">
            <PriceCard
              tier="Trial"
              price="חינם"
              sub="14 יום ראשונים"
              features={["גישה מלאה ל-Pro", "תחזיות ללא הגבלה", "צ'אט + היסטוריה", "בלי כרטיס אשראי"]}
              cta="התחילו עכשיו"
              ctaHref="/login?mode=signup"
            />
            <PriceCard
              tier="Pro"
              price="₪990"
              sub="לחודש · ביטול בכל עת"
              features={["כל מה שיש ב-Trial", "ללא הגבלות אחרי 14 יום", "אנליטיקה מתקדמת", "תמיכה במייל"]}
              cta="התחילו עם Trial"
              ctaHref="/login?mode=signup"
              highlight
            />
            <PriceCard
              tier="Enterprise"
              price="מותאם"
              sub="לערוצים וסוכנויות גדולות"
              features={["API גישה לאינטגרציה", "מודל מותאם לערוץ", "SLA · ההדרכה", "Setup חד-פעמי"]}
              cta="דברו איתנו"
              ctaHref="mailto:contact@example.com?subject=Enterprise%20Inquiry"
            />
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-4 sm:px-6 pb-16 md:pb-20">
        <div className="max-w-6xl mx-auto bg-brand-dark text-white rounded-2xl px-6 py-12 md:py-14 text-center">
          <h2 className="text-3xl md:text-4xl font-bold">הפסיקו לנחש. התחילו לחזות.</h2>
          <p className="text-lg text-white/80 mt-3">14 יום חינם. בלי כרטיס אשראי. בלי התחייבות.</p>
          <Link href="/login?mode=signup" className="btn bg-white text-brand-dark hover:bg-slate-100 text-base px-8 mt-7">
            נסו חינם
            <Icon name="arrowLeft" size={18} />
          </Link>
        </div>
      </section>
    </main>
  );
}

function PriceCard({
  tier, price, sub, features, cta, ctaHref, highlight,
}: {
  tier: string; price: string; sub: string; features: string[];
  cta: string; ctaHref: string; highlight?: boolean;
}) {
  return (
    <article className={`card p-6 ${highlight ? "border-2 border-brand-primary shadow-card-hover" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-brand-primary">{tier}</h3>
        {highlight && (
          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-50 text-brand-primary">מומלץ</span>
        )}
      </div>
      <div className="text-4xl font-bold text-brand-dark num mt-3">{price}</div>
      <div className="text-sm text-muted mt-1">{sub}</div>
      <ul className="space-y-2.5 my-6 text-sm">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <Icon name="check" size={16} className="text-brand-primary mt-0.5" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <Link href={ctaHref} className={`w-full ${highlight ? "btn-primary" : "btn-secondary"}`}>
        {cta}
      </Link>
    </article>
  );
}
