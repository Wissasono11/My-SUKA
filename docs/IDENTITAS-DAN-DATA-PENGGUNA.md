# Identitas dan data pengguna lintas layanan

## Keputusan
- **Kredensial (password) hanya ada di database kampus.** MySuka dan kelima layanan tidak menyalin atau menyimpannya.
- **MySuka tanpa database pengguna.** Setelah login berhasil ia menerbitkan JWT; layanan memverifikasinya lewat JWKS.
- **Tiap layanan punya tabel profil tipis** (tanpa kolom password) yang dibuat saat pertama login (just-in-time). Tabel ini perlu agar data layanan (laporan, arsip, dsb.) bisa memakai foreign key.
- **Peran tetap lokal per layanan.**
- Database pusat MySuka baru perlu bila ada kebutuhan peran global atau audit lintas layanan; saat itu pun tanpa password.

## Id pengguna
| Id | Dibentuk dari | Dipakai untuk |
|---|---|---|
| `campus_id` | id permanen dari sumber kampus (sementara: email, sampai kampus menyediakan id permanen) | hanya di dalam portal-api |
| `user.id` / `sub` global | `usr_` + HMAC-SHA256(`IDENTITY_HMAC_SECRET`, `v1:global:<campus_id>`) | layanan biasa |
| id khusus layanan | HMAC dengan lingkup nama layanan | layanan di `PRIVACY_SERVICES` (default SISKA) |

Id buram tidak membocorkan email/NIM dan tidak bisa dibalik. Id SISKA berbeda dari id layanan lain, sehingga database SISKA tidak dapat dicocokkan dengan database lain. Konsekuensinya: SISKA tidak bisa menautkan pelapor ke layanan lain, dan itu disengaja. Bila SISKA butuh email/nama (mis. notifikasi), kosongkan `PRIVACY_SERVICES` atau tambah klaim secara eksplisit setelah dipertimbangkan bersama pengelola SISKA.

## Tabel profil di layanan (contoh SQL)
```sql
CREATE TABLE user_profiles (
  external_id  TEXT PRIMARY KEY,      -- = sub dari token (usr_...)
  display_name TEXT,
  email        TEXT,                  -- hanya bila klaim tersedia (bukan untuk SISKA)
  role         TEXT NOT NULL DEFAULT 'USER',   -- peran LOKAL layanan, bukan peran kampus
  first_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Tabel data layanan memakai FOREIGN KEY ke user_profiles(external_id).

-- Saat /sso-callback (setelah token tervalidasi, jti belum pernah dipakai, svc cocok):
INSERT INTO user_profiles (external_id, display_name, email)
VALUES ($1, $2, $3)
ON CONFLICT (external_id) DO UPDATE SET last_seen = now(), display_name = COALESCE(EXCLUDED.display_name, user_profiles.display_name);
```
Layanan **tidak** boleh menerima login selain lewat token MySuka setelah migrasi selesai.

## Migrasi akun lama (mis. SISKA yang kini punya "Masuk" dan "Daftar")
1. Tambah kolom `external_id` (nullable) pada tabel pengguna lama.
2. Pada login pertama lewat MySuka, tautkan ke akun lama memakai pencocokan terverifikasi (email atau NIM dari sumber kampus). Untuk SISKA, pertimbangkan **tidak** menautkan akun lama ke identitas kampus bila pelapor mendaftar secara anonim; tanyakan pengelola SISKA.
3. Setelah semua tertaut atau dimigrasi, hapus kolom password dan nonaktifkan form lokal.

## Pertanyaan untuk pengelola database kampus (PUSAT TIK / SIA)
1. Apakah kampus punya **SSO standar** (OpenID Connect, SAML, CAS, atau LDAP/AD) yang boleh dipakai aplikasi lain? Bila ya: dokumentasi, daftar client, redirect URI, scope/claim yang tersedia.
2. Bila tidak ada SSO: apakah ada **API verifikasi login** (endpoint yang menerima identifier + password dan mengembalikan profil)?
3. Bila hanya database: bolehkah dibuatkan **pengguna database baca-saja** dengan **view minimal** (id permanen, email, NIM, NIP, nama, peran, status aktif, hash password), dibatasi IP VPS, dan lewat TLS? Apa **algoritma hash** password (bcrypt, argon2, pbkdf2, md5/sha1 tak bergaram?). Hash lemah menjadi risiko tersendiri.
4. Apakah ada **id pengguna permanen** selain NIM/NIP/email? Apakah NIM/NIP dapat berganti atau dipakai ulang?
5. Bagaimana status akun dinonaktifkan (lulus, cuti, pegawai keluar) dan bagaimana kami mengetahuinya?
6. Apakah ada **MFA** atau kebijakan password yang harus diikuti? Siapa kontak insiden bila terjadi kebocoran?
7. Apakah kampus mengizinkan form login di luar sistem kampus (MySuka memegang password pengguna saat login)? Jika tidak, SSO kampus menjadi satu-satunya jalur.

## Adaptor menurut jawaban
| Jawaban kampus | Yang dibangun | Catatan keamanan |
|---|---|---|
| OIDC/SAML/CAS | MySuka menjadi client; password tak pernah terlihat | paling aman, paling disarankan |
| API verifikasi | form login MySuka memanggil API | rate limit, lockout, tanpa log password |
| Hanya database | form login MySuka + pemeriksaan hash baca-saja | view minimal, TLS, IP allowlist, tanpa menyalin hash |
| Belum ada jawaban | tetap Google/dev seperti sekarang; semua modul id di atas sudah netral terhadap penyedia | jangan produksi dengan Google bila akun kampus bukan Google |

Semua adaptor cukup menghasilkan `CampusUser` (`portal-api/app/identity.py`); sisanya (id buram, klaim per layanan, token) tidak berubah.
