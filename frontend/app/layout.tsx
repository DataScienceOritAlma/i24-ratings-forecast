import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "i24 Ratings Forecast",
  description: "ניבוי רייטינג של תוכניות i24 NEWS — חיזוי מבוסס מכונה לומדת",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
