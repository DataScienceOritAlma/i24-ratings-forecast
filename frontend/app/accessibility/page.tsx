import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "הצהרת נגישות",
  description: "הצהרת נגישות לאתר i24 Ratings Forecast — תאימות WCAG 2.0 AA ו-ת\"י 5568.",
  robots: { index: true, follow: true },
};

export default function AccessibilityPage() {
  return (
    <main className="min-h-screen bg-white">
      <header className="bg-gradient-to-br from-brand-dark to-brand-primary text-white py-8">
        <div className="max-w-3xl mx-auto px-6">
          <Link href="/" className="text-sm opacity-80 hover:opacity-100">← דף הבית</Link>
          <h1 className="text-3xl font-black mt-3">הצהרת נגישות</h1>
          <p className="text-sm opacity-80 mt-1">עודכן לאחרונה: 2026-05-31</p>
        </div>
      </header>

      <article className="max-w-3xl mx-auto px-6 py-10 text-base leading-relaxed">

      <section className="mb-8">
        <h2 className="text-xl font-bold text-brand-dark mb-3">מחויבות לנגישות</h2>
        <p className="text-ink leading-relaxed">
          אנו מאמינים שאתר זה חייב להיות נגיש לכל אדם — כולל אנשים עם מוגבלות.
          אנחנו פועלים מתוך מחויבות לקיום הוראות חוק שוויון זכויות לאנשים עם מוגבלות (1998)
          ותקנותיו (תשע&quot;ג-2013), ולתאימות לתקן הישראלי <strong>ת&quot;י 5568</strong> ברמה AA,
          המבוסס על הנחיות <strong>WCAG 2.0</strong> של W3C.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-brand-dark mb-3">מה האתר מציע</h2>
        <p className="text-ink leading-relaxed mb-3">
          בכל דף באתר זמין <strong>תפריט נגישות</strong> (כפתור עגול בפינה השמאלית התחתונה ♿),
          שמאפשר התאמות אישיות:
        </p>
        <ul className="space-y-2 text-ink">
          <li>📏 <strong>הגדלת גופן</strong> — 3 רמות מעבר לגודל הברירת-מחדל.</li>
          <li>🌗 <strong>ניגודיות מוגברת</strong> — מצב צהוב-על-שחור או מצב הפוך (כהה).</li>
          <li>🔗 <strong>הדגשת קישורים</strong> — מסגרת וקו תחתון בולטים לכל קישור.</li>
          <li>🎬 <strong>השהיית אנימציות</strong> — לשימוש מתאים לאנשים עם רגישות לתנועה.</li>
          <li>↺ <strong>איפוס</strong> — חזרה מהירה לברירת המחדל.</li>
        </ul>
        <p className="text-muted text-sm mt-3 leading-relaxed">
          ההעדפות נשמרות במכשיר שלך באופן מקומי, ומופעלות אוטומטית בכל ביקור חוזר.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-brand-dark mb-3">התאמות שכבר בנויות בקוד</h2>
        <ul className="space-y-2 text-ink">
          <li>✓ <strong>ניווט מקלדת מלא</strong> — כל הפעולות זמינות באמצעות מקלדת (Tab, Enter, Escape).</li>
          <li>✓ <strong>טבעות מיקוד נראות</strong> — מסגרת כחולה בולטת על כל אלמנט אינטראקטיבי שמקבל מיקוד.</li>
          <li>✓ <strong>תיוג סמנטי</strong> — שימוש בתגיות HTML מתאימות (header, nav, main, footer, section).</li>
          <li>✓ <strong>aria-labels</strong> לכפתורים ולחלקים אינטראקטיביים שאינם מכילים טקסט.</li>
          <li>✓ <strong>טקסט חלופי (alt)</strong> לכל התמונות המשמעותיות.</li>
          <li>✓ <strong>תמיכה ב-prefers-reduced-motion</strong> ברמת הדפדפן.</li>
          <li>✓ <strong>RTL מלא</strong> בעברית, כולל כיוון, יישור וניווט.</li>
          <li>✓ <strong>גופן Heebo</strong> בקריאות גבוהה לעברית.</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-brand-dark mb-3">מגבלות ידועות</h2>
        <p className="text-ink leading-relaxed">
          חלק מהוויזואליזציות (תרשימים ואיורי SVG בעמוד &quot;מקסם למדע&quot;) מבוססים על תוכן גרפי
          ועלולים להיות פחות נגישים לקוראי-מסך. אנחנו פועלים לשפר זאת. אם נתקלת בקושי
          ספציפי — אנא צרי קשר ונשמח לסייע.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-brand-dark mb-3">פנייה בנושאי נגישות</h2>
        <p className="text-ink leading-relaxed mb-3">
          אם נתקלת בבעיית נגישות באתר, נשמח לשמוע ולתקן בהקדם.
        </p>
        <ul className="space-y-1 text-ink">
          <li><strong>אחראית נגישות:</strong> אורית עלמה זיו-נר</li>
          <li><strong>דוא&quot;ל:</strong> <a href="mailto:oritdaki@gmail.com" className="text-brand-primary hover:text-brand-dark underline">oritdaki@gmail.com</a></li>
          <li><strong>זמן תגובה משוער:</strong> עד 7 ימי עסקים</li>
        </ul>
      </section>

      <section className="text-sm text-muted leading-relaxed pt-6 border-t border-slate-200">
        <p>
          תקן: ת&quot;י 5568 ברמה AA · WCAG 2.0 · תקנות שוויון זכויות לאנשים עם מוגבלות
          (התאמות נגישות לשירות), תשע&quot;ג-2013.
        </p>
      </section>
      </article>
    </main>
  );
}
