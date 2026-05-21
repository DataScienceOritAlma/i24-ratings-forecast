import Link from "next/link";

export const metadata = { title: "מדיניות פרטיות | i24 Ratings Forecast" };

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-white">
      <header className="bg-gradient-to-br from-brand-dark to-brand-primary text-white py-8">
        <div className="max-w-3xl mx-auto px-6">
          <Link href="/" className="text-sm opacity-80 hover:opacity-100">← דף הבית</Link>
          <h1 className="text-3xl font-black mt-3">מדיניות פרטיות</h1>
          <p className="text-sm opacity-80 mt-1">עודכן לאחרונה: 2026-05-21</p>
        </div>
      </header>

      <article className="max-w-3xl mx-auto px-6 py-10 text-base leading-relaxed space-y-6">
        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">1. אילו נתונים אנחנו אוספים</h2>
          <ul className="list-disc pr-6 space-y-1">
            <li><strong>פרטי התחברות:</strong> מייל וסיסמה (מאוחסנים מוצפנים ב-Supabase Auth).</li>
            <li><strong>נתוני שימוש:</strong> תחזיות שיצרת — שם תוכנית, תאריך, שעה, תרחיש. כדי שתוכלי לראות את ההיסטוריה שלך.</li>
            <li><strong>נתוני חיוב:</strong> פרטי תשלום מנוהלים אצל Stripe (אנחנו לא רואים מספרי כרטיסים).</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">2. מה אנחנו לא אוספים</h2>
          <ul className="list-disc pr-6 space-y-1">
            <li><strong>Cookies של מעקב.</strong> אין לנו Google Analytics, אין Facebook Pixel.</li>
            <li><strong>אין שיתוף עם צדדים שלישיים</strong> מלבד ספקי תשתית (Supabase, Stripe, Vercel, Render) — כולם חתומים על DPA תקני.</li>
            <li><strong>אין פרסום ממוקד.</strong> לעולם לא נמכור או נשכיר את הנתונים שלך.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">3. מי רואה מה</h2>
          <p>
            הדאטא מאובטח עם <strong>Row-Level Security</strong> ברמת מסד הנתונים:
          </p>
          <ul className="list-disc pr-6 space-y-1 mt-2">
            <li>כל ארגון רואה רק את התחזיות של עצמו.</li>
            <li>אורית עלמה זיו-נר (בעלת השירות) יכולה לראות מטא-דאטא בקובץ-לוגים לצורכי תמיכה ושיפור המוצר, אך לא תחזיות פרטיות של ארגונים אחרים.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">4. ספקי תשתית</h2>
          <table className="w-full text-sm border border-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="border p-2 text-right">ספק</th>
                <th className="border p-2 text-right">תפקיד</th>
                <th className="border p-2 text-right">איפה</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border p-2"><strong>Supabase</strong></td>
                <td className="border p-2">מסד נתונים + הזדהות</td>
                <td className="border p-2">פרנקפורט, גרמניה (EU)</td>
              </tr>
              <tr>
                <td className="border p-2"><strong>Stripe</strong></td>
                <td className="border p-2">תשלומים</td>
                <td className="border p-2">ארה&quot;ב + אירופה</td>
              </tr>
              <tr>
                <td className="border p-2"><strong>Vercel</strong></td>
                <td className="border p-2">אירוח Frontend</td>
                <td className="border p-2">CDN גלובלי</td>
              </tr>
              <tr>
                <td className="border p-2"><strong>Render</strong></td>
                <td className="border p-2">אירוח Backend</td>
                <td className="border p-2">פרנקפורט, גרמניה</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">5. הזכויות שלך</h2>
          <ul className="list-disc pr-6 space-y-1">
            <li><strong>גישה:</strong> כל הנתונים שלך זמינים לך באפליקציה.</li>
            <li><strong>תיקון:</strong> אפשר לעדכן פרטים בדף החשבון.</li>
            <li><strong>מחיקה:</strong> פנייה למחיקת חשבון מוחקת תוך 30 יום את כל הנתונים.</li>
            <li><strong>ניידות:</strong> פנייה תספק את כל הנתונים שלך ב-JSON.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">6. נתוני הרייטינג ההיסטוריים</h2>
          <p>
            המודל אומן על נתוני רייטינג היסטוריים של ערוץ i24 NEWS. הנתונים הללו <strong>אינם מכילים מידע אישי</strong>
            של צופים — הם רק מספרים אגרגטיביים על כמה משקי בית צפו בכל תוכנית.
          </p>
        </section>

        <section className="border-t pt-6 text-sm text-muted">
          <p>שאלות לגבי הפרטיות? צרו קשר דרך <a href="https://github.com/DataScienceOritAlma/i24-ratings-forecast/issues" className="text-brand-primary underline">GitHub Issues</a> או דף ה-<Link href="/account" className="text-brand-primary underline">חשבון</Link>.</p>
        </section>
      </article>
    </main>
  );
}
