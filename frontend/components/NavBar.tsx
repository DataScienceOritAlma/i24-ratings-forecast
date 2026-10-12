"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Icon, { type IconName } from "@/components/Icon";

interface Props {
  email: string | null;
  title?: string;
}

const NAV: { href: string; label: string; key: string; icon: IconName }[] = [
  { href: "/dashboard", label: "חיזוי", key: "dashboard", icon: "target" },
  { href: "/chat", label: "שאלה", key: "chat", icon: "message" },
  { href: "/history", label: "היסטוריה", key: "history", icon: "history" },
  { href: "/analytics", label: "אנליטיקה", key: "analytics", icon: "chart" },
  { href: "/account", label: "חשבון", key: "account", icon: "user" },
];

export default function NavBar({ email, title = "לוח חיזוי תחזיות" }: Props) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.replace("/");
  }

  return (
    <header>
      <div className="bg-brand-dark text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
          <Link href="/dashboard" className="font-bold tracking-tight whitespace-nowrap" dir="ltr">
            i24 <span className="font-normal text-white/70">Ratings Forecast</span>
          </Link>

          <div className="flex items-center gap-2 text-sm min-w-0">
            {email ? (
              <>
                <span className="hidden md:inline text-xs text-white/70 max-w-[220px] truncate" dir="ltr" title={email}>
                  {email}
                </span>
                <button
                  onClick={handleSignOut}
                  className="inline-flex items-center gap-2 min-h-[44px] px-3 rounded-lg text-white/80 hover:bg-white/10 hover:text-white transition-colors duration-150 cursor-pointer"
                >
                  <Icon name="logOut" size={18} />
                  <span>יציאה</span>
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="inline-flex items-center min-h-[44px] px-3 rounded-lg text-white/80 hover:bg-white/10 hover:text-white transition-colors duration-150"
              >
                התחברות
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white border-b border-line">
        <nav aria-label="ניווט ראשי" className="max-w-6xl mx-auto px-1 sm:px-6 flex sm:gap-1">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.key}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex-1 sm:flex-none flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2 min-h-[52px] px-1 sm:px-4 text-[11px] sm:text-sm border-b-2 transition-colors duration-150 ${
                  active
                    ? "border-brand-primary text-brand-primary font-bold"
                    : "border-transparent text-muted hover:text-brand-dark hover:border-slate-300"
                }`}
              >
                <Icon name={item.icon} size={18} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-6 sm:pt-8">
        <h1 className="text-2xl font-bold text-brand-dark">{title}</h1>
      </div>
    </header>
  );
}
