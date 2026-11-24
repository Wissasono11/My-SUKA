import type { MetadataRoute } from "next";
const base = (process.env.APP_BASE_URL ?? "http://localhost:3000").replace(/\/+$/, "");

export default function sitemap(): MetadataRoute.Sitemap {
  return ["/", "/layanan", "/tentang", "/login"].map((p) => ({ url: `${base}${p}`, changeFrequency: "monthly", priority: p === "/" ? 1 : 0.6 }));
}
