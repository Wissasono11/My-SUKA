# Integrasi TERAS SC ke My-SUKA

Dokumen ini mencatat konfigurasi integrasi tahap awal. TERAS SC tetap berjalan
sebagai aplikasi terpisah; My-SUKA hanya menjadi portal peluncur layanan.

## 1. Environment variable

Tambahkan variabel berikut pada environment deployment My-SUKA (Production,
Preview jika diperlukan, dan Development):

```env
TERASSC_ORIGIN=https://terassc.vercel.app
```

Isi variabel dengan **origin saja**: tanpa `/terassc`, tanpa trailing slash,
dan tanpa path lain. `href` layanan sudah mengarahkan pengguna ke `/terassc`.

## 2. URL layanan

- Origin: `https://terassc.vercel.app`
- Base path frontend Vite: `/terassc/`
- URL yang dibuka dari My-SUKA: `https://terassc.vercel.app/terassc`

Jangan menanam TERAS SC ke dalam iframe atau mem-proxy aplikasinya melalui
origin My-SUKA pada tahap ini. Pemisahan origin menjaga cookie, local storage,
dan batas keamanan masing-masing aplikasi.

## 3. Status autentikasi

Patch ini **belum mengaktifkan Single Sign-On (SSO)**. Login TERAS SC yang
sekarang tetap menggunakan akun MongoDB lokal melalui endpoint backend
`/auth/login`. Penambahan kartu/tautan layanan pada My-SUKA tidak otomatis
membuat sesi login My-SUKA berlaku di TERAS SC.

Jangan mengirim password, `apiToken`, access token, atau refresh token My-SUKA
melalui query string URL. Jangan menganggap email dari parameter URL sebagai
bukti identitas pengguna.

SSO harus dikerjakan sebagai perubahan terpisah dengan alur server-to-server:

1. My-SUKA menerbitkan authorization code/token sekali pakai yang singkat
   masa berlakunya, ditujukan khusus untuk audience `terassc`.
2. Browser mengirim code tersebut ke endpoint backend TERAS SC melalui HTTPS.
3. Backend TERAS SC memvalidasi tanda tangan, issuer, audience, expiry, nonce,
   dan status sekali pakai sebelum membuat sesi lokal.
4. Backend memetakan identitas terverifikasi ke akun MongoDB berdasarkan email
   yang dinormalisasi. Jangan menimpa password atau role lokal (`admin`/`user`).
5. Jika akun belum terhubung, tolak login dengan pesan yang jelas sampai
   kebijakan provisioning akun disepakati. Jangan otomatis memberi role admin.

Gunakan mekanisme sesi lokal TERAS SC yang kompatibel dengan middleware
`protect` saat ini. Simpan hash token sesi di database, bukan token mentah.
Pertahankan login lokal selama masa transisi dan uji logout/revokasi untuk
kedua metode autentikasi.

## 4. Widget dashboard
