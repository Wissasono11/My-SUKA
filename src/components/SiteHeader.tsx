import Link from "next/link";

type Active = "home" | "layanan" | "tentang";

export default function SiteHeader({ active }: { active?: Active }) {
  const cur = (k: Active) => (active === k ? "page" : undefined);
  return (
    <header className="site-header">
      <div className="container header-inner">
        <Link className="brand" href="/">
          <span className="brand-mark" aria-hidden="true">M</span>
          <span>MySuka</span>
        </Link>
        <nav aria-label="Navigasi utama" className="nav">
          <Link href="/" aria-current={cur("home")}>Beranda</Link>
          <Link href="/layanan" aria-current={cur("layanan")}>Layanan</Link>
          <Link href="/tentang" aria-current={cur("tentang")}>Tentang</Link>
        </nav>
        <Link className="btn btn-primary" href="/login">Masuk</Link>
      </div>
    </header>
  );
}
