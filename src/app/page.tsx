import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import ServiceCard from "@/components/ServiceCard";
import { SERVICES } from "@/lib/services";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "MySuka",
  inLanguage: "id-ID",
  description: "Portal layanan digital civitas akademika UIN Sunan Kalijaga.",
};

export default function HomePage() {
  return (
    <>
      <SiteHeader active="home" />
      <main id="konten">
        <section className="hero" aria-labelledby="hero-title">
          <div className="container hero-inner">
            <p className="pill">MySuka</p>
            <h1 id="hero-title">Satu Ruang Digital untuk <span>Civitas Akademika</span> UIN Sunan Kalijaga</h1>
            <p className="hero-lead">Layanan digital kampus yang terintegrasi, dirancang untuk mendukung aktivitas seluruh civitas akademika UIN Sunan Kalijaga.</p>
            <Link className="btn btn-light" href="/login">Masuk dengan akun UIN</Link>
          </div>
        </section>

        <section className="section" aria-labelledby="layanan-title">
          <div className="container">
            <p className="eyebrow">Layanan MySuka</p>
            <h2 id="layanan-title" className="section-title">Semua kebutuhan kampus, <span>satu ruang</span></h2>
            <p className="section-lead">Temukan berbagai layanan digital yang dirancang untuk mendukung aktivitas civitas akademika UIN Sunan Kalijaga.</p>
            <ul className="card-grid">{SERVICES.map((s, i) => <ServiceCard key={s.id} service={s} index={i} />)}</ul>
          </div>
        </section>

        <section className="section section-soft" aria-labelledby="genggam-title">
          <div className="container split">
            <div>
              <p className="eyebrow">MySuka dalam genggaman</p>
              <h2 id="genggam-title" className="section-title">Di mana saja. Kapan saja. Tetap terhubung.</h2>
              <p className="section-lead">Dari ruang kelas hingga rumah, akses layanan kampus melalui laptop atau ponsel.</p>
              <ul className="checks">
                <li>Fleksibel di berbagai perangkat</li>
                <li>Satu akun untuk layanan kampus</li>
                <li>Pindah layanan tanpa login ulang</li>
              </ul>
            </div>
            <div className="panel" role="img" aria-label="Contoh tampilan daftar layanan kampus pada portal MySuka">
              <p className="panel-title">Layanan kampus Anda</p>
              <p className="panel-sub">Semua kebutuhan akademik, satu akses.</p>
              <div className="panel-grid" aria-hidden="true">{SERVICES.map((s) => <span key={s.id}>{s.name}</span>)}</div>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </>
  );
}
