"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

interface Props {
  email: string | null;
  title?: string;
}

const NAV: { href: string; label: string; key: string; external?: boolean }[] = [
  { href: "/dashboard", label: "🎯 חיזוי", key: "dashboard" },
  { href: "/chat", label: "💬 שאל", key: "chat" },
  { href: "/history", label: "📚 היסטוריה", key: "history" },
  { href: "/analytics", label: "📊 אנליטיקה", key: "analytics" },
  { href: "/index.html#about", label: "אודות", key: "about", external: true },
  { href: "/index.html#stats", label: "מספרים", key: "stats", external: true },
  { href: "/index.html#tech", label: "טכנולוגיה", key: "tech", external: true },
  { href: "/infographic.html", label: "🔮 מקסם למדע", key: "infographic", external: true },
  { href: "/account", label: "👤 חשבון", key: "account" },
];

export default function NavBar({ email, title = "לוח חיזוי תחזיות" }: Props) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.replace("/");
  }

  return (
    <header className="bg-gradient-to-br from-brand-dark to-brand-primary text-white py-5 shadow-lg">
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs opacity-80">i24 Ratings Forecast</div>
          <h1 className="text-xl font-black">{title}</h1>
        </div>
        <nav className="flex items-center gap-1.5 text-sm flex-wrap">
          {NAV.map((item) => {
            const active = pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));
            const cls = `px-3 py-1.5 rounded-lg transition ${
              active ? "bg-white/20 font-bold" : "bg-white/5 hover:bg-white/15"
            }`;
            return item.external ? (
              <a key={item.key} href={item.href} className={cls}>{item.label}</a>
            ) : (
              <Link key={item.key} href={item.href} className={cls}>{item.label}</Link>
            );
          })}
          <span className="opacity-90 mx-2 hidden md:inline text-xs" dir="ltr">
            {email}
          </span>
          <button
            onClick={handleSignOut}
            className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition"
          >
            יציאה
          </button>
        </nav>
      </div>
    </header>
  );
}
