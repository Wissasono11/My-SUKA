# Runbook keamanan My-SUKA (pemantauan dan insiden)

## Log audit
portal-api menulis satu baris JSON per kejadian ke logger `mysuka.audit` (stdout), tanpa email/nama/NIM/kode/token. Kejadian:
`login_success`, `login_denied`, `launch`, `launch_denied`, `exchange_ok`, `exchange_fail`, `rate_limited`, `logout`,
`logout_revoke_failed`, `backchannel_logout_failed`. IP dipotong ke /24 (IPv4) atau /56 (IPv6).

## Alert yang disarankan (di Loki/Grafana/CloudWatch atau skrip cron)
| Kondisi | Arti | Tindakan |
|---|---|---|
| `exchange_fail` reason `invalid_client` > 10 / 5 mnt untuk satu layanan | tebakan/kebocoran `client_secret` | rotasi rahasia layanan itu |
| `exchange_fail` reason `invalid_grant`/`pkce_mismatch` melonjak | kode dicuri/diputar ulang | periksa layanan itu, aktifkan PKCE |
| `login_denied` melonjak | credential stuffing / domain salah | periksa `rate_limited`, pertimbangkan blok IP di edge |
| `backchannel_logout_failed` berulang | sesi layanan tidak mati saat logout | hubungi tim layanan |
| `logout_revoke_failed` atau Redis tidak sehat | pencabutan sesi gagal | pulihkan Redis; sesi tetap mati oleh idle/exp |

## Insiden
- **Rahasia client layanan bocor:** isi `SSO_CLIENT_SECRET_<ID>_NEXT` dengan nilai baru, serahkan ke tim layanan, setelah migrasi pindahkan ke nilai utama dan kosongkan `_NEXT`; deploy.
- **Kunci privat SSO bocor:** buat kunci + `SSO_KEY_ID` baru, JANGAN taruh kunci lama di `SSO_RETIRED_JWKS`, deploy. Semua sesi portal tidak sah seketika.
- **Sesi massal harus dicabut:** `redis-cli FLUSHDB` (instance khusus portal) mengeluarkan semua pengguna; tanpa Redis, restart portal-api.
- **`IDENTITY_HMAC_SECRET` bocor:** id pengguna dapat dikorelasikan; ganti mengubah semua id, jadi rencanakan migrasi dengan tim layanan.
- **Layanan dibobol:** cabut `SSO_CLIENT_SECRET_<ID>` (launch ke layanan itu 503) sambil menyelidiki; layanan lain tidak terdampak karena `aud` dan id per layanan.

## Rutin
Mingguan: tinjau PR Dependabot dan hasil workflow `security`. Per kuartal: rotasi `client_secret`, uji pemulihan Redis, jalankan `check-service.mjs` ke semua layanan.
