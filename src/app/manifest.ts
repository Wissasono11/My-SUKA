import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return { name: "MySuka", short_name: "MySuka", description: "Portal layanan digital UIN Sunan Kalijaga", lang: "id", start_url: "/", display: "standalone", background_color: "#F8FAFC", theme_color: "#155E38",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }] };
}
