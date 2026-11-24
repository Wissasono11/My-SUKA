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

## 4. Silent login `/sso-callback` (kontrak 2.3)
Backend verifikasi `token` dengan `SSO_JWKS_URL` dan `SSO_ISSUER` dari environment (jangan ditanam di kode; cache, validasi `alg=RS256`, `iss`, `aud=mysuka-microapps-ecosystem`, `exp`), set cookie HttpOnly sesi layanan, lalu **segera** `history.replaceState` untuk menghapus `?token=`. Token serah-terima hanya berlaku 120 detik dan memuat `jti`: **tolak `jti` yang sudah pernah dipakai** (Redis `SET jti 1 NX EX 120`; bila gagal, token itu replay). Contoh FastAPI: `PyJWKClient(SSO_JWKS_URL)` + `jwt.decode(..., algorithms=["RS256"], issuer=SSO_ISSUER, audience="mysuka-microapps-ecosystem", options={"require": ["exp","jti"]})`, lalu redirect 303 agar `?token=` hilang dari URL.
Tambahan v0.2: token memuat `svc` (nama layanan) dan layanan **wajib menolak token dengan `svc` yang bukan miliknya**. Klaim `user` untuk SISKA hanya `id` dan `primary_role`; `sub` = `user.id` berupa id buram (`usr_…`), bukan lagi `mhs_<NIM>`. Lihat `docs/IDENTITAS-DAN-DATA-PENGGUNA.md` untuk tabel profil lokal.
Express: `jose` → `jwtVerify(token, createRemoteJWKSet(new URL(JWKS_URL)), {...})`. Supabase/Firebase: tukar klaim ke sesi masing-masing di backend.

## 5. Widget `GET /<layanan>/api/widget/summary` (kontrak 4)
Bearer = token yang sama; balas < 1,5 detik, format JSON baku. **SISKA tidak membuat endpoint ini.**

## 6. Syarat skor 100 per layanan
Skor Lighthouse dinilai per URL publik layanan, bukan oleh portal. Minimal: `<title>` + `meta description` unik, `lang="id"`, `viewport`, label form, alt gambar, kontras sesuai token, bundel JS awal kecil (route splitting), gambar AVIF/WebP berdimensi, tanpa error console. Jalankan `lhci` terhadap halaman publik masing-masing.
Halaman di balik login tidak ikut dinilai; beri `noindex` pada halaman itu. Landing publik SISKA boleh terindeks (tanpa data laporan), sisanya `noindex`.

## 7. Khusus SISKA
Pasang sendiri di aplikasi: `Cache-Control: no-store`, `X-Frame-Options: DENY` (atau `frame-ancestors 'none'`), `Referrer-Policy: same-origin`. Portal membuang cookie sesinya sebelum meneruskan request ke `/siska`, dan tidak pernah menarik widget SISKA.
