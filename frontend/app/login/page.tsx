"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Icon from "@/components/Icon";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-muted">טוען...</div>}>
      <LoginInner />
    </Suspense>
  );
}

function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const initialMode = params.get("mode") === "signup" ? "signup" : "signin";
  const [mode, setMode] = useState<"signin" | "signup">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/dashboard");
    });
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      if (mode === "signup") {
        const { error: e1 } = await supabase.auth.signUp({ email, password });
        if (e1) throw e1;
        setNotice("נשלח אליך מייל אישור. לחצי על הקישור שבו, ואז תוכלי להתחבר.");
      } else {
        const { error: e1 } = await supabase.auth.signInWithPassword({ email, password });
        if (e1) throw e1;
        router.replace("/dashboard");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function switchMode(next: "signin" | "signup") {
    setMode(next);
    setError(null);
    setNotice(null);
  }

  return (
    <main className="min-h-dvh flex items-center justify-center p-4 sm:p-6 bg-canvas">
      <div className="w-full max-w-md">
        <Link href="/" className="btn-quiet text-sm mb-4">
          <Icon name="arrowLeft" size={16} className="rotate-180" />
          חזרה לדף הבית
        </Link>

        <div className="card p-6 sm:p-8">
          <header className="mb-6">
            <div className="font-bold text-brand-dark tracking-tight" dir="ltr">
              i24 <span className="font-normal text-muted">Ratings Forecast</span>
            </div>
            <h1 className="text-2xl font-bold text-brand-dark mt-4">
              {mode === "signup" ? "יצירת חשבון" : "התחברות"}
            </h1>
            <p className="text-sm text-muted mt-1">
              {mode === "signup"
                ? "14 יום חינם, בלי כרטיס אשראי."
                : "ברוכה השבה."}
            </p>
          </header>

          <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 rounded-lg mb-6" role="tablist" aria-label="סוג הכניסה">
            {([["signin", "התחברות"], ["signup", "הרשמה"]] as const).map(([value, label]) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={mode === value}
                onClick={() => switchMode(value)}
                className={`min-h-[40px] rounded-md font-bold text-sm transition-colors duration-150 cursor-pointer ${
                  mode === value ? "bg-white text-brand-dark shadow-card" : "text-muted hover:text-brand-dark"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="label">אימייל</label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="field text-left"
                dir="ltr"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="label">סיסמה</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={6}
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field text-left pe-16"
                  dir="ltr"
                  aria-describedby="password-help"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-pressed={showPassword}
                  className="absolute inset-y-0 right-0 px-3 text-xs font-bold text-brand-primary hover:text-brand-dark cursor-pointer"
                >
                  {showPassword ? "הסתרה" : "הצגה"}
                </button>
              </div>
              <p id="password-help" className="text-xs text-muted mt-1.5">לפחות 6 תווים.</p>
            </div>

            {error && (
              <div className="flex gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800" role="alert">
                <Icon name="alert" size={18} />
                <span className="break-words">{error}</span>
              </div>
            )}
            {notice && (
              <div className="flex gap-2 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-900" role="status">
                <Icon name="check" size={18} />
                <span>{notice}</span>
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  רגע...
                </>
              ) : mode === "signin" ? "התחברות" : "יצירת חשבון"}
            </button>
          </form>

          {mode === "signup" && (
            <p className="text-xs text-muted text-center mt-4 leading-relaxed">
              ביצירת חשבון את מסכימה ל
              <Link href="/terms" className="text-brand-primary underline underline-offset-2 hover:text-brand-dark">תנאי השימוש</Link>
              {" "}ול
              <Link href="/privacy" className="text-brand-primary underline underline-offset-2 hover:text-brand-dark">מדיניות הפרטיות</Link>.
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
