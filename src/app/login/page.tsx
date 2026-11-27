import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getSessionUser } from "@/lib/sso/session";
import { safeReturnTo } from "@/lib/return-to";

export const metadata: Metadata = { title: "Masuk", description: "Masuk ke MySuka dengan akun Google UIN Sunan Kalijaga.", alternates: { canonical: "/login" } };

const ERRORS: Record<string, string> = {
  denied: "Masuk gagal. Gunakan akun Google resmi UIN Sunan Kalijaga.",
  state: "Sesi masuk kedaluwarsa. Silakan coba lagi.",
  invalid: "Permintaan masuk tidak valid. Silakan coba lagi.",
  config: "Layanan masuk belum dikonfigurasi.",
  ratelimit: "Terlalu banyak percobaan masuk. Tunggu sebentar lalu coba lagi.",
  unavailable: "Layanan masuk sementara tidak tersedia. Silakan coba lagi sebentar lagi.",
  idle: "Sesi berakhir karena tidak ada aktivitas. Silakan masuk lagi.",
};

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string; returnTo?: string }> }) {
  const { error, returnTo } = await searchParams;
  const target = safeReturnTo(returnTo);
  if (await getSessionUser()) redirect(target);
  const message = error ? ERRORS[error] : undefined;
  return (
    <>
      <main id="konten" className="login-page">
        <section className="login-card" aria-labelledby="login-title">
          <span className="login-emblem" aria-hidden="true">✦</span>
          <p className="login-eyebrow">PORTAL TERPADU UIN SUNAN KALIJAGA</p>
          <h1 id="login-title">Masuk ke <span>MySuka</span></h1>
          <p className="login-description">Gunakan akun Google resmi UIN Sunan Kalijaga untuk mengakses seluruh layanan digital kampus.</p>
          {message && <p role="alert" className="login-alert">{message}</p>}
          <a className="login-submit" href={`/api/sso/login?returnTo=${encodeURIComponent(target)}`}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21.6 12.23c0-.72-.06-1.25-.19-1.8H12v3.27h5.52a4.72 4.72 0 0 1-2.05 3.1v2.12h3.32c1.94-1.79 2.81-4.42 2.81-6.69Z"/><path fill="currentColor" d="M12 22c2.7 0 4.97-.9 6.63-2.45l-3.32-2.12c-.92.62-2.1.99-3.31.99-2.55 0-4.72-1.72-5.5-4.03H3.07v2.19A10 10 0 0 0 12 22Z"/><path fill="currentColor" d="M6.5 14.39A6.02 6.02 0 0 1 6.18 12c0-.83.14-1.64.32-2.39V7.42H3.07A10 10 0 0 0 2 12c0 1.65.4 3.2 1.07 4.58l3.43-2.19Z"/><path fill="currentColor" d="M12 5.58c1.47 0 2.78.5 3.82 1.5l2.86-2.86A9.57 9.57 0 0 0 12 2a10 10 0 0 0-8.93 5.42L6.5 9.61c.78-2.31 2.95-4.03 5.5-4.03Z"/></svg>
            Masuk dengan akun Google UIN
            <span aria-hidden="true">→</span>
          </a>
          <p className="login-note">Akses aman melalui Single Sign-On (SSO)</p>
        </section>
      </main>
    </>
  );
}
