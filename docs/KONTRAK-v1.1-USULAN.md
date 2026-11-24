# Usulan Integration Contract v1.1 (draf untuk disetujui tim)

Alasan: satu origin dengan path berbeda (`/siska`, `/archive`, …) tidak menjadi batas keamanan. XSS pada satu layanan dapat memanggil API layanan lain dan membaca storage origin yang sama. Cookie `Path` bukan isolasi.

## 1. SISKA pada origin terpisah (prioritas tinggi)
- `siska.<domain>` (subdomain sendiri), bukan `/siska`. Cookie sesi SISKA tanpa atribut `Domain` (host-only), `HttpOnly`, `Secure`, `SameSite=Lax`.
- CSP ketat, `frame-ancestors 'none'`, `Cache-Control: no-store`, tanpa Service Worker untuk konten pengaduan.
- Portal cukup menautkan ke SISKA; hapus rewrite `/siska` dari gateway. Layanan lain boleh tetap di path (risiko lebih rendah) sampai ada alasan memisahkannya.

## 2. Ganti token di URL dengan authorization code + PKCE per layanan
- Sekarang: `/{app}/sso-callback?token=JWT` (token 120 dtk, `no-referrer`). Lebih lemah: token berada di URL, riwayat browser, dan log proxy.
- Usulan: tiap layanan menjadi OIDC client dari IdP (portal sekarang, Keycloak nanti). Layanan melakukan redirect Authorization Code + PKCE, menukar kode di backend, lalu membuat sesi sendiri. Pengguna tidak melihat form login karena sesi IdP masih aktif.
- Sampai itu siap, handoff token tetap dipakai dengan syarat: TTL ≤ 120 dtk, redirect 303 segera (atau `history.replaceState`), dan penolakan token yang sudah dipakai (`jti` sudah ada di token portal-api).

## 3. Verifikasi token lewat konfigurasi, bukan nilai tertanam
Setiap layanan membaca dua variabel lingkungan:
```
SSO_ISSUER=https://<domain-portal>
SSO_JWKS_URL=https://<domain-portal>/.well-known/jwks.json
```
Validasi `alg=RS256`, `iss`, `aud`, `exp`; cache JWKS dan segarkan saat `kid` tidak dikenal. Dengan begitu pindah ke Keycloak atau IdP lain cukup mengganti dua variabel ini.

## 4. Logout
`POST /api/sso/logout` dengan pemeriksaan Origin (bukan GET). Event `superapp:logout` tetap dipancarkan; handler layanan memakai `fetch(..., { keepalive: true })`.
