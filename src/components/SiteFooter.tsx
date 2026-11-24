import Link from "next/link";
import { SERVICES } from "@/lib/services";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div>
          <p className="footer-brand">MySuka</p>
          <p className="footer-text">Satu ruang digital untuk civitas akademika UIN Sunan Kalijaga.</p>
        </div>
        <nav aria-label="Layanan">
          <h2 className="footer-title">Layanan</h2>
          <ul>{SERVICES.map((s) => <li key={s.id}><Link href={s.href}>{s.name}</Link></li>)}</ul>
        </nav>
        <nav aria-label="Jelajahi">
          <h2 className="footer-title">Jelajahi</h2>
          <ul>
            <li><Link href="/">Beranda</Link></li>
            <li><Link href="/layanan">Layanan kampus</Link></li>
            <li><Link href="/tentang">Tentang</Link></li>
          </ul>
        </nav>
      </div>
      <div className="container footer-bottom"><small>MySuka · UIN Sunan Kalijaga</small><small>Terhubung. Terintegrasi. Satu akses.</small></div>
    </footer>
  );
}
