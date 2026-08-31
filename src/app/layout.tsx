import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "محوّل الكتب إلى Markdown",
  description: "تحويل كتب PDF العربية إلى Markdown عبر Gemini Vision OCR",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <body className="antialiased">{children}</body>
    </html>
  );
}
