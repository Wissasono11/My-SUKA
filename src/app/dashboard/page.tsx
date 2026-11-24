import type { Metadata } from "next";
import { Suspense } from "react";
import { redirect } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
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
      <SiteHeader />
      <main id="konten" className="section">
        <div className="container">
          <h1 className="section-title">Halo, {user.name}</h1>
          <p className="section-lead">{user.primary_role} · {user.email}</p>
          <h2 className="h2">Ringkasan aktivitas</h2>
          <ul className="card-grid">
            <Suspense fallback={<li className="widget widget-skeleton" aria-hidden="true" />}><Widgets /></Suspense>
          </ul>
          <h2 className="h2">Semua layanan</h2>
          <ul className="card-grid">{SERVICES.map((s, i) => <ServiceCard key={s.id} service={s} index={i} />)}</ul>
          <form method="post" action="/api/sso/logout"><button className="btn btn-ghost" type="submit">Keluar</button></form>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
