"use client";

// /infographic — Same approach as /about: the React NavBar is the single source of
// truth; the heavy body content (23 SVG illustrations + modal) is fetched at runtime
// from the static /infographic.html, the appbar is stripped, and the body is rendered
// via dangerouslySetInnerHTML. The modal/print/top-button JS is re-implemented in
// useEffect after the content is in the DOM (dangerouslySetInnerHTML doesn't execute
// scripts).

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";

export default function InfographicPage() {
  const [email, setEmail] = useState<string | null>(null);
  const [body, setBody] = useState<string>("");

  // Load session + CSS once on mount.
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setEmail(data.session?.user.email ?? null);
    });

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/infographic.css";
    document.head.appendChild(link);

    // Light-theme overrides for pi-header / pi-btn — match the dashboard aesthetic
    // (these used to live as <style> inside the static page's <head>, but we only
    // copy <body> content so we re-inject them here).
    const style = document.createElement("style");
    style.textContent = `
      #infographic-shell .pi-header{background:var(--bg);color:var(--text);padding:32px 0 28px}
      #infographic-shell .pi-header::before{display:none}
      #infographic-shell .pi-title{color:var(--text)}
      #infographic-shell .pi-subtitle{color:var(--text-muted);font-weight:400}
      #infographic-shell .pi-subtitle strong{color:var(--text)}
      #infographic-shell .pi-btn{background:#fff;color:var(--primary-dark);border:1px solid var(--border);box-shadow:none}
      #infographic-shell .pi-btn:hover{background:#fff;border-color:var(--primary);color:var(--primary);transform:translateY(-1px)}
    `;
    document.head.appendChild(style);

    // Fetch the static page, strip out the old appbar/headers/inline scripts,
    // and keep the actual content (pi-header + pi-main + modal + topBtn).
    fetch("/infographic.html")
      .then((r) => r.text())
      .then((html) => {
        const doc = new DOMParser().parseFromString(html, "text/html");
        // Remove the duplicate appbar (we render our own React NavBar above).
        doc.querySelector("header.appbar")?.remove();
        // Remove the static page's auth/modal inline scripts — we run them below.
        doc.querySelectorAll("script").forEach((s) => s.remove());
        setBody(doc.body.innerHTML);
      })
      .catch(() => setBody(""));

    return () => {
      link.remove();
      style.remove();
    };
  }, []);

  // After body is in the DOM, wire up modal, print button, and top-button behaviors.
  useEffect(() => {
    if (!body) return;

    const modal = document.getElementById("modal") as HTMLElement | null;
    const modalBox = document.getElementById("modalBox") as HTMLElement | null;
    const mArt = document.getElementById("mArt") as HTMLElement | null;
    const mTitle = document.getElementById("mTitle") as HTMLElement | null;
    const mBody = document.getElementById("mBody") as HTMLElement | null;
    if (!modal || !modalBox || !mArt || !mTitle || !mBody) return;

    let lastFocus: HTMLElement | null = null;

    function openModal(card: HTMLElement) {
      const svg = card.querySelector(".pi-art svg");
      const detail = card.querySelector(".pi-detail") as HTMLTemplateElement | HTMLElement | null;
      const name = card.querySelector(".pi-name");
      if (!svg || !detail || !name || !modal || !modalBox || !mArt || !mTitle || !mBody) return;
      lastFocus = card;
      modalBox.style.setProperty("--c", card.style.getPropertyValue("--c"));
      mArt.innerHTML = "";
      mArt.appendChild(svg.cloneNode(true));
      mTitle.innerHTML = name.innerHTML;
      mBody.innerHTML = (detail as HTMLElement).innerHTML;
      modal.hidden = false;
      document.body.classList.add("pi-lock");
      document.getElementById("modalX")?.focus();
    }
    function closeModal() {
      if (!modal) return;
      modal.hidden = true;
      document.body.classList.remove("pi-lock");
      lastFocus?.focus();
    }

    const cards = document.querySelectorAll<HTMLElement>(".pi-card");
    const cardClick = (card: HTMLElement) => () => openModal(card);
    const cardKey = (card: HTMLElement) => (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openModal(card); }
    };
    const handlers: Array<[HTMLElement, string, EventListener]> = [];
    cards.forEach((card) => {
      const ck = cardClick(card) as EventListener;
      const kk = cardKey(card) as EventListener;
      card.addEventListener("click", ck);
      card.addEventListener("keydown", kk);
      handlers.push([card, "click", ck], [card, "keydown", kk]);
    });

    const modalClick: EventListener = (e) => {
      const t = e.target as HTMLElement;
      if (t.hasAttribute("data-close")) closeModal();
    };
    modal.addEventListener("click", modalClick);
    const escKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !modal.hidden) closeModal();
    };
    document.addEventListener("keydown", escKey);

    const printBtn = document.getElementById("printBtn");
    const printClick = () => window.print();
    printBtn?.addEventListener("click", printClick);

    const topBtn = document.getElementById("topBtn") as HTMLButtonElement | null;
    const onScroll = () => { if (topBtn) topBtn.hidden = window.scrollY < 600; };
    const topClick = () => window.scrollTo({ top: 0, behavior: "smooth" });
    window.addEventListener("scroll", onScroll, { passive: true });
    topBtn?.addEventListener("click", topClick);

    return () => {
      handlers.forEach(([el, ev, fn]) => el.removeEventListener(ev, fn));
      modal.removeEventListener("click", modalClick);
      document.removeEventListener("keydown", escKey);
      printBtn?.removeEventListener("click", printClick);
      window.removeEventListener("scroll", onScroll);
      topBtn?.removeEventListener("click", topClick);
    };
  }, [body]);

  return (
    <main className="min-h-screen bg-slate-100">
      <NavBar email={email} title="מקסם למדע" />
      {body ? (
        <div id="infographic-shell" dangerouslySetInnerHTML={{ __html: body }} />
      ) : (
        <div className="max-w-6xl mx-auto px-6 py-12 text-center text-muted">טוען…</div>
      )}
    </main>
  );
}
