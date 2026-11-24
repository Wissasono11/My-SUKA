# Deploy ke VPS sendiri (Docker Compose + Caddy)

Topologi:
```
Internet → Caddy (TLS, routing, isolasi cookie)
            ├── /api/*, /.well-known/jwks.json → portal-api (FastAPI :8000)  ← pemegang kunci privat
            ├── /siska*, /sukaketemu*, /campusfix*, /archive*, /paas* → upstream masing-masing
            └── lainnya → portal-web (Next.js :3000)  ← hanya verifikasi lewat JWKS
```

## Langkah
1. VPS dengan Docker + Compose, DNS `A` ke VPS, port 80/443 terbuka.
2. `cp .env.example .env.production`, isi: `APP_BASE_URL`, `SITE_ADDRESS`, `ACME_EMAIL`, `*_ORIGIN`, Google OAuth, `ALLOWED_EMAIL_DOMAINS`, dan `ENV=production`.
3. Buat kunci: `openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out priv.pem`, lalu isi `SSO_PRIVATE_KEY_PEM` (baris baru jadi `\n`):
   `awk 'NF{printf "%s\\n",$0}' priv.pem`. Simpan `priv.pem` di tempat aman lalu hapus dari VPS.
4. Buat `IDENTITY_HMAC_SECRET` (`openssl rand -hex 32`) dan simpan bersama kunci privat; mengubahnya mengganti semua id pengguna.
5. Google Cloud Console: Authorized redirect URI = `https://<SITE_ADDRESS>/api/sso/callback`.
6. `docker compose --env-file .env.production -f infra/docker-compose.yml up -d --build`.
7. Cek: `curl https://<domain>/healthz` (`{"status":"ok"}`, dilayani portal-api), `curl https://<domain>/.well-known/jwks.json` (tanpa field `d`), `curl -I https://<domain>/siska/` (ada `Cache-Control: no-store`).

## Catatan operasional
- **Rate limit** ada di memori satu worker (`--workers 1`). Untuk beberapa replika, pasang rate limit di Caddy (plugin) atau pindahkan ke Redis.
- **X-Forwarded-For** ditimpa Caddy dengan alamat klien asli; jangan mengekspos portal-api langsung ke internet.
- **Rotasi kunci:** tambahkan kunci baru dengan `SSO_KEY_ID` baru; layanan memuat ulang JWKS saat `kid` tidak dikenal. Perlu dukungan multi-kunci di JWKS bila ingin rotasi tanpa putus (belum ada; saat ini satu kunci).
- **jti:** setiap token memuat `jti`. Layanan wajib menolak `jti` yang sudah dipakai (simpan ≤ 120 dtk): `SET jti 1 NX EX 120` di Redis, atau tabel/dict ber-TTL bila satu proses.
- **Backup:** portal tidak menyimpan data pengguna; yang perlu dijaga hanya kunci privat dan `.env.production`.
- **Logout (403 "Origin tidak cocok")**: `POST /api/sso/logout` hanya menerima Origin yang sama dengan `APP_BASE_URL` (tambahan lewat `ALLOWED_ORIGINS`, dipisah koma). Di mode dev, `localhost`/`127.0.0.1` di port mana pun juga diterima. Di produksi akses selalu lewat domain `APP_BASE_URL`.
- **Docs API** (`/api/docs`) otomatis mati saat `ENV=production`.
- Caddyfile belum diuji di lingkungan pembuatan (tidak ada binary Caddy). Jalankan `docker run --rm -v $PWD/infra/Caddyfile:/etc/caddy/Caddyfile caddy:2 caddy validate --config /etc/caddy/Caddyfile` dengan env terisi sebelum dipakai.
