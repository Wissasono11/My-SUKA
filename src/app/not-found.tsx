import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";

export const metadata = { title: "Halaman tidak ditemukan", robots: { index: false } };

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="konten" className="section"><div className="container narrow">
        <h1 className="section-title">Halaman tidak ditemukan</h1>
        <p className="section-lead">Alamat yang Anda buka tidak tersedia.</p>
        <Link className="btn btn-primary" href="/">Kembali ke beranda</Link>
      </div></main>
      <SiteFooter />
    </>
  );
}
