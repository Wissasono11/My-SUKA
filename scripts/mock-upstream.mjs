// Upstream tiruan untuk uji gateway lokal: mencerminkan path, cookie, dan header yang diterima.
import http from "node:http";
const [port, id] = [Number(process.argv[2]), process.argv[3]];
http.createServer((req, res) => {
  if (req.url === `/${id}/api/widget/summary`) {
    res.setHeader("content-type", "application/json");
    return res.end(JSON.stringify({ status: "success", app_id: id, data: { summary_title: "Status", active_count: 2, count_label: "Laporan Aktif", badge_label: "1 Kecocokan Baru!", recent_items: [{ id: "r1", title: "KTM Informatika", subtitle: "Dititipkan di Pos Satpam", updated_at: "2026-11-20T10:15:00Z" }], action_url: `/${id}/dashboard` }, auth: req.headers.authorization ? "bearer" : "none" }));
  }
  res.setHeader("content-type", "application/json");
  res.end(JSON.stringify({ id, url: req.url, cookie: req.headers.cookie ?? null, authorization: req.headers.authorization ?? null }));
}).listen(port, "127.0.0.1");
