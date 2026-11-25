import { SERVICES } from "@/lib/services";

function FooterMark() {
  return (
    <span className="footer-mark" aria-hidden="true">
      <svg viewBox="0 0 40 40" fill="none">
        <path d="M20 2.8 24.8 7.2 31.3 7.5 32.5 14 37.2 20 32.5 26 31.3 32.5 24.8 32.8 20 37.2 15.2 32.8 8.7 32.5 7.5 26 2.8 20 7.5 14 8.7 7.5 15.2 7.2 20 2.8Z" fill="#F4F8E9" stroke="#D5B95D" strokeWidth="1.5"/>
        <path d="m20 9 3.2 4.1 5.1 1.1-2.6 4.5.4 5.2-5-1.5-5 1.5.4-5.2-2.6-4.5 5.1-1.1L20 9Z" fill="#08734B"/>
        <circle cx="20" cy="19.5" r="3.2" fill="#E6C85B"/>
      </svg>
    </span>
  );
}

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-about">
          <p className="footer-brand"><FooterMark /> MySuka</p>
          <p>Portal ekosistem layanan terpadu civitas akademika Universitas Islam Negeri Sunan Kalijaga Yogyakarta.</p>
        </div>
        <div className="footer-social">
          <h2 className="footer-title">Sosial Media</h2>
          <p>Ikuti kabar terbaru dan pengumuman resmi civitas:</p>
          <div className="social-icons" aria-label="Sosial media">
            <a href="https://www.facebook.com/uinsukajogja" aria-label="Facebook">f</a>
            <a href="https://x.com/uinsk" aria-label="X">𝕏</a>
            <a href="https://www.instagram.com/uinsk/" aria-label="Instagram">◎</a>
            <a href="https://www.youtube.com/@uinsunankalijaga" aria-label="YouTube">▶</a>
          </div>
        </div>
        <div className="footer-contact">
          <h2 className="footer-title">Kontak</h2>
          <p><span>♧</span> Telepon: +62-274-512474 / +62-274-589621</p>
          <p><span>▣</span> Fax: +62-274-586117</p>
          <p><span>✉</span> Email: humas@uin-suka.ac.id</p>
          <p><span>⌖</span> Address: Jl. Laksda Adisucipto, Papringan, Caturtunggal, Kec. Depok, Kabupaten Sleman, Daerah Istimewa Yogyakarta 55281</p>
        </div>
      </div>
      <div className="footer-bottom"><small>Copyright © 2026 PTIPD - UIN Sunan Kalijaga All Rights Reserved.</small></div>
    </footer>
  );
}
