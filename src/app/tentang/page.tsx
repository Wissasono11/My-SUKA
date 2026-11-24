import type { Metadata } from "next";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";

export const metadata: Metadata = {
  title: "Tentang",
  description: "Tentang MySuka, portal terpadu layanan digital civitas akademika UIN Sunan Kalijaga.",
  alternates: { canonical: "/tentang" },
};

export default function TentangPage() {
  return (
    <>
      <SiteHeader active="tentang" />
      <main id="konten" className="section">
        <div className="container prose">
          <h1 className="section-title">Tentang MySuka</h1>
          <p>MySuka adalah portal terpadu yang menghubungkan layanan digital kampus. Setiap layanan tetap berjalan di sistem dan basis datanya sendiri; portal hanya menyediakan pintu masuk, login tunggal, dan ringkasan aktivitas.</p>
          <h2>Privasi</h2>
          <p>Ringkasan aktivitas di beranda hanya memuat data non-sensitif. Layanan SISKA sengaja tidak menampilkan ringkasan apa pun di portal untuk melindungi kerahasiaan penyintas.</p>
          <h2>Masuk dengan akun kampus</h2>
          <p>Masuk memakai akun Google UIN Sunan Kalijaga. Setelah itu Anda dapat membuka layanan lain tanpa mengisi form login lagi.</p>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
