# Keamanan layanan (micro-app) My-SUKA

Perlindungan di portal tidak menolong bila satu layanan salah. Dokumen ini adalah syarat keamanan yang **dapat diuji** untuk
setiap layanan, dengan kit dan pemeriksa di `microapp-kit/`.

## Cara memakai
1. Salin `microapp-kit/python/mysuka_sso.py` atau `microapp-kit/node/mysuka-sso.mjs` ke layanan. Referensi alur lengkap:
   `microapp-kit/python/example_fastapi.py`. Jangan menulis ulang verifikasi token sendiri.
2. Env tiap layanan: `SSO_SERVICE_ID`, `SSO_ISSUER`, `SSO_JWKS_URL`, `SSO_EXCHANGE_URL`, `SSO_CLIENT_SECRET` (dari secret manager).
3. Jalankan pemeriksa terhadap **staging layanan sendiri** (dan di CI):
   ```
   node microapp-kit/conformance/check-service.mjs --base https://staging.layanan.example --service sukaketemu \
     --issuer https://mysuka.portal.ac.id --jwks-url https://mysuka.portal.ac.id/.well-known/jwks.json \
     --widget --backchannel /sukaketemu/api/backchannel-logout --foreign-token-env FOREIGN_WIDGET_TOKEN \
     --secret-env SSO_CLIENT_SECRET --yes          # tambahkan --sensitive untuk SISKA
   ```
   `FOREIGN_WIDGET_TOKEN` = token widget SAH untuk layanan LAIN (tim portal dapat menerbitkannya di staging). Tanpa itu
   pemeriksaan `aud` lintas layanan (T05) di-SKIP, dan SKIP bukan lulus.

## Syarat wajib (semua layanan)
| # | Syarat | Diuji |
|---|---|---|
| 1 | `/sso-callback` hanya menerima `?code=`, menukarnya di backend; tidak ada `?token=` | T06–T08, kit |
| 2 | JWT: alg RS256 dikunci, `iss`, **`aud` = id layanan persis**, `typ`, `svc`, `exp`, umur ≤ 120 dtk, `jti` sekali pakai | T02–T05, kit |
| 3 | `client_secret` hanya di backend/secret manager; tidak di repo, bundel, atau log | T21, `check-secrets` |
| 4 | Sesi lokal baru setiap login; cookie `__Host-`, HttpOnly, Secure, SameSite=Lax, **tanpa `Domain`** | T23, kit |
| 5 | Back-channel logout dipasang dan memverifikasi `logout_token` | T10, kit |
| 6 | Widget: identitas hanya dari token, abaikan `user_id` dari klien (anti-IDOR); respons kecil dan sesuai kontrak | T01–T05 |
| 7 | Tidak ada open redirect (`next`/`returnTo` hanya path internal) | T09, `safe_next` |
| 8 | Header: nosniff, anti-framing, Referrer-Policy, HSTS, CSP tanpa `unsafe-eval`; tidak membocorkan teknologi | T11–T17 |
| 9 | CORS tidak memantulkan origin asing; tanpa wildcard berkredensial | T11 |
| 10 | `.env`, `.git`, kunci service account tidak terpapar; galat tanpa stack trace | T20, T22 |
| 11 | Dependensi diaudit (`npm audit`, `pip-audit`) dan diperbarui otomatis | CI |
| 12 | Jalankan >1 instance: ganti `MemoryReplayCache` dengan Redis | kit |

## Per layanan
- **SISKA** (paling sensitif): origin terpisah (sudah), `--sensitive`, PKCE (`SSO_PKCE_SERVICES=siska` + `/sso-start`), tanpa access log
  (sudah di edge), tanpa Service Worker untuk konten pengaduan. Di SISKA sendiri: aturan Firestore deny-by-default (hanya pemilik laporan dan
  peran berwenang), enkripsi bidang sensitif, tanpa fallback pihak ketiga (mis. LLM eksternal) yang menerima isi laporan, dan kunci
  admin/service account tidak pernah di klien. Ini ada di repositori SISKA dan belum saya periksa.
- **PaaS Praktikum**: kode mahasiswa dijalankan di domain sandbox terpisah (`*.sandbox.<domain>`, bukan di bawah origin portal), kontainer tanpa
  jaringan ke Redis/portal-api, tanpa mount rahasia, batas CPU/memori/waktu, `cap_drop: ALL`, rootless.
- **TERAS SC** (MongoDB): hash token sesi di database, jangan menimpa role lokal dari klaim SSO, provisioning akun tidak otomatis admin
  (lihat `TERASSC-INTEGRATION.md`); semua query memakai parameter terikat, bukan string dari klien (hindari injeksi operator `$`).
- **Archive**: validasi tipe/ukuran unggahan di server, sajikan unggahan dari origin/CDN tanpa cookie, `Content-Disposition: attachment`, pindai berkas.
- **SukaKetemu / CampusFix**: unggahan foto sama seperti Archive; batasi data kontak yang tampil publik; rate limit pelaporan.

## Yang tidak dapat dijamin kit
Kit menutup kesalahan umum pada alur login. Logika otorisasi bisnis (siapa boleh membaca laporan siapa), penyimpanan data, dan
infrastruktur layanan tetap harus ditinjau dan diuji tim masing-masing.
