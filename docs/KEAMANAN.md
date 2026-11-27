# Keamanan My-SUKA: status temuan dan kontrak SSO aman

Dokumen ini memetakan temuan dari tiga analisis keamanan (audit 11 celah, checklist backend, analisis S-01…S-12) ke kondisi **kode sebenarnya**. Beberapa temuan ditulis dari dokumen arsitektur, bukan dari kode, sehingga sebagian sudah tidak berlaku.

## Status per temuan

| Temuan | Status di kode | Perubahan |
|---|---|---|
| `private.pem` di repositori | Tidak ada berkas kunci di repo ini; kunci dibaca dari `SSO_PRIVATE_KEY_PEM` (produksi gagal cepat bila kosong) | `*.pem/*.key` masuk `.gitignore` dan `.dockerignore`; `npm run secrets:check` menggagalkan build bila ada kunci privat; JWKS mendukung rotasi (`SSO_RETIRED_JWKS`) |
| JWT di URL `?token=` | **Diperbaiki** | `/launch` hanya mengirim kode sekali pakai (30 dtk); JWT ditukar server-ke-server lewat `POST /api/sso/exchange` (rahasia client per layanan, PKCE opsional). Mode lama hanya dengan `SSO_LEGACY_TOKEN_HANDOFF=1` |
| Replay / TTL 24 jam | **Diperkuat** | Kode sekali pakai atomik, JWT serah-terima 60 dtk, `jti`, sesi portal 8 jam dengan `sid` yang dapat dicabut |
| `aud` global | **Diperbaiki** | Sesi: `aud=mysuka-portal`, `typ=session`. Serah-terima/widget: `aud` = id layanan. Token serah-terima tidak lagi bisa dipakai sebagai cookie sesi portal (sebelumnya bisa, karena audience dan kunci sama) |
| SLO / pencabutan sesi | **Diperbaiki** | Logout mencabut `sid` di server (cookie curian ikut mati, termasuk di portal-web lewat `/api/sso/session`) dan mengirim back-channel logout token ke layanan |
| Open redirect logout | Tidak ada parameter `redirect` pada logout; `returnTo` login sudah divalidasi | Tidak perlu |
| Same-Origin Policy / XSS lintas layanan | **SISKA dipisah** ke subdomain (host-only cookie, tanpa access log) | Caddyfile + `SISKA_PUBLIC_ORIGIN/HOST`. Layanan lain tetap di path (risiko lebih rendah) |
| Sandbox PaaS | Repo ini hanya memproksi `/paas`; tidak ada kode sandbox | **Belum**: pratinjau/kontainer mahasiswa wajib di domain terpisah (mis. `*.sandbox.<domain>` dengan sertifikat wildcard), jangan di bawah origin portal |
| Minimisasi data | Klaim SISKA sudah minimal (PPID) | Token widget kini hanya `id` + peran; `sid` per layanan agar sesi SISKA tak bisa dikorelasikan |
| Log menyimpan token/kode | **Diperbaiki** | Caddy menyamarkan `code/token/state`, menghapus Cookie/Authorization, memotong IP; uvicorn access log disamarkan; `/siska` tidak dicatat |
| IP palsu lewat `X-Forwarded-For` | **Diperbaiki** | Rate limit memakai entri terakhir (ditulis proxy tepercaya), bukan entri kiri yang bisa dipalsukan |
| Form password di portal | Tidak ada: login Google OIDC (PKCE, state, nonce) | Klaim ID token Google kini wajib `exp/iat/iss/aud/sub/email`; perbandingan `state` konstan-waktu |
| IDOR widget | Identitas diambil dari sesi server, cache per `service:user_id`, SISKA tak pernah ditarik | Tidak perlu |
| SSRF BFF | Origin hanya dari env, `follow_redirects=False`, timeout 1,5 dtk | Tidak perlu |
| Integritas navbar | **Ditambah** | Build menghasilkan `/assets/v/<hash>/superapp-navbar.js` (immutable) dan `/assets/superapp-navbar.manifest.json` berisi `integrity="sha384-…"` |

## Belum dikerjakan (perlu keputusan atau infrastruktur)

- **Layar consent dan retensi/offboarding** (UU PDP): keputusan produk/hukum bersama PTIPD.
- **Keamanan internal SISKA** (Gemini fallback, enkripsi kolom Firestore, aturan Firestore): ada di repositori SISKA, bukan di sini. Ini temuan terpenting untuk data penyintas.
- **Domain terpisah untuk sandbox PaaS** (lihat atas).
- **Idle timeout dan BroadcastChannel antar-tab**: butuh sesi sliding; sesi sekarang berlaku mutlak 8 jam (`SESSION_TTL_SECONDS`, turunkan bila perlu).
- **CSP tanpa `'unsafe-inline'`** pada portal: butuh nonce per request yang memaksa render dinamis dan menurunkan skor performa; keputusan ada di tim.
- **Redis**: kode otorisasi, revokasi sesi, dan rate limit di memori satu worker. Untuk replika ganda pindahkan `app/store.py` dan `app/security.py`.
- **Pemisahan origin Archive/PaaS/lainnya**: pola Caddy untuk SISKA dapat disalin.

## Kontrak exchange (ringkas)

`GET /api/sso/launch?app=<id>[&code_challenge=<S256>&code_challenge_method=S256]` → `302 /<id>/sso-callback?code=<kode>`

`POST /api/sso/exchange` `{code, client_id, client_secret[, code_verifier]}` → `200 {token, token_type:"Bearer", expires_in}` | `400 invalid_grant` | `401 invalid_client` | `429 rate_limited`. Kode dibakar pada percobaan pertama yang melewati autentikasi client, termasuk bila dipakai layanan lain. Tebakan rahasia dibatasi 10 gagal/menit/IP.

Panduan sisi layanan: `docs/ADOPSI-MICROAPP.md` bagian 4.

## Langkah migrasi (urutan)

1. Isi `SSO_CLIENT_SECRET_<LAYANAN>` (min. 32 karakter) di portal dan serahkan ke tiap tim lewat secret manager.
2. Tiap layanan mengimplementasikan exchange dan memeriksa `aud` = id layanan. Selama migrasi, set `SSO_LEGACY_TOKEN_HANDOFF=1` sementara (token tetap ber-`aud` per layanan, jadi tim tetap harus mengubah `audience`).
3. Buat DNS `SISKA_PUBLIC_HOST`, isi `SISKA_PUBLIC_ORIGIN` dan `SISKA_PUBLIC_HOST`, deploy, uji `curl -I https://<domain>/siska` (308).
4. Matikan `SSO_LEGACY_TOKEN_HANDOFF`.
5. Bila `private.pem` pernah ter-commit di riwayat Git mana pun: buat kunci baru + `SSO_KEY_ID` baru, jangan masukkan kunci lama ke `SSO_RETIRED_JWKS`, bersihkan riwayat dengan `git filter-repo --path private.pem --invert-paths`, lalu force-push dan minta semua kontributor clone ulang.

## Perubahan yang memutus kompatibilitas

- `aud` JWT serah-terima berubah dari `mysuka-microapps-ecosystem` menjadi id layanan; `/launch` mengirim `?code=` bukan `?token=` (kecuali mode legacy).
- Cookie sesi lama tidak valid (`aud`/`typ`/`sid` baru): semua pengguna login ulang sekali setelah deploy.
- Tanpa `SSO_CLIENT_SECRET_<ID>`, `/launch` ke layanan itu menjawab 503 (fail closed).
- `/siska` di domain utama kini mengalihkan ke `SISKA_PUBLIC_HOST`; SISKA harus tetap melayani di path `/siska` (basePath-nya sudah begitu).

## Pengerasan lanjutan (patch `mysuka-security-hardening`)

| Area | Perubahan | Berkas |
|---|---|---|
| ENV aman-bawaan | `ENV` kosong/salah eja = **production** (sebelumnya development: login dev, kunci sementara, cookie tanpa Secure). Next dan FastAPI memakai aturan yang sama | `config.py`, `cookie.ts` |
| Sesi | Model **allowlist**: sesi sah hanya bila terdaftar; ada batas **idle** (`SESSION_IDLE_SECONDS`, 30 mnt) dan batas mutlak; restart tidak menghidupkan sesi yang dicabut; logout mengirim `Clear-Site-Data` | `store.py`, `tokens.py` |
| Redis | Sesi, kode sekali pakai (`GETDEL` atomik) dan rate limit global; gagal tertutup bila Redis mati; compose menambah Redis tanpa persistensi disk | `store.py`, `security.py`, `docker-compose.yml` |
| Cookie OIDC | Produksi: `__Host-mysuka_oidc` (anti cookie tossing dari subdomain) | `routes_sso.py` |
| Exchange | Rotasi rahasia tanpa downtime (`_NEXT`), kode ditolak bila sesi sudah berakhir, PKCE terkelola (`SSO_PKCE_SERVICES`, `/sso-start`) | `routes_sso.py`, `config.py` |
| Masukan IdP | Nama dibersihkan (kontrol/bidi, 120 karakter); foto hanya dari `*.googleusercontent.com` | `tokens.py` |
| Widget (layanan tak tepercaya) | Respons maks. 32 KB, panjang/jumlah field dibatasi, `action_url` harus path di dalam layanan itu | `widgets.py` |
| Audit | Log JSON tanpa data pribadi (`mysuka.audit`), IP dipotong; dasar alert | `audit.py` |
| Header API | CSP `default-src 'none'`, X-Frame-Options, HSTS (produksi), Permissions-Policy | `main.py` |
| Edge | `/healthz`, `/api/docs`, `/.env`, `/.git` tidak pernah keluar; X-Real-IP/Forwarded dibuang ke upstream (divalidasi `caddy validate` 2.10) | `Caddyfile` |
| Rantai pasok | `check-secrets` mendeteksi kunci Google/AWS/GitHub/Slack/service account dan `.env` terlacak Git; CI: npm audit, pip-audit, gitleaks, Trivy; Dependabot; `npm ci --ignore-scripts` | `.github/`, `scripts/` |
| Layanan | **microapp-kit**: verifier (Python/Node), contoh layanan, dan pemeriksa black-box | `microapp-kit/`, `docs/KEAMANAN-MICROAPP.md` |

### Masih terbuka (jujur)
- **CSP tanpa `'unsafe-inline'`** untuk skrip: butuh nonce per request, memaksa render dinamis pada halaman publik. Tidak dikerjakan karena tidak dapat diverifikasi tanpa browser di lingkungan ini.
- **Rate limit di edge** (mis. plugin `caddy-ratelimit`): perlu build Caddy kustom; belum diuji. Rate limit aplikasi (Redis) sudah ada.
- **Layar consent/retensi (UU PDP)**, **kode layanan lain** (SISKA, PaaS, dll.), **konfigurasi Google Cloud, VPS, firewall**: di luar repo ini. CI dan Docker image belum dijalankan di sini (hanya YAML yang divalidasi).
- `campus_id` masih berupa email; pindah ke `sub` Google/ID kampus permanen akan mengubah semua id pengguna, jadi perlu keputusan migrasi.
