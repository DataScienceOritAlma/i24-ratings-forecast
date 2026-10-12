"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Icon, { type IconName } from "@/components/Icon";

interface Props {
  email: string | null;
  title?: string;
}

const NAV: { href: string; label: string; key: string; icon: IconName; external?: boolean }[] = [
  { href: "/dashboard", label: "חיזוי", key: "dashboard", icon: "target" },
  { href: "/chat", label: "שאלה חופשית", key: "chat", icon: "message" },
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
            i24 <span className="hidden sm:inline font-normal text-white/70">Ratings Forecast</span>
          </Link>

          <nav aria-label="ניווט ראשי" className="flex items-center gap-1 text-sm">
            {NAV.map((item) => {
              const active = pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              const cls = `inline-flex items-center gap-2 min-h-[44px] px-3 rounded-lg transition-colors duration-150 ${
                active ? "bg-white/15 font-bold" : "text-white/80 hover:bg-white/10 hover:text-white"
              }`;
              const inner = (
                <>
                  <Icon name={item.icon} size={18} />
                  <span>{item.label}</span>
                </>
              );
              return item.external ? (
                <a key={item.key} href={item.href} className={cls}>{inner}</a>
              ) : (
                <Link
                  key={item.key}
                  href={item.href}
                  className={cls}
                  aria-current={active ? "page" : undefined}
                >
                  {inner}
                </Link>
              );
            })}

            <span className="w-px h-6 bg-white/20 mx-2" aria-hidden="true" />

            {email ? (
              <>
                <span className="hidden md:inline text-xs text-white/70 max-w-[180px] truncate" dir="ltr" title={email}>
                  {email}
                </span>
                <button
                  onClick={handleSignOut}
                  aria-label="יציאה"
                  className="inline-flex items-center gap-2 min-h-[44px] px-3 rounded-lg text-white/80 hover:bg-white/10 hover:text-white transition-colors duration-150 cursor-pointer"
                >
                  <Icon name="logOut" size={18} />
                  <span className="hidden sm:inline">יציאה</span>
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
          </nav>
        </div>
      </div>

      <div className="bg-white border-b border-line">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4">
          <h1 className="text-xl font-bold text-brand-dark">{title}</h1>
        </div>
      </div>
    </header>
  );
}
