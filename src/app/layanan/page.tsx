import type { Metadata } from "next";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import ServiceCard from "@/components/ServiceCard";
import { SERVICES } from "@/lib/services";

export const metadata: Metadata = {
  title: "Layanan",
  description: "Daftar layanan digital UIN Sunan Kalijaga: SukaKetemu, CampusFix, SISKA, Archive, dan PaaS Praktikum.",
  alternates: { canonical: "/layanan" },
};

export default function LayananPage() {
  return (
    <>
      <SiteHeader active="layanan" />
      <main id="konten" className="section">
        <div className="container">
          <h1 className="section-title">Layanan kampus</h1>
          <p className="section-lead">Pilih layanan yang Anda butuhkan. Masuk satu kali, berpindah layanan tanpa login ulang.</p>
          <ul className="card-grid">{SERVICES.map((s, i) => <ServiceCard key={s.id} service={s} index={i} />)}</ul>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
