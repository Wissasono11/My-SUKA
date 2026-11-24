# design-universal v2.0.0

Perubahan dari v1:
- Token aksesibel baru: `secondaryTextOnLight` #7A5A00 (6,38:1) dan `secondaryTextOnDark` #EBCB6B. Emas #C59B27 (2,60:1 di putih) hanya dekorasi.
- `borderControl` #769080 (≥3:1) untuk batas input; `borderStrong` tetap dekoratif.
- `focusOnDark` putih untuk latar hijau (biru fokus hanya 1,18:1 di hijau).
- Satu sistem nama `--ms-*`; alias v1 (`--green`, `--ss-*`) dipertahankan sementara.
- Token baru: spacing, elevation, motion, z-index, layout (navbar 64/56px, tap target 44px).
- Skala tipografi fluid; `h1` kini jelas (hero vs title).
- `prefers-reduced-motion` dan `forced-colors` ditangani di token.
- Gerbang kualitas: 24 pasangan kontras diuji; build gagal bila ada yang di bawah minimum.
- Keluaran baru: `tokens.dart` (Flutter ThemeData) dan `tokens.ts`.
- Tanpa runtime skin: dipasang statis lewat `<link>`.
Tidak berubah: palet inti, radius, Plus Jakarta Sans.
Mode gelap sengaja belum didukung (sesuai pedoman v1).
