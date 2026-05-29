"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LandingPage() {
  const router = useRouter();

  // אם משתמש כבר מחובר — להעביר לדשבורד
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/dashboard");
    });
  }, [router]);

  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link href="/" className="font-black text-brand-dark text-lg">
            📺 i24 Forecast
          </Link>
          <div className="hidden md:flex items-center gap-5 text-sm text-muted">
            <a href="/index.html#about" className="hover:text-brand-dark transition">אודות</a>
            <a href="/index.html#stats" className="hover:text-brand-dark transition">מספרים</a>
            <a href="/index.html#tech" className="hover:text-brand-dark transition">טכנולוגיה</a>
            <a href="/infographic.html" className="hover:text-brand-dark transition font-bold">🔮 מקסם למדע</a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-muted hover:text-brand-dark transition px-3 py-2"
            >
              התחברות
            </Link>
            <Link
              href="/login?mode=signup"
              className="text-sm bg-brand-primary hover:bg-brand-dark text-white font-bold px-4 py-2 rounded-lg transition"
            >
              נסה חינם →
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-dark via-brand-primary to-brand-light text-white py-20 px-6 relative overflow-hidden">
        <div className="absolute inset-0 opacity-30" style={{
          background: "radial-gradient(circle at 20% 50%, rgba(255,107,53,0.4) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(74,144,226,0.4) 0%, transparent 50%)"
        }} />
        <div className="max-w-4xl mx-auto text-center relative">
          <div className="inline-block mb-5 px-4 py-1.5 rounded-full bg-white/10 backdrop-blur text-xs font-bold border border-white/20">
            🚀 חינם ל-14 ימים · בלי כרטיס אשראי
          </div>
          <h1 className="text-4xl md:text-6xl font-black mb-5 leading-tight">
            תחזיות רייטינג טלוויזיה
            <br />
            <span className="bg-gradient-to-r from-brand-accent to-orange-300 bg-clip-text text-transparent">
              מבוססות מכונה לומדת
            </span>
          </h1>
          <p className="text-lg md:text-xl text-white/90 mb-8 max-w-2xl mx-auto leading-relaxed">
            הפסיקי לנחש — חזי רייטינג של תוכניות עד <strong>6 חודשים קדימה</strong>,
            עם רווח-ביטחון של 80%. מודל שאומן על 10,000 שידורים אמיתיים של i24 NEWS.
          </p>
          <div className="flex flex-wrap gap-3 justify-center mb-10">
            <Link
              href="/login?mode=signup"
              className="px-8 py-4 rounded-xl bg-brand-accent hover:bg-orange-600 text-white font-bold text-lg transition shadow-lg shadow-brand-accent/30"
            >
              נסה חינם 14 יום ←
            </Link>
            <Link
              href="#how-it-works"
              className="px-8 py-4 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur text-white font-bold text-lg transition border border-white/20"
            >
              איך זה עובד?
            </Link>
          </div>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
            {[
              { n: "0.263", lbl: "MAE — דיוק" },
              { n: "60%", lbl: "R² · השונות מוסברת" },
              { n: "19", lbl: "מודלים בהשוואה" },
              { n: "10K", lbl: "שידורים באימון" },
            ].map((k) => (
              <div key={k.lbl} className="bg-white/10 backdrop-blur rounded-2xl p-4 border border-white/10">
                <div className="text-3xl font-black tabular-nums">{k.n}</div>
                <div className="text-xs opacity-80 mt-1">{k.lbl}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <div className="text-xs font-bold text-brand-primary mb-2">פיצ&apos;רים</div>
            <h2 className="text-3xl md:text-4xl font-black text-brand-dark">כל מה שצריך כדי לתכנן לוז חכם</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { i: "🎯", t: "חיזוי מדויק", d: "MAE של 0.263 — טעות ממוצעת של פחות מ-7,000 בתי-אב. נבחר מתוך 19 מודלים שהושוו." },
              { i: "💬", t: "צ'אט בעברית טבעית", d: "שאלי 'מה הצפי לקבינט שישי בשישי הבא?' וקבלי תשובה מפורטת + רווח ביטחון." },
              { i: "📚", t: "היסטוריית תחזיות", d: "כל תחזית נשמרת. תראי אילו צדקת ואיפה — שקיפות מלאה של המודל." },
              { i: "📊", t: "אנליטיקה מתקדמת", d: "ביצועי מודל לפי סטטוס · זיהוי drift · 57% מהתחזיות בטווח ±0.2 מהאמת." },
              { i: "🔐", t: "אבטחה מלאה", d: "Row-Level Security פר-ארגון. הנתונים שלך נראים רק לך." },
              { i: "🇮🇱", t: "מותאם לישראל", d: "חגים, אירועים ביטחוניים, ופאנל-נושם — נכלל אוטומטית בחיזוי." },
            ].map((f) => (
              <article key={f.t} className="bg-slate-50 rounded-2xl p-6 hover:shadow-card transition">
                <div className="text-3xl mb-3">{f.i}</div>
                <h3 className="text-lg font-black text-brand-dark mb-2">{f.t}</h3>
                <p className="text-muted leading-relaxed">{f.d}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-20 px-6 bg-slate-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <div className="text-xs font-bold text-brand-primary mb-2">3 צעדים</div>
            <h2 className="text-3xl md:text-4xl font-black text-brand-dark">איך זה עובד?</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { n: "1", t: "הרשמה", d: "מייל + סיסמה. בלי כרטיס אשראי. תוך 30 שניות אתם בפנים." },
              { n: "2", t: "שאלה", d: "בחרו תוכנית, תאריך, ושעה. או שאלו בעברית טבעית בצ'אט." },
              { n: "3", t: "תחזית", d: "רייטינג צפוי + טווח 80% + הערכת בתי-אב וצופים — תוך שנייה." },
            ].map((s) => (
              <div key={s.n} className="bg-white rounded-2xl p-6 shadow-card text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-brand-primary text-white font-black text-xl mb-4">
                  {s.n}
                </div>
                <h3 className="text-lg font-black text-brand-dark mb-2">{s.t}</h3>
                <p className="text-muted">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <div className="text-xs font-bold text-brand-primary mb-2">תמחור</div>
            <h2 className="text-3xl md:text-4xl font-black text-brand-dark">פשוט. הוגן.</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <PriceCard
              tier="Trial"
              price="חינם"
              sub="14 יום ראשונים"
              features={["גישה מלאה ל-Pro", "תחזיות ללא הגבלה", "צ'אט + היסטוריה", "בלי כרטיס אשראי"]}
              cta="התחילי עכשיו"
              ctaHref="/login?mode=signup"
            />
            <PriceCard
              tier="Pro"
              price="₪990"
              sub="לחודש · ביטול בכל עת"
              features={["כל מה שיש ב-Trial", "ללא הגבלות אחרי 14 יום", "אנליטיקה מתקדמת", "תמיכה במייל"]}
              cta="התחילי עם Trial"
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
      <section className="py-20 px-6 bg-gradient-to-br from-brand-dark to-brand-primary text-white text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-black mb-4">
            הפסיקו לנחש. התחילו לחזות.
          </h2>
          <p className="text-lg opacity-90 mb-8">
            14 יום חינם. בלי כרטיס אשראי. בלי התחייבות.
          </p>
          <Link
            href="/login?mode=signup"
            className="inline-block px-10 py-4 rounded-xl bg-brand-accent hover:bg-orange-600 text-white font-bold text-lg transition shadow-2xl"
          >
            נסה חינם ←
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
    <article
      className={`rounded-2xl p-6 ${
        highlight
          ? "bg-gradient-to-br from-brand-dark to-brand-primary text-white shadow-2xl scale-105"
          : "bg-slate-50 text-ink"
      }`}
    >
      <div className={`text-sm font-bold ${highlight ? "text-brand-accent" : "text-brand-primary"} mb-2`}>
        {tier}
      </div>
      <div className="text-4xl font-black mb-1">{price}</div>
      <div className={`text-sm mb-5 ${highlight ? "opacity-80" : "text-muted"}`}>{sub}</div>
      <ul className="space-y-2 mb-6 text-sm">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <span className="text-brand-accent flex-shrink-0">✓</span>
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <Link
        href={ctaHref}
        className={`block text-center py-3 rounded-xl font-bold transition ${
          highlight
            ? "bg-white text-brand-dark hover:bg-slate-100"
            : "bg-brand-primary text-white hover:bg-brand-dark"
        }`}
      >
        {cta}
      </Link>
    </article>
  );
}
