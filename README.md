# 🎓 Repositori Pengembangan Superapp Kampus
### Capstone Project — Tim Orkestrasi & Integrasi Portal Terpadu

Selamat datang di repositori kerja **Subtim Inti Superapp Kampus**. Repositori ini berfungsi sebagai pusat koordinasi, pengembangan portal utama (*App-Shell Host*), manajemen autentikasi terpusat (SSO), serta standarisasi integrasi bagi 5 aplikasi layanan kampus.

---

## 📌 Ringkasan Proyek

Superapp Kampus menyatukan 5 aplikasi mandiri ke dalam satu pintu akses terpadu (`superapp.kampus.ac.id`):
1. **SukaKetemu** *(Smart Lost & Found)*
2. **CampusFix** *(Pelaporan Kerusakan Fasilitas Kampus)*
3. **SISKA** *(Sistem Pengaduan Kekerasan Seksual - Pengamanan Khusus)*
4. **Archive System** *(Pendukung Belajar Mengajar)*
5. **PaaS Praktikum Kampus** *(Environment & Manajemen Praktikum)*

> **Prinsip Utama:** Masing-masing dari 5 tim tetap mengelola aplikasi dan databasenya sendiri. Repositori ini fokus membangun **portal induk (pintu masuk), tombol navigasi bersama (*App-Switcher*), serta jembatan login sekali masuk (Single Sign-On)**.

---

## 👥 Tim & Pembagian Peran (Core Team)

Proyek ini digerakkan oleh tim inti dengan pembagian fokus kerja sebagai berikut:

| Nama | Peran | Fokus & Tanggung Jawab Utama |
| :--- | :--- | :--- |
| **Bayu** | **Project Manager & Integration Lead** | • Memimpin koordinasi teknis dengan 5 ketua tim aplikasi (total 40 pengembang).<br>• Menyusun *Integration Contract* (aturan main integrasi & format data).<br>• Mengawal timeline sprint mingguan, manajemen risiko, dan memastikan rilis tepat waktu. |
| **Hannah** | **UI/UX & Design System Lead** | • Merancang antarmuka Portal Utama (Halaman Login, Katalog Aplikasi, Dashboard, Profil).<br>• Menyusun panduan visual (*Mini Design System*) agar tampilan antar-aplikasi selaras.<br>• Memimpin pengujian alur pengguna (*User Acceptance Testing* / UAT). |
| **Zamron** | **Frontend Engineer (App-Shell & Widgets)** | • Membangun website Portal Utama (*App-Shell Host*).<br>• Membuat komponen *Top Navigation Bar* (`<superapp-navbar>`) yang akan ditempelkan di 5 aplikasi.<br>• Mengembangkan kartu ringkasan informasi (*widgets*) di halaman beranda. |
| **Chairul** | **Backend Engineer (SSO & Data Aggregator)** | • Membangun sistem login terpusat (*Central SSO Broker*) berbasis NIM & kata sandi.<br>• Menyediakan jembatan penukar token login untuk Express.js, Supabase, dan Firebase.<br>• Membuat API ringkasan (*BFF Aggregator*) untuk menyuplai data ke kartu beranda. |
| **Salman** | **Jaringan & Infrastruktur (DevOps)** | *Peran ini saat ini masih terbuka. Untuk sementara, tugas setup domain, SSL, dan reverse proxy* |

---

## 📅 Roadmap & Pembagian Kerja Mingguan (Sprint Plan)

Target peluncuran resmi sistem adalah **14 Desember 2026 (`v1.0-prod`)** melalui 4 tahapan mingguan:

### 📍 Pekan 1: Perencanaan, Kontrak Integrasi & Desain (17 – 22 Nov 2026)
*Target: Fondasi & Kesepakatan Awal (`v0.1-alpha`)*
- **Bayu:** Finalisasi dokumen kesepakatan integrasi bersama 5 ketua tim dan menyiapkan papan tugas (*task board*).
- **Hannah:** Membuat rancangan desain UI (Figma) untuk Portal Utama dan panduan warna/komponen bersama.
- **Zamron:** Menyiapkan kerangka dasar proyek Frontend portal utama dan struktur navigasi.
- **Chairul:** Merancang skema data akun, struktur token login (JWT), dan spesifikasi API ringkasan data.
- **Tim (Bayu & Chairul):** Menyiapkan domain utama kampus dan perencanaan rute link aplikasi.

---

### 📍 Pekan 2: Pembuatan Portal Utama, Login Terpusat & Topbar (23 – 29 Nov 2026)
*Target: Sistem Inti Mulai Berfungsi (`v0.2-beta`)*
- **Bayu:** Memantau kesiapan 5 tim dalam menyesuaikan jalur URL aplikasi masing-masing.
- **Hannah:** Uji tampilan desain di versi mobile dan merapikan aset ikon resmi dari 5 aplikasi.
- **Zamron:** Menyelesaikan halaman Login, katalog 5 aplikasi, serta membuat script *Topbar* bersama.
- **Chairul:** Mengaktifkan server autentikasi (login via NIM berhasil menerbitkan token terverifikasi).
- **Tim:** Menguji penyematan *Topbar* di salah satu aplikasi uji coba.

---

### 📍 Pekan 3: Integrasi dengan 5 Aplikasi Mitra (30 Nov – 6 Des 2026)
*Target: Seluruh Aplikasi Terhubung (`v0.9-rc`)*
- **Bayu:** Mengawal uji coba alur login dari portal menuju ke-5 aplikasi secara langsung.
- **Hannah:** Melakukan evaluasi kenyamanan pengguna saat berpindah antar-aplikasi.
- **Zamron:** Memasang kartu ringkasan status di beranda (misal: jumlah laporan di CampusFix / status di SukaKetemu).
- **Chairul:** Menghubungkan API ringkasan data dari aplikasi mitra ke beranda portal.
- **Tim:** Memastikan sistem pengaduan **SISKA** tetap terisolasi aman (tanpa bocor data ke beranda umum).

---

### 📍 Pekan 4: Uji Coba Menyeluruh, Perbaikan & Peluncuran (7 – 14 Des 2026)
*Target: Rilis Produksi Final (`v1.0-prod`)*
- **Bayu:** Memimpin evaluasi akhir, memberlakukan **Code Freeze per 12 Desember 2026**, dan menyusun laporan proyek.
- **Hannah:** Mendampingi sesi pengujian pengguna (UAT) bersama mahasiswa/dosen perwakilan.
- **Zamron:** Memperbaiki bug tampilan, memastikan portal ringan, dan responsif di semua perangkat.
- **Chairul:** Uji ketahanan server login dan memastikan tidak ada celah keamanan data akun.
- **Seluruh Anggota:** **Go-Live produksi bersama pada 14 Desember 2026.**

---

## 🤝 Alur Koordinasi dengan 5 Tim Layanan

Karena proyek ini melibatkan 40 pengembang dari 5 aplikasi berbeda, alur koordinasi ditetapkan sebagai berikut:

```
[ Mahasiswa / Pengguna ]
           │
           ▼
┌────────────────────────────────────────┐
│  PORTAL UTAMA (Zamron & Hannah)       │ ◄─── Pintu Masuk Tunggal
│  SSO LOGIN    (Chairul)                │
└───────────────────┬────────────────────┘
                    │  (Pindah Aplikasi & Tukar Sesi Login)
     ┌──────────────┼──────────────┬──────────────┬──────────────┐
     ▼              ▼              ▼              ▼              ▼
[SukaKetemu]   [CampusFix]      [SISKA]      [Archive]      [PaaS]
 Tim Mitra 1    Tim Mitra 2   Tim Mitra 3   Tim Mitra 4   Tim Mitra 5
```

1. **Jalur Komunikasi:** Seluruh komunikasi teknis keluar-masuk dipimpin oleh **Bayu (PM)** agar arahan tetap satu pintu.
2. **Kebutuhan Tim Mitra:** Tim mitra hanya perlu menyisipkan 1 baris skrip *Topbar* buatan **Zamron** dan menerima kiriman data login dari sistem buatan **Chairul**.
3. **Privasi SISKA:** Sesuai etika penanganan kekerasan seksual, layanan SISKA **tidak akan** menampilkan ringkasan data apa pun di beranda umum demi melindungi privasi korban.

---

## 🛠️ Aturan Kolaborasi di GitHub

Untuk menjaga kode tetap rapi dan mempermudah kerja sama:

1. **Struktur Branch:**
   - `main`: Kode stabil yang sudah siap digunakan/diuji.
   - `staging`: Tempat penggabungan hasil kerja mingguan tim.
   - `feat/nama-fitur`: Branch kerja mandiri (contoh: `feat/halaman-login-zamron`, `feat/api-sso-chairul`).
2. **Pull Request (PR):**
   - Setiap fitur yang selesai wajib dibuatkan Pull Request ke branch `staging`.
   - Wajib di-*review* minimal oleh 1 rekan tim sebelum di-*merge*.
3. **Jadwal Sinkronisasi:**
   - *Weekly Sync:* Evaluasi pencapaian target setiap akhir pekan bersama seluruh anggota.
   - *Code Freeze:* **12 Desember 2026** (tidak ada penambahan fitur baru, hanya perbaikan bug minor).

---

<p align="center">
  <b>Subtim Inti Orkestrasi Superapp Kampus</b><br>
  Fakultas Sains dan Teknologi • Semester 7 Capstone Project
</p>
