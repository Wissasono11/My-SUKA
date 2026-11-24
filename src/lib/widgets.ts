import { cookies } from "next/headers";

export interface WidgetView {
  app_id: string; summary_title: string; active_count: number; count_label: string; badge_label?: string;
  recent_items: { id: string; title: string; subtitle: string; updated_at: string }[]; action_url: string;
}

/** Ringkasan widget dari portal-api (internal). Gagal/lambat => daftar kosong, dashboard tetap tampil. */
export async function loadWidgets(): Promise<WidgetView[]> {
  const api = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const res = await fetch(`${api}/api/widget/summary`, { headers: { cookie: (await cookies()).toString(), accept: "application/json" }, cache: "no-store", signal: AbortSignal.timeout(2500) });
    if (!res.ok) return [];
    const body = (await res.json()) as { status?: string; data?: { widgets?: WidgetView[] } };
    return body.status === "success" && Array.isArray(body.data?.widgets) ? body.data.widgets : [];
  } catch {
    return [];
  }
}
