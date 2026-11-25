import Link from "next/link";
import ServiceIcon from "@/components/ServiceIcon";
import ServiceShowcase from "@/components/ServiceShowcase";
import SiteFooter from "@/components/SiteFooter";
import { SERVICES } from "@/lib/services";

const featuredServices = SERVICES.filter((service) =>
  ["sukaketemu", "campusfix", "siska", "archive", "paas"].includes(service.id),
);

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "MySuka",
  inLanguage: "id-ID",
  description: "Portal layanan digital civitas akademika UIN Sunan Kalijaga.",
};

function MySukaMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`mysuka-mark${small ? " mysuka-mark-small" : ""}`} aria-hidden="true">
      <svg viewBox="0 0 40 40" fill="none">
        <path d="M20 2.8 24.8 7.2 31.3 7.5 32.5 14 37.2 20 32.5 26 31.3 32.5 24.8 32.8 20 37.2 15.2 32.8 8.7 32.5 7.5 26 2.8 20 7.5 14 8.7 7.5 15.2 7.2 20 2.8Z" fill="#F4F8E9" stroke="#D5B95D" strokeWidth="1.5"/>
        <path d="m20 9 3.2 4.1 5.1 1.1-2.6 4.5.4 5.2-5-1.5-5 1.5.4-5.2-2.6-4.5 5.1-1.1L20 9Z" fill="#08734B"/>
        <circle cx="20" cy="19.5" r="3.2" fill="#E6C85B"/>
      </svg>
    </span>
  );
}

export default function HomePage() {
  return (
    <>
      <main id="konten" className="home-page">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-frame">
            <div className="hero-content">
              <p className="hero-brand"><MySukaMark small /> MySuka</p>
              <h1 id="hero-title">Satu Ruang Digital untuk Civitas<br className="desktop-break" /> Akademika UIN Sunan Kalijaga</h1>
              <p className="hero-lead">Layanan digital kampus yang terintegrasi, dirancang untuk mendukung aktivitas seluruh<br className="desktop-break" /> civitas akademika UIN Sunan Kalijaga.</p>
              <Link className="hero-login" href="/login">Masuk Dengan Akun UIN <span aria-hidden="true">↗</span></Link>
            </div>
          </div>
        </section>

        <section className="services-section" aria-labelledby="layanan-title">
          <div className="section-heading">
            <p className="eyebrow">Layanan MySuka</p>
            <h2 id="layanan-title">Semua Kebutuhan Kampus, <span>Satu Ruang</span></h2>
            <p>Temukan berbagai layanan digital yang dirancang untuk mendukung aktivitas civitas akademika<br className="desktop-break" /> UIN Sunan Kalijaga</p>
          </div>

          <ServiceShowcase />
        </section>

        <section className="connected-section" aria-labelledby="genggam-title">
          <div className="connected-inner">
            <div className="portal-mockup">
              <div className="monitor-camera" />
              <div className="monitor-screen">
                <div className="mock-toolbar"><span className="mock-logo"><MySukaMark small /> MySuka</span><span>Portal Layanan Terpadu</span></div>
                <div className="mock-heading"><small>LAYANAN UNTUK KAMPUS TERPADU</small><h3>Akses Cepat 5 Layanan Utama Sivitas</h3><p>Pintu masuk layanan digital Satu-Single Sign-On UIN Sunan Kalijaga</p></div>
                <div className="mock-services">
                  {featuredServices.slice(0, 4).map((service) => (
                    <div className="mock-service" key={service.id}>
                      <span className="mock-icon"><ServiceIcon id={service.id} size={17} /></span>
                      <small>{service.name.toUpperCase()}</small>
                      <strong>{service.title}</strong>
                      <span className="mock-open">Buka Portal ↗</span>
                    </div>
                  ))}
                </div>
                <div className="mock-pagination"><i /><i /><i /></div>
              </div>
              <div className="monitor-neck" />
              <div className="monitor-foot" />
            </div>
            <div className="connected-copy">
              <p className="hero-brand connected-brand"><MySukaMark small /> MySuka</p>
              <h2 id="genggam-title">Di mana saja, <span>Kapan saja,</span><br />Tetap terhubung.</h2>
              <p>Dari ruang kelas hingga rumah, akses layanan kampus melalui laptop atau ponsel. MySuka hadir mengikuti aktivitas Anda.</p>
              <ul className="checks">
                <li>Fleksibel di berbagai perangkat</li>
                <li>Satu akun untuk akses berbagai layanan</li>
              </ul>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </>
  );
}
