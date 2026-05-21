import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="text-center max-w-md">
        <div className="text-7xl mb-3">📺</div>
        <h1 className="text-3xl font-black text-brand-dark mb-2">404 — לא נמצא</h1>
        <p className="text-muted mb-6">
          הדף שחיפשת לא קיים. אולי הוא הועבר, או שיש טעות בכתובת.
        </p>
        <Link
          href="/"
          className="inline-block px-5 py-3 rounded-xl bg-brand-primary text-white font-bold hover:bg-brand-dark transition"
        >
          ← חזרה לדף הראשי
        </Link>
      </div>
    </main>
  );
}
