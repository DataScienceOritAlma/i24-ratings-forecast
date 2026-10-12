import type { Metadata } from "next";
import { Heebo } from "next/font/google";
import "./globals.css";
import Footer from "@/components/Footer";
import AccessibilityWidget from "@/components/AccessibilityWidget";

const heebo = Heebo({
  subsets: ["latin", "hebrew"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-heebo",
});

export const metadata: Metadata = {
  title: {
    default: "i24 Ratings Forecast — תחזיות רייטינג מבוססות AI",
    template: "%s · i24 Ratings Forecast",
  },
  description: "תחזית רייטינג לשידור הבא, עם טווח ביטחון של 80% והערכת בתי אב וצופים. מודל שפותח על שידורים אמיתיים של i24 NEWS.",
  keywords: ["רייטינג", "תחזית רייטינג", "i24", "machine learning", "תכנון לוז", "tv ratings forecast", "ניבוי צופים"],
  authors: [{ name: "אורית עלמה זיו-נר" }],
  creator: "אורית עלמה זיו-נר",
  openGraph: {
    type: "website",
    locale: "he_IL",
    title: "i24 Ratings Forecast — תחזיות רייטינג מבוססות AI",
    description: "תחזית רייטינג עם טווח ביטחון של 80% · 14 יום חינם",
    siteName: "i24 Ratings Forecast",
  },
  twitter: {
    card: "summary_large_image",
    title: "i24 Ratings Forecast",
    description: "תחזיות רייטינג טלוויזיה מבוססות מכונה לומדת",
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={heebo.variable}>
      <body className="font-sans antialiased min-h-screen flex flex-col">
        <div className="flex-1">{children}</div>
        <Footer />
        <AccessibilityWidget />
      </body>
    </html>
  );
}
