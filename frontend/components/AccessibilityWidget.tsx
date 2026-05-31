"use client";

// Accessibility widget — fulfills תקנות שוויון זכויות (תשע"ג-2013) requirement
// for an always-visible accessibility control. Toggles classes on <html>; the
// actual CSS lives in globals.css. Settings persist in localStorage.

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

type FontSize = 0 | 1 | 2 | 3;
type Contrast = "" | "high" | "inverse";

interface Settings {
  fontSize: FontSize;
  contrast: Contrast;
  links: boolean;
  noAnim: boolean;
}

const STORAGE_KEY = "i24-a11y";
const DEFAULT: Settings = { fontSize: 0, contrast: "", links: false, noAnim: false };

function applyToHtml(s: Settings) {
  const r = document.documentElement;
  // Font
  r.classList.remove("a11y-font-1", "a11y-font-2", "a11y-font-3");
  if (s.fontSize > 0) r.classList.add(`a11y-font-${s.fontSize}`);
  // Contrast
  r.classList.remove("a11y-contrast-high", "a11y-contrast-inverse");
  if (s.contrast) r.classList.add(`a11y-contrast-${s.contrast}`);
  // Links
  r.classList.toggle("a11y-links", s.links);
  // Animations
  r.classList.toggle("a11y-no-anim", s.noAnim);
}

export default function AccessibilityWidget() {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState<Settings>(DEFAULT);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Load from localStorage on mount, then apply.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const loaded: Settings = raw ? { ...DEFAULT, ...JSON.parse(raw) } : DEFAULT;
      setSettings(loaded);
      applyToHtml(loaded);
    } catch {
      applyToHtml(DEFAULT);
    }
  }, []);

  // Persist + apply on every change after first mount.
  const update = useCallback((next: Partial<Settings>) => {
    setSettings((prev) => {
      const merged = { ...prev, ...next };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      } catch {}
      applyToHtml(merged);
      return merged;
    });
  }, []);

  const reset = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
    setSettings(DEFAULT);
    applyToHtml(DEFAULT);
  }, []);

  // Close on Escape; trap focus to first option when opening.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const firstBtn = panelRef.current?.querySelector<HTMLElement>("button");
    firstBtn?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="a11y-widget" dir="rtl">
      {/* Floating button — international wheelchair symbol (rendered as SVG so it
          shows up identically on every OS, not as the inconsistent ♿ Unicode glyph) */}
      <button
        ref={buttonRef}
        type="button"
        aria-label="פתיחת תפריט נגישות"
        aria-expanded={open}
        aria-controls="a11y-panel"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 left-5 z-[300] w-14 h-14 rounded-full bg-brand-primary hover:bg-brand-dark text-white shadow-lg shadow-brand-primary/40 flex items-center justify-center ring-2 ring-white/40"
        title="נגישות"
      >
        <svg
          viewBox="0 0 24 24"
          width="28"
          height="28"
          fill="currentColor"
          aria-hidden="true"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Head */}
          <circle cx="12" cy="3.5" r="1.75" />
          {/* Torso + arms reaching wheelchair */}
          <path d="M16.5 14h-3.4l-1.05-2.65L13 9.7V8.3l-2.5-1.45a1.5 1.5 0 0 0-2.2 1.85L9.8 13.4a1.5 1.5 0 0 0 1.4.9h4.05l1.05 4.05a1 1 0 0 0 1.94-.5L17.5 14.5A.6.6 0 0 0 16.5 14Z" />
          {/* Wheelchair wheel */}
          <circle cx="10.5" cy="17.5" r="4" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <circle cx="10.5" cy="17.5" r="0.9" />
        </svg>
      </button>

      {/* Panel */}
      {open && (
        <div
          ref={panelRef}
          id="a11y-panel"
          role="dialog"
          aria-modal="false"
          aria-label="תפריט נגישות"
          className="fixed bottom-20 left-5 z-[300] w-[300px] max-w-[calc(100vw-2.5rem)] rounded-2xl bg-white shadow-2xl border border-slate-200 p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-black text-brand-dark">תפריט נגישות</h2>
            <button
              type="button"
              aria-label="סגירה"
              onClick={() => { setOpen(false); buttonRef.current?.focus(); }}
              className="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-500 text-xl leading-none"
            >
              ✕
            </button>
          </div>

          {/* Font size */}
          <fieldset className="mb-4">
            <legend className="text-sm font-bold text-ink mb-2">גודל גופן</legend>
            <div className="grid grid-cols-4 gap-1.5">
              {([0, 1, 2, 3] as FontSize[]).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => update({ fontSize: n })}
                  aria-pressed={settings.fontSize === n}
                  className={`py-2 rounded-lg text-sm font-bold border transition ${
                    settings.fontSize === n
                      ? "bg-brand-primary text-white border-brand-primary"
                      : "bg-white text-ink border-slate-200 hover:border-brand-primary"
                  }`}
                >
                  {n === 0 ? "רגיל" : "א".repeat(1) + (n > 1 ? "+".repeat(n - 1) : "+")}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Contrast */}
          <fieldset className="mb-4">
            <legend className="text-sm font-bold text-ink mb-2">ניגודיות</legend>
            <div className="grid grid-cols-3 gap-1.5">
              {([
                { v: "" as Contrast, label: "רגיל" },
                { v: "high" as Contrast, label: "גבוהה" },
                { v: "inverse" as Contrast, label: "הפוך" },
              ]).map((opt) => (
                <button
                  key={opt.v || "off"}
                  type="button"
                  onClick={() => update({ contrast: opt.v })}
                  aria-pressed={settings.contrast === opt.v}
                  className={`py-2 rounded-lg text-sm font-bold border transition ${
                    settings.contrast === opt.v
                      ? "bg-brand-primary text-white border-brand-primary"
                      : "bg-white text-ink border-slate-200 hover:border-brand-primary"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Toggles */}
          <div className="space-y-2 mb-4">
            <label className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 cursor-pointer">
              <span className="text-sm font-bold text-ink">הדגשת קישורים</span>
              <input
                type="checkbox"
                checked={settings.links}
                onChange={(e) => update({ links: e.target.checked })}
                className="w-5 h-5 accent-brand-primary cursor-pointer"
              />
            </label>
            <label className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 cursor-pointer">
              <span className="text-sm font-bold text-ink">השהיית אנימציות</span>
              <input
                type="checkbox"
                checked={settings.noAnim}
                onChange={(e) => update({ noAnim: e.target.checked })}
                className="w-5 h-5 accent-brand-primary cursor-pointer"
              />
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between gap-2 pt-3 border-t border-slate-200">
            <button
              type="button"
              onClick={reset}
              className="text-sm text-muted hover:text-brand-dark underline"
            >
              איפוס
            </button>
            <Link
              href="/accessibility"
              onClick={() => setOpen(false)}
              className="text-sm text-brand-primary hover:text-brand-dark font-bold"
            >
              הצהרת נגישות ←
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
