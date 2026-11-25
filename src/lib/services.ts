export type ServiceId = "sukaketemu" | "campusfix" | "siska" | "archive" | "paas" | "terassc";

export interface Service {
  id: ServiceId;
  name: string;
  title: string;
  description: string;
  href: string;
  /** SISKA dikecualikan dari widget demi kerahasiaan penyintas (kontrak 4.1). */
  widget: boolean;
  originEnv: string;
}

export const SERVICES: readonly Service[] = [
  { id: "sukaketemu", name: "SukaKetemu", title: "Pencarian & Pelaporan Barang", description: "Temukan dan laporkan barang hilang atau ditemukan di lingkungan kampus.", href: "/sukaketemu", widget: true, originEnv: "SUKAKETEMU_ORIGIN" },
  { id: "campusfix", name: "CampusFix", title: "Pelaporan Kerusakan Fasilitas", description: "Laporkan kerusakan fasilitas kampus agar dapat segera ditindaklanjuti.", href: "/campusfix", widget: true, originEnv: "CAMPUSFIX_ORIGIN" },
  { id: "siska", name: "SISKA", title: "Layanan Pengaduan & Perlindungan", description: "Akses layanan pengaduan kekerasan seksual dengan mengutamakan privasi.", href: "/siska", widget: false, originEnv: "SISKA_ORIGIN" },
  { id: "archive", name: "Archive", title: "Akses Materi & Arsip Akademik", description: "Temukan dan unduh materi serta arsip untuk mendukung kegiatan belajar mengajar.", href: "/archive", widget: true, originEnv: "ARCHIVE_ORIGIN" },
  { id: "paas", name: "PaaS Praktikum", title: "Manajemen Praktikum & Lingkungan Uji Coba", description: "Kelola kebutuhan praktikum dan lingkungan uji coba dalam satu tempat.", href: "/paas", widget: true, originEnv: "PAAS_ORIGIN" },
  { id: "terassc", name: "TERAS SC", title: "Layanan & Informasi Student Center", description: "Akses layanan TERAS Student Center melalui portal My-SUKA.", href: "/terassc", widget: false, originEnv: "TERASSC_ORIGIN" },
] as const;

export const isServiceId = (v: string): v is ServiceId => SERVICES.some((s) => s.id === v);
export const getService = (id: string) => SERVICES.find((s) => s.id === id);
export const originOf = (s: Service) => (process.env[s.originEnv] ?? "").replace(/\/+$/, "");
