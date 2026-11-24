import type { Metadata } from "next";
import { redirect } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { getSessionUser } from "@/lib/sso/session";
import { safeReturnTo } from "@/lib/return-to";

export const metadata: Metadata = { title: "Masuk", description: "Masuk ke MySuka dengan akun Google UIN Sunan Kalijaga.", alternates: { canonical: "/login" } };

const ERRORS: Record<string, string> = {
  denied: "Masuk gagal. Gunakan akun Google resmi UIN Sunan Kalijaga.",
  state: "Sesi masuk kedaluwarsa. Silakan coba lagi.",
  invalid: "Permintaan masuk tidak valid. Silakan coba lagi.",
  config: "Layanan masuk belum dikonfigurasi.",
  ratelimit: "Terlalu banyak percobaan masuk. Tunggu sebentar lalu coba lagi.",
};

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string; returnTo?: string }> }) {
  const { error, returnTo } = await searchParams;
  const target = safeReturnTo(returnTo);
  if (await getSessionUser()) redirect(target);
  const message = error ? ERRORS[error] : undefined;
  return (
    <>
      <SiteHeader />
      <main id="konten" className="section">
        <div className="container narrow">
          <h1 className="section-title">Masuk ke MySuka</h1>
          <p className="section-lead">Gunakan akun Google UIN Sunan Kalijaga Anda.</p>
          {message && <p role="alert" className="alert">{message}</p>}
          <a className="btn btn-primary btn-block" href={`/api/sso/login?returnTo=${encodeURIComponent(target)}`}>Masuk dengan akun UIN</a>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
