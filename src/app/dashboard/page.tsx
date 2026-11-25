import type { Metadata } from "next";
import { Suspense } from "react";
import { redirect } from "next/navigation";
import DashboardNavbar from "@/components/DashboardNavbar";
import ServiceCard from "@/components/ServiceCard";
import { SERVICES } from "@/lib/services";
import { getSessionUser } from "@/lib/sso/session";
import { loadWidgets } from "@/lib/widgets";

export const metadata: Metadata = { title: "Beranda Saya", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

async function Widgets() {
  const widgets = await loadWidgets();
  return widgets.map((w) => (
    <li className="widget" key={w.app_id}>
      <h3>{SERVICES.find((s) => s.id === w.app_id)?.name ?? w.app_id}</h3>
      <p className="widget-count"><strong>{w.active_count}</strong> {w.count_label}</p>
      {w.badge_label && <p className="badge">{w.badge_label}</p>}
      <ul className="widget-items">{w.recent_items.slice(0, 3).map((i) => <li key={i.id}><span>{i.title}</span><small>{i.subtitle}</small></li>)}</ul>
      <a className="card-link" href={`/api/sso/launch?app=${w.app_id}`}>Buka {SERVICES.find((s) => s.id === w.app_id)?.name}</a>
    </li>
  ));
}

export default async function DashboardPage() {
  const user = await getSessionUser();
  if (!user) redirect("/login?returnTo=%2Fdashboard");
  return (
    <>
      <DashboardNavbar user={user} />
      <main id="konten" className="dashboard-page">
        <div className="dashboard-container">
          <section className="dashboard-welcome" aria-labelledby="dashboard-title">
            <div>
              <p className="dashboard-eyebrow">PORTAL LAYANAN TERPADU UIN SUNAN KALIJAGA</p>
              <h1 id="dashboard-title">Selamat datang, {user.name.split(" ")[0]}.</h1>
              <p>Akses layanan digital kampus dalam satu ruang yang terintegrasi.</p>
            </div>
            <span className="dashboard-welcome-mark" aria-hidden="true">✦</span>
          </section>

          <section className="dashboard-services" aria-labelledby="dashboard-services-title">
            <div className="dashboard-section-heading">
              <div>
                <p className="dashboard-eyebrow">JELAJAHI EKOSISTEM KAMPUS</p>
                <h2 id="dashboard-services-title">Layanan My-SUKA</h2>
                <p>Pilih layanan sesuai kebutuhan Anda. Satu akun untuk mengakses seluruh layanan.</p>
              </div>
              <span className="dashboard-service-count">{SERVICES.length} layanan tersedia</span>
            </div>
            <ul className="dashboard-service-grid">
              {SERVICES.map((service, index) => (
                <ServiceCard key={service.id} service={service} index={index} />
              ))}
            </ul>
          </section>

          <section className="dashboard-information" aria-labelledby="dashboard-information-title">
            <div className="dashboard-section-heading">
              <div>
                <p className="dashboard-eyebrow">INFORMASI PORTAL</p>
                <h2 id="dashboard-information-title">Informasi untuk Anda</h2>
                <p>Kenali fitur dan dukungan yang tersedia di portal My-SUKA.</p>
              </div>
            </div>
            <div className="dashboard-info-grid">
              <article className="dashboard-info-card">
                <span className="dashboard-info-icon" aria-hidden="true">↗</span>
                <h3>Akses terpadu dengan SSO</h3>
                <p>Gunakan satu akun untuk berpindah antar layanan tanpa perlu login berulang kali.</p>
              </article>
              <article className="dashboard-info-card">
                <span className="dashboard-info-icon" aria-hidden="true">▣</span>
                <h3>Dirancang untuk berbagai perangkat</h3>
                <p>My-SUKA dapat diakses melalui desktop, tablet, maupun perangkat seluler.</p>
              </article>
              <article className="dashboard-info-card">
                <span className="dashboard-info-icon" aria-hidden="true">?</span>
                <h3>Butuh bantuan?</h3>
                <p>Hubungi PTIPD UIN Sunan Kalijaga melalui kanal kontak resmi universitas.</p>
                <a href="mailto:humas@uin-suka.ac.id">Hubungi kami <span aria-hidden="true">→</span></a>
              </article>
            </div>
          </section>

          <section className="dashboard-activity" aria-labelledby="dashboard-activity-title">
            <div className="dashboard-section-heading">
              <div>
                <p className="dashboard-eyebrow">PEMBARUAN LAYANAN</p>
                <h2 id="dashboard-activity-title">Ringkasan aktivitas layanan</h2>
                <p>Informasi ringkas dari layanan yang menyediakan widget aktivitas.</p>
              </div>
            </div>
            <ul className="dashboard-widget-grid">
              <Suspense fallback={<li className="widget widget-skeleton" aria-hidden="true" />}><Widgets /></Suspense>
            </ul>
          </section>
        </div>
      </main>
    </>
  );
}
