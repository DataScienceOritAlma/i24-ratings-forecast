import type { Metadata } from "next";
import { Heebo } from "next/font/google";
import "./globals.css";
import Footer from "@/components/Footer";

const heebo = Heebo({
  subsets: ["latin", "hebrew"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-heebo",
});

export const metadata: Metadata = {
  title: "i24 Ratings Forecast",
  description: "ניבוי רייטינג של תוכניות i24 NEWS — חיזוי מבוסס מכונה לומדת",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={heebo.variable}>
      <body className="font-sans antialiased min-h-screen flex flex-col">
        <div className="flex-1">{children}</div>
        <Footer />
      </body>
    </html>
  );
}
