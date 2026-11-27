# Deploy ke VPS sendiri (Docker Compose + Caddy)

Topologi:
```
Internet → Caddy (TLS, routing, isolasi cookie)
            ├── /api/*, /.well-known/jwks.json → portal-api (FastAPI :8000)  ← pemegang kunci privat
            ├── /sukaketemu*, /campusfix*, /archive*, /paas*, /terassc* → upstream masing-masing
            ├── /siska* → pengalihan 308 ke https://<SISKA_PUBLIC_HOST>/siska (origin terpisah, tanpa access log)
            └── lainnya → portal-web (Next.js :3000)  ← hanya verifikasi lewat JWKS
```

## Langkah
1. VPS dengan Docker + Compose, DNS `A` ke VPS untuk `SITE_ADDRESS` **dan** `SISKA_PUBLIC_HOST` (subdomain SISKA), port 80/443 terbuka.
2. `cp .env.example .env.production`, isi: `APP_BASE_URL`, `SITE_ADDRESS`, `ACME_EMAIL`, `*_ORIGIN`, Google OAuth, `ALLOWED_EMAIL_DOMAINS`, `SISKA_PUBLIC_HOST`, `SISKA_PUBLIC_ORIGIN`, dan `ENV=production`.
   Isi `REDIS_PASSWORD` (`openssl rand -hex 32`). Buat satu `SSO_CLIENT_SECRET_<LAYANAN>` acak (`openssl rand -base64 48`) per layanan; serahkan hanya ke backend layanan itu.
3. Buat kunci: `openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out priv.pem`, lalu isi `SSO_PRIVATE_KEY_PEM` (baris baru jadi `\n`):
   `awk 'NF{printf "%s\\n",$0}' priv.pem`. Simpan `priv.pem` di tempat aman lalu hapus dari VPS.
4. Buat `IDENTITY_HMAC_SECRET` (`openssl rand -hex 32`) dan simpan bersama kunci privat; mengubahnya mengganti semua id pengguna.
5. Google Cloud Console: Authorized redirect URI = `https://<SITE_ADDRESS>/api/sso/callback`.
6. `docker compose --env-file .env.production -f infra/docker-compose.yml up -d --build`.
7. Cek: `/healthz` TIDAK dilayani ke internet (404 di edge; healthcheck compose memakai alamat internal). `curl https://<domain>/.well-known/jwks.json` (tanpa field `d`), `curl -I https://<domain>/siska/` (harus 308 ke subdomain SISKA) dan `curl -I https://<SISKA_PUBLIC_HOST>/siska/` (ada `Cache-Control: no-store`).

## Catatan operasional
- **Rate limit, sesi, dan kode otorisasi** disimpan di Redis (service `redis` di compose, tanpa persistensi ke disk). Dengan Redis semua itu global lintas worker dan sesi bertahan saat portal-api restart. Bila Redis mati: login/launch menjawab 503 dan sesi dianggap tidak sah (gagal tertutup).
- **X-Forwarded-For** ditimpa Caddy dengan alamat klien asli; jangan mengekspos portal-api langsung ke internet.
- **Rotasi kunci:** buat kunci baru + `SSO_KEY_ID` baru; pindahkan JWK PUBLIK kunci lama ke `SSO_RETIRED_JWKS` (JWKS menyajikan keduanya) selama ≥ 1 jam, lalu hapus. Bila kunci lama diduga bocor, jangan simpan di `SSO_RETIRED_JWKS`: cabut langsung (semua sesi portal keluar otomatis).
- **Kode & jti:** kode otorisasi sekali pakai dikonsumsi atomik di portal-api; JWT hasil exchange tetap memuat `jti` dan layanan sebaiknya menolak `jti` yang sudah dipakai (`SET jti 1 NX EX 60`).
- **Model sesi allowlist:** sesi sah hanya bila terdaftar di server, belum lewat `SESSION_TTL_SECONDS` (mutlak) dan `SESSION_IDLE_SECONDS` (tak aktif). Tanpa `REDIS_URL` restart portal-api = semua pengguna login ulang (tidak pernah menghidupkan kembali sesi yang sudah dicabut).
- **Backup:** portal tidak menyimpan data pengguna; yang perlu dijaga hanya kunci privat dan `.env.production`.
- **Logout (403 "Origin tidak cocok")**: `POST /api/sso/logout` hanya menerima Origin yang sama dengan `APP_BASE_URL` (tambahan lewat `ALLOWED_ORIGINS`, dipisah koma). Di mode dev, `localhost`/`127.0.0.1` di port mana pun juga diterima. Di produksi akses selalu lewat domain `APP_BASE_URL`.
- **Docs API** (`/api/docs`) otomatis mati saat `ENV=production`.
- Caddyfile telah divalidasi dengan Caddy 2.10 (`caddy validate`) dan redaksi log diuji dengan request nyata. Jalankan ulang bila Anda mengubahnya: `docker run --rm -v $PWD/infra/Caddyfile:/etc/caddy/Caddyfile caddy:2 caddy validate --config /etc/caddy/Caddyfile` dengan env terisi sebelum dipakai.
