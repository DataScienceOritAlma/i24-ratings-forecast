"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // אם המשתמש כבר מחובר — לדשבורד
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/dashboard");
    });
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === "signup") {
        const { error: e1 } = await supabase.auth.signUp({ email, password });
        if (e1) throw e1;
        setError("נשלח אליך מייל אישור. אנא לחצי על הקישור בו ותוכלי להתחבר.");
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

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-card p-8">
        <header className="text-center mb-6">
          <div className="text-4xl mb-2">📺</div>
          <h1 className="text-2xl font-black text-brand-dark">i24 Ratings Forecast</h1>
          <p className="text-sm text-muted mt-1">ניבוי רייטינג של תוכניות טלוויזיה</p>
        </header>

        <div className="flex gap-2 p-1 bg-slate-100 rounded-xl mb-6">
          <button
            type="button"
            onClick={() => setMode("signin")}
            className={`flex-1 py-2 rounded-lg font-bold transition ${
              mode === "signin" ? "bg-white text-brand-dark shadow" : "text-muted"
            }`}
          >
            התחברות
          </button>
          <button
            type="button"
            onClick={() => setMode("signup")}
            className={`flex-1 py-2 rounded-lg font-bold transition ${
              mode === "signup" ? "bg-white text-brand-dark shadow" : "text-muted"
            }`}
          >
            הרשמה
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-bold mb-1">אימייל</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-brand-primary focus:outline-none transition"
              dir="ltr"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-bold mb-1">סיסמה</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-brand-primary focus:outline-none transition"
              dir="ltr"
              placeholder="לפחות 6 תווים"
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-brand-primary text-white font-bold hover:bg-brand-dark transition disabled:opacity-50"
          >
            {loading ? "טוען..." : mode === "signin" ? "התחבר/י" : "הרשם/י"}
          </button>
        </form>

        <p className="text-center text-xs text-muted mt-6">
          MVP — הטמעת SaaS Beta · 2026
        </p>
      </div>
    </main>
  );
}
