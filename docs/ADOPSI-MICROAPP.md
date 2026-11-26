# Panduan adopsi untuk 5 layanan (±1 jam per tim)

Urutan ini mengikuti Integration Contract v1.0. Setiap langkah bisa diuji sendiri.

## 1. Base path (kontrak 1.1)
SukaKetemu `base: '/sukaketemu/'` (Vite + Express) · CampusFix `/campusfix/` · SISKA `basePath: '/siska'` · Archive `app.baseURL: '/archive/'` · PaaS `base: '/paas/'`.
Cookie layanan wajib `Path=/<layanan>`; jangan memakai `Path=/`.

## 2. Design system (statis, tanpa runtime)
Di `<head>`:
```html
<link rel="preload" href="/assets/design/v1/tokens.css" as="style">
<link rel="stylesheet" href="/assets/design/v1/tokens.css">
```
Pakai variabel `--ms-*` (contoh `background: var(--ms-color-primary)`). Alias lama (`--green`, `--ss-primary`, …) masih tersedia agar CSS SISKA yang ada tetap jalan.
Font: host sendiri `PlusJakartaSans-latin.woff2` (OFL) dengan `font-display: swap`; jangan memuat dari Google Fonts.
Aturan emas: `#C59B27` hanya dekorasi. Teks emas di latar terang pakai `--ms-color-secondary-text-on-light`, di latar hijau pakai `--ms-color-secondary-text-on-dark`.
Flutter: salin `design-system/dist/tokens.dart` lalu `theme: mySukaTheme()`.

## 3. `<superapp-navbar>` (kontrak 3)
```html
<script type="module" src="/assets/superapp-navbar.js" async></script>
<superapp-navbar active-app="sukaketemu" theme="light" user-name="…" user-role="…"></superapp-navbar>
<style>
  body{padding-top:64px}
  @media (max-width:767px){body{padding-top:56px}}
  superapp-navbar:not(:defined){display:block;height:64px} /* cegah CLS sebelum skrip termuat */
</style>
```
Hapus header global buatan sendiri (dilarang double navbar). Tangani `superapp:logout`:
```js
window.addEventListener('superapp:logout', () => {
  localStorage.clear(); sessionStorage.clear();
  fetch('/sukaketemu/api/logout', { method: 'POST', keepalive: true }); // keepalive: navigasi segera setelah event
});
```

## 4. Silent login `/sso-callback` (kontrak v1.1: authorization code, bukan token di URL)
1. Portal mengalihkan ke `/<layanan>/sso-callback?code=<kode>`. Kode acak 256-bit, **sekali pakai, berlaku 30 detik**; ia bukan JWT dan tidak berisi identitas.
2. Backend layanan (server-ke-server, **bukan** dari browser) menukarnya:
   ```
   POST https://<portal>/api/sso/exchange   Content-Type: application/json
   {"code":"...","client_id":"<id-layanan>","client_secret":"<SSO_CLIENT_SECRET_...>"}   (+ "code_verifier" bila memakai PKCE)
   -> 200 {"token":"<JWT>","token_type":"Bearer","expires_in":60}   | 400 invalid_grant | 401 invalid_client | 429
   ```
   `client_secret` hanya ada di backend (secret manager), tidak di bundel frontend dan tidak di repositori. PKCE opsional: mulai dari `GET /api/sso/launch?app=<id>&code_challenge=<S256>&code_challenge_method=S256`, kirim `code_verifier` saat exchange.
3. Verifikasi JWT hasil exchange dengan `SSO_JWKS_URL` dan `SSO_ISSUER` dari environment (cache JWKS, segarkan saat `kid` tak dikenal): `alg=RS256`, `iss`, **`aud` = id layanan Anda** (mis. `sukaketemu`, bukan lagi `mysuka-microapps-ecosystem`), `exp`, `typ="handoff"`, `svc` = layanan Anda, `jti` (tolak yang sudah dipakai: `SET jti 1 NX EX 60`).
   Contoh FastAPI: `jwt.decode(token, key, algorithms=["RS256"], issuer=SSO_ISSUER, audience="sukaketemu", options={"require": ["exp","jti","sid"]})`.
4. Buat sesi lokal (cookie `HttpOnly; Secure; SameSite=Lax`, host-only, `Path=/`) dan simpan `sid` dari token bersama sesi itu, lalu redirect 303 ke halaman layanan.
5. **Back-channel logout** (disarankan): sediakan `POST /<layanan>/api/backchannel-logout` yang menerima form `logout_token` (JWT RS256, `typ` header `logout+jwt`, `aud` = layanan Anda, klaim `events` berisi `http://schemas.openid.net/event/backchannel-logout`, `sid`). Setelah memverifikasi, akhiri semua sesi lokal ber-`sid` tersebut, jawab 200, dan beri tahu tim portal URL-nya (`<ID>_BACKCHANNEL_LOGOUT_URL`).
Klaim `user` untuk SISKA hanya `id` dan `primary_role`; `sub` = `user.id` berupa id buram (`usr_…`). `sid` berbeda per layanan agar sesi SISKA tak dapat dikorelasikan dengan layanan lain. Lihat `docs/IDENTITAS-DAN-DATA-PENGGUNA.md` untuk tabel profil lokal.
Express: `jose` → `jwtVerify(token, createRemoteJWKSet(new URL(JWKS_URL)), { issuer, audience: "<id>", algorithms: ["RS256"] })`. Supabase/Firebase: tukar klaim ke sesi masing-masing di backend.

## 5. Widget `GET /<layanan>/api/widget/summary` (kontrak 4)
Bearer = JWT `typ="widget"`, `aud` = layanan Anda, klaim `user` hanya `id` dan `primary_role` (tanpa email/nama/NIM). Verifikasi seperti bagian 4 dan **pakai `user.id` dari token, abaikan parameter identitas dari klien** (anti-IDOR); balas < 1,5 detik, format JSON baku. **SISKA tidak membuat endpoint ini.**

## 6. Syarat skor 100 per layanan
Skor Lighthouse dinilai per URL publik layanan, bukan oleh portal. Minimal: `<title>` + `meta description` unik, `lang="id"`, `viewport`, label form, alt gambar, kontras sesuai token, bundel JS awal kecil (route splitting), gambar AVIF/WebP berdimensi, tanpa error console. Jalankan `lhci` terhadap halaman publik masing-masing.
Halaman di balik login tidak ikut dinilai; beri `noindex` pada halaman itu. Landing publik SISKA boleh terindeks (tanpa data laporan), sisanya `noindex`.

## 7. Khusus SISKA
SISKA dilayani dari origin terpisah (`SISKA_PUBLIC_HOST`, cookie host-only) dan akses ke sana tidak dicatat edge. Pasang juga sendiri di aplikasi: `Cache-Control: no-store`, `X-Frame-Options: DENY` (atau `frame-ancestors 'none'`), `Referrer-Policy: same-origin`. Portal membuang cookie sesinya sebelum meneruskan request ke `/siska`, dan tidak pernah menarik widget SISKA.
