"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";

// Renders the app's consistent top bar (NavBar) above an embedded showcase page,
// so /about /numbers /technology /infographic feel like part of the app (same nav)
// while preserving the original static design exactly.
export default function EmbedView({ src, title }: { src: string; title: string }) {
  const [email, setEmail] = useState<string | null>(null);
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setEmail(data.session?.user.email ?? null));
  }, []);
  return (
    <main className="h-screen flex flex-col">
      <NavBar email={email} title={title} />
      <iframe src={src} title={title} className="flex-1 w-full border-0" />
    </main>
  );
}
