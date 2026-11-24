import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";

const jakarta = localFont({
  src: "./fonts/PlusJakartaSans-latin.woff2",
  weight: "200 800",
  display: "swap",
  variable: "--font-jakarta",
  fallback: ["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
});

const siteUrl = (process.env.APP_BASE_URL ?? "http://localhost:3000").replace(/\/+$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "MySuka — Satu Ruang Digital untuk Civitas Akademika UIN Sunan Kalijaga", template: "%s | MySuka" },
  description: "Portal layanan digital UIN Sunan Kalijaga: SukaKetemu, CampusFix, SISKA, Archive, dan PaaS Praktikum dengan satu akun.",
  applicationName: "MySuka",
  alternates: { canonical: "/" },
  openGraph: { type: "website", locale: "id_ID", siteName: "MySuka", url: "/", title: "MySuka — Satu Ruang Digital untuk Civitas Akademika", description: "Semua kebutuhan kampus, satu ruang." },
  twitter: { card: "summary", title: "MySuka", description: "Semua kebutuhan kampus, satu ruang." },
};

export const viewport: Viewport = { themeColor: "#155E38", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id" className={jakarta.variable}>
      <body>
        <a className="skip-link" href="#konten">Lewati ke konten utama</a>
        {children}
      </body>
    </html>
  );
}
