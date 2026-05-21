import Link from "next/link";

export const metadata = { title: "תנאי שימוש | i24 Ratings Forecast" };

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-white">
      <header className="bg-gradient-to-br from-brand-dark to-brand-primary text-white py-8">
        <div className="max-w-3xl mx-auto px-6">
          <Link href="/" className="text-sm opacity-80 hover:opacity-100">← דף הבית</Link>
          <h1 className="text-3xl font-black mt-3">תנאי שימוש</h1>
          <p className="text-sm opacity-80 mt-1">עודכן לאחרונה: 2026-05-21</p>
        </div>
      </header>

      <article className="max-w-3xl mx-auto px-6 py-10 prose prose-slate text-base leading-relaxed space-y-6">
        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">1. ברוכים הבאים</h2>
          <p>
            i24 Ratings Forecast (להלן: <strong>&quot;השירות&quot;</strong>) הוא כלי לחיזוי רייטינג של תוכניות
            טלוויזיה בשוק הישראלי, מבוסס למידת-מכונה. השירות מסופק על-ידי אורית עלמה זיו-נר,
            עוסק פטור (להלן: <strong>&quot;ספק השירות&quot;</strong>).
          </p>
          <p className="mt-2">
            השימוש בשירות מהווה הסכמה לתנאים הבאים. אם אינך מסכים — אנא הימנע מהשימוש.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">2. רישום וחשבון</h2>
          <ul className="list-disc pr-6 space-y-1">
            <li>הרישום פתוח רק לארגונים עסקיים (סוכנויות מדיה, ערוצים, יחידות מחקר).</li>
            <li>אתה אחראי לסיסמה שלך ולשמירה על אבטחתה.</li>
            <li>אסור לשתף את חשבונך עם משתמשים אחרים מחוץ לארגון.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">3. תשלום ומנויים</h2>
          <ul className="list-disc pr-6 space-y-1">
            <li>תקופת ניסיון של 14 יום מוצעת ללא חיוב. אפשר לבטל בכל רגע.</li>
            <li>אחרי תקופת הניסיון, יחויב כרטיס האשראי בסכום של 990 ש&quot;ח לחודש, אלא אם בוטל המנוי.</li>
            <li>חיובים מתבצעים דרך Stripe ומאובטחים בתקני PCI-DSS.</li>
            <li>אין החזרים על תשלומים שכבר חויבו. ביטול מנוי מונע את החיוב הבא.</li>
            <li>חשבונית מס/קבלה תישלח במייל לאחר כל חיוב.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">4. תחזיות והגבלת אחריות</h2>
          <p>
            התחזיות המופקות הן <strong>הערכות סטטיסטיות</strong> המבוססות על מודל מכונה לומדת.
            כל תחזית מלווה ברווח-ביטחון של 80%.
          </p>
          <p className="mt-2">
            <strong>אנו לא אחראים</strong> להחלטות עסקיות שיתקבלו על בסיס התחזיות. אירועי
            ברייקינג ביטחוניים, שינויי לוז פתאומיים, או שינויים בפאנל המדידה — עלולים לגרום
            לחיזויים בלתי מדויקים. השירות הוא <strong>כלי עזר</strong>, לא תחליף לשיקול דעת מקצועי.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">5. שימוש מותר ואסור</h2>
          <ul className="list-disc pr-6 space-y-1">
            <li><strong>מותר:</strong> שימוש פנימי בארגונך לתכנון תוכניות עבודה, החלטות שיבוץ, הערכת תקציבים.</li>
            <li><strong>אסור:</strong> מכירה מחדש של התחזיות, שימוש בהנדסה הפוכה, או פגיעה בשירות.</li>
            <li><strong>אסור:</strong> שימוש לרעה — סקרייפינג אוטומטי, יצירת חשבונות מזויפים, או הפרת זכויות יוצרים.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">6. שינויים ועדכונים</h2>
          <p>
            ספק השירות שומר לעצמו את הזכות לעדכן את התנאים. עדכונים מהותיים יישלחו במייל
            ולמשתמשים תינתן תקופה של 30 יום לבטל את המנוי אם אינם מסכימים.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-black text-brand-dark mb-2">7. סמכות שיפוט</h2>
          <p>
            ההסכם כפוף לחוק הישראלי. סמכות שיפוט בלעדית — בתי המשפט בתל אביב-יפו.
          </p>
        </section>

        <section className="border-t pt-6 text-sm text-muted">
          <p>שאלות? צרו קשר ב-<a href="https://github.com/DataScienceOritAlma/i24-ratings-forecast/issues" className="text-brand-primary underline">GitHub Issues</a> או דרך דף ה-<Link href="/account" className="text-brand-primary underline">חשבון</Link>.</p>
        </section>
      </article>
    </main>
  );
}
