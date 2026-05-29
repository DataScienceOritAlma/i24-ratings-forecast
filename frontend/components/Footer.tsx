import Link from "next/link";

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-slate-200 bg-white">
      <div className="max-w-5xl mx-auto px-6 py-6 flex flex-wrap items-center justify-between gap-3 text-sm">
        <div className="text-muted">
          © {new Date().getFullYear()} · אורית עלמה זיו-נר
        </div>
        <nav className="flex gap-4 text-muted">
          <Link href="/terms" className="hover:text-brand-primary transition">תנאי שימוש</Link>
          <Link href="/privacy" className="hover:text-brand-primary transition">פרטיות</Link>
          <a
            href="https://github.com/DataScienceOritAlma/i24-ratings-forecast"
            target="_blank"
            rel="noopener"
            className="hover:text-brand-primary transition"
          >
            GitHub
          </a>
        </nav>
      </div>
    </footer>
  );
}
