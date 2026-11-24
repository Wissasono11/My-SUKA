import type { NextConfig } from "next";

const origin = (name: string) => (process.env[name] ?? "").replace(/\/+$/, "");
const SERVICES = [
  ["sukaketemu", "SUKAKETEMU_ORIGIN"], ["campusfix", "CAMPUSFIX_ORIGIN"], ["siska", "SISKA_ORIGIN"], ["archive", "ARCHIVE_ORIGIN"], ["paas", "PAAS_ORIGIN"],
] as const;

const SECURITY = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];
const PORTAL_CSP = [
  "default-src 'self'", "script-src 'self' 'unsafe-inline'", "style-src 'self' 'unsafe-inline'", "img-src 'self' data:", "font-src 'self'",
  "connect-src 'self'", "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'",
].join("; ");

const config: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  trailingSlash: false,
  async rewrites() {
    // Prefix-preserving, tanpa transformasi body: /siska/x -> {SISKA_ORIGIN}/siska/x (kontrak 1.1).
    // Layanan yang origin-nya belum diisi tidak dirute (404), bukan diarahkan ke host kosong.
    const proxied = SERVICES.filter(([, env]) => origin(env));
    // Hanya untuk dev/tanpa proxy edge: di VPS, Caddy yang merutekan /api dan JWKS ke portal-api.
    const api = origin("API_ORIGIN");
    return {
      beforeFiles: [
        ...(api ? [{ source: "/api/:path*", destination: `${api}/api/:path*` }, { source: "/.well-known/jwks.json", destination: `${api}/.well-known/jwks.json` }] : []),
        ...proxied.flatMap(([id, env]) => [
        { source: `/${id}`, destination: `${origin(env)}/${id}` },
        { source: `/${id}/:path*`, destination: `${origin(env)}/${id}/:path*` },
      ])],
    };
  },
  async headers() {
    return [
      // Portal: tidak boleh di-iframe, CSP ketat.
      { source: "/((?!sukaketemu|campusfix|siska|archive|paas).*)", headers: [...SECURITY, { key: "Content-Security-Policy", value: PORTAL_CSP }, { key: "X-Frame-Options", value: "DENY" }, { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" }] },
      // SISKA (blueprint: isolasi ketat). CATATAN: header ini tidak terbukti ikut pada respons yang di-proxy lewat
      // rewrite (diuji lokal dengan next start). Pasang juga di aplikasi SISKA sendiri dan/atau di edge (Cloudflare).
      { source: "/siska/:path*", headers: [{ key: "Cache-Control", value: "no-store" }, { key: "X-Frame-Options", value: "DENY" }, { key: "Referrer-Policy", value: "same-origin" }] },
      { source: "/siska", headers: [{ key: "Cache-Control", value: "no-store" }, { key: "X-Frame-Options", value: "DENY" }, { key: "Referrer-Policy", value: "same-origin" }] },
      // Aset bersama untuk micro-app: cache pendek + SWR, boleh dimuat lintas origin bila diperlukan.
      { source: "/assets/:path*", headers: [{ key: "Cache-Control", value: "public, max-age=300, stale-while-revalidate=86400" }] },
      { source: "/fonts/:path*", headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }] },
    ];
  },
};

export default config;
