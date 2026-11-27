#!/usr/bin/env node
// Uji keamanan black-box untuk SATU layanan di ekosistem My-SUKA. Tiap tim menjalankannya terhadap staging layanannya
// sendiri (dan CI); hasilnya FAIL/WARN/PASS per pemeriksaan. Tidak mengirim eksploit destruktif: hanya token palsu,
// path umum, dan pembacaan header/cookie/bundel.
//
//   node microapp-kit/conformance/check-service.mjs --base https://staging.layanan.example --service sukaketemu \
//        --issuer https://mysuka.portal.ac.id --widget --yes
//
// Opsi:  --widget                      layanan punya GET /<id>/api/widget/summary
//        --backchannel <path>          path back-channel logout (mis. /sukaketemu/api/backchannel-logout)
//        --callback <path>             default /<id>/sso-callback
//        --issuer <url>                SSO_ISSUER portal (wajib untuk uji token palsu agar penolakan karena TANDA TANGAN)
//        --jwks-url <url>              JWKS portal: mengaktifkan uji alg-confusion HS256
//        --foreign-token-env <VAR>     env berisi token widget SAH dari portal untuk layanan LAIN (uji aud lintas layanan)
//        --secret-env <VAR>            env berisi SSO_CLIENT_SECRET layanan ini: dicari di bundel frontend
//        --sensitive                   layanan sensitif (SISKA): cache no-store, cookie tanpa Domain, referrer same-origin
//        --json                        keluaran JSON      --yes   konfirmasi: Anda berwenang menguji target ini
// Kode keluar 1 bila ada FAIL.
import { SignJWT, exportJWK, generateKeyPair } from "jose";
import { createHmac } from "node:crypto";
import { parseArgs } from "node:util";

const b64 = (o) => Buffer.from(typeof o === "string" ? o : JSON.stringify(o)).toString("base64url");
const claims = (iss, svc, typ = "widget") => {
  const now = Math.floor(Date.now() / 1000);
  return { iss, aud: svc, iat: now, exp: now + 60, jti: "c".repeat(32), sub: "usr_conformance", sid: "sid_conformance", typ, svc, user: { id: "usr_conformance", primary_role: "MAHASISWA" } };
};
const SECRET_PATTERNS = [
  [/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/, "kunci privat"], [/GOCSPX-[A-Za-z0-9_-]{20,}/, "rahasia Google OAuth"],
  [/AKIA[0-9A-Z]{16}/, "kunci AWS"], [/SSO_CLIENT_SECRET/, "nama variabel SSO_CLIENT_SECRET"],
  [/client_?secret["']?\s*[:=]\s*["'][^"']{20,}["']/i, "client_secret tertanam"],
];
const TRACE = /Traceback \(most recent|\bat [^\n]+\.(?:js|ts|mjs):\d+:\d+|node_modules\/|SQLSTATE|MongoServerError|stack trace|FirebaseError/i;

export async function runChecks(o) {
  const out = [];
  const add = (id, title, level, detail = "") => out.push({ id, title, level, detail });
  const base = o.base.replace(/\/+$/, ""), svc = o.service, https = base.startsWith("https://");
  const cb = o.callback ?? `/${svc}/sso-callback`, widgetPath = `/${svc}/api/widget/summary`;
  const cookiesSeen = [];
  async function req(path, init = {}) {
    const res = await fetch(base + path, { redirect: "manual", signal: AbortSignal.timeout(8000), ...init });
    const set = res.headers.getSetCookie?.() ?? [];
    cookiesSeen.push(...set.map((c) => ({ path, c })));
    let text = ""; try { text = (await res.text()).slice(0, 2_000_000); } catch { /* ignore */ }
    return { status: res.status, headers: res.headers, text, set };
  }
  const ok2xx = (s) => s >= 200 && s < 300;

  // ---- token palsu pada endpoint widget (aud/tanda tangan/alg) ----
  if (o.widget) {
    const bearer = (t) => ({ headers: { authorization: `Bearer ${t}` } });
    let r = await req(widgetPath);
    add("T01", "widget tanpa Authorization ditolak", ok2xx(r.status) ? "FAIL" : "PASS", `status ${r.status}`);
    if (!o.issuer) {
      for (const id of ["T02", "T03", "T04"]) add(id, "uji token palsu", "SKIP", "butuh --issuer (agar penolakan pasti karena tanda tangan, bukan iss salah)");
    } else {
      r = await req(widgetPath, bearer(`${b64({ alg: "none", typ: "JWT" })}.${b64(claims(o.issuer, svc))}.`));
      add("T02", "token alg=none ditolak", ok2xx(r.status) ? "FAIL" : "PASS", `status ${r.status}`);
      const atk = await generateKeyPair("RS256");
      const forged = await new SignJWT(claims(o.issuer, svc)).setProtectedHeader({ alg: "RS256", kid: "attacker" }).sign(atk.privateKey);
      r = await req(widgetPath, bearer(forged));
      add("T03", "token bertanda tangan kunci penyerang ditolak", ok2xx(r.status) ? "FAIL" : "PASS", `status ${r.status}`);
      if (o.jwksUrl) {
        try {
          const jwks = await (await fetch(o.jwksUrl, { signal: AbortSignal.timeout(5000) })).json();
          const key = jwks.keys[0], head = b64({ alg: "HS256", typ: "JWT", kid: key.kid }), body = b64(claims(o.issuer, svc));
          // alg-confusion klasik: HMAC memakai kunci publik (JWK serialisasi) sebagai rahasia.
          for (const secret of [JSON.stringify(key), key.n]) {
            const t = `${head}.${body}.${createHmac("sha256", secret).update(`${head}.${body}`).digest("base64url")}`;
            r = await req(widgetPath, bearer(t));
            if (ok2xx(r.status)) break;
          }
          add("T04", "alg-confusion HS256 ditolak", ok2xx(r.status) ? "FAIL" : "PASS", `status ${r.status}`);
        } catch (e) { add("T04", "alg-confusion HS256", "SKIP", `JWKS tidak terbaca: ${e.name}`); }
      } else add("T04", "alg-confusion HS256", "SKIP", "butuh --jwks-url");
    }
    const foreign = o.foreignToken ?? (o.foreignTokenEnv ? process.env[o.foreignTokenEnv] : undefined);
    if (foreign) {
      r = await req(widgetPath, bearer(foreign));
      add("T05", "token SAH untuk layanan lain ditolak (aud dicek)", ok2xx(r.status) ? "FAIL" : "PASS", `status ${r.status}`);
    } else add("T05", "token sah layanan lain ditolak (aud)", "SKIP", "butuh --foreign-token-env (token widget sah dari portal untuk layanan LAIN)");
  }

  // ---- sso-callback ----
  let r = await req(`${cb}?code=${"x".repeat(32)}`);
  const loc = r.headers.get("location") ?? "";
  add("T06", "kode sampah tidak membuat sesi dan tidak 5xx", r.set.length ? "FAIL" : r.status >= 500 ? "WARN" : "PASS", `status ${r.status}${r.set.length ? ", Set-Cookie dikirim" : ""}`);
  add("T07", "tidak ada token/JWT di URL redirect", /token=|eyJ[A-Za-z0-9_-]{10,}/.test(loc) ? "FAIL" : "PASS", loc ? `Location: ${loc.slice(0, 80)}` : "tanpa Location");
  const atk2 = await generateKeyPair("RS256");
  const legacy = await new SignJWT(claims(o.issuer ?? base, svc, "handoff")).setProtectedHeader({ alg: "RS256", kid: "attacker" }).sign(atk2.privateKey);
  r = await req(`${cb}?token=${legacy}`);
  add("T08", "mode lama ?token= palsu tidak membuat sesi", r.set.length ? "FAIL" : "PASS", `status ${r.status}`);
  r = await req(`${cb}?code=${"y".repeat(32)}&next=https://evil.example/&returnTo=https://evil.example/&redirect=https://evil.example/`);
  const evil = (r.headers.get("location") ?? "").match(/^https?:\/\/([^/]+)/)?.[1] ?? "";
  add("T09", "tidak ada open redirect lewat next/returnTo", evil.includes("evil.example") ? "FAIL" : "PASS", evil ? `redirect ke ${evil}` : "aman");

  // ---- back-channel logout ----
  if (o.backchannel) {
    const form = (t) => ({ method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: `logout_token=${encodeURIComponent(t)}` });
    r = await req(o.backchannel, form(`${b64({ alg: "none", typ: "logout+jwt" })}.${b64({ iss: o.issuer ?? base, aud: svc, sub: "x", sid: "s", jti: "j", iat: 1, events: { "http://schemas.openid.net/event/backchannel-logout": {} } })}.`));
    const r2 = await req(o.backchannel, { method: "POST" });
    add("T10", "back-channel logout menolak token palsu dan permintaan kosong", ok2xx(r.status) || ok2xx(r2.status) ? "FAIL" : "PASS", `palsu ${r.status}, kosong ${r2.status}`);
  } else add("T10", "back-channel logout", "SKIP", "tanpa --backchannel (sangat disarankan: tanpa ini logout portal tidak mematikan sesi layanan)");

  // ---- CORS, header, metode ----
  const page = await req(`/${svc}/`, { headers: { origin: "https://evil.example" } });
  const acao = page.headers.get("access-control-allow-origin"), acac = page.headers.get("access-control-allow-credentials");
  add("T11", "CORS tidak memantulkan origin asing / wildcard berkredensial", (acao === "https://evil.example" || (acao === "*" && acac === "true")) ? "FAIL" : acao === "*" ? "WARN" : "PASS", `ACAO=${acao ?? "-"} ACAC=${acac ?? "-"}`);
  const h = (k) => page.headers.get(k);
  const csp = h("content-security-policy") ?? "";
  add("T12", "X-Content-Type-Options: nosniff", h("x-content-type-options")?.toLowerCase() === "nosniff" ? "PASS" : "FAIL");
  add("T13", "anti-clickjacking (X-Frame-Options atau frame-ancestors)", /deny|sameorigin/i.test(h("x-frame-options") ?? "") || /frame-ancestors/i.test(csp) ? "PASS" : "FAIL");
  add("T14", "Referrer-Policy diset", h("referrer-policy") ? (o.sensitive && !/(same-origin|no-referrer)/i.test(h("referrer-policy")) ? "FAIL" : "PASS") : (o.sensitive ? "FAIL" : "WARN"), h("referrer-policy") ?? "tidak ada");
  add("T15", "HSTS (hanya https)", !https ? "SKIP" : /max-age=\d{7,}/.test(h("strict-transport-security") ?? "") ? "PASS" : "WARN", h("strict-transport-security") ?? "tidak ada");
  add("T16", "tidak membocorkan teknologi (X-Powered-By / versi Server)", h("x-powered-by") || /\d+\.\d+/.test(h("server") ?? "") ? "WARN" : "PASS", `${h("x-powered-by") ?? ""} ${h("server") ?? ""}`.trim());
  add("T17", "CSP tanpa unsafe-eval dan tanpa sumber wildcard", !csp ? "WARN" : /unsafe-eval|(?:script-src|default-src)[^;]*\s\*(?:\s|;|$)/.test(csp) ? "FAIL" : "PASS", csp ? csp.slice(0, 80) : "tidak ada CSP");
  if (o.sensitive) add("T18", "layanan sensitif: Cache-Control no-store", /no-store/i.test(h("cache-control") ?? "") ? "PASS" : "FAIL", h("cache-control") ?? "tidak ada");
  r = await req(`/${svc}/`, { method: "TRACE" }).catch(() => ({ status: 0 }));
  add("T19", "metode TRACE dimatikan", ok2xx(r.status) ? "WARN" : "PASS", `status ${r.status}`);

  // ---- berkas sensitif (cek ISI: SPA yang mengembalikan index.html untuk semua path bukan temuan) ----
  const probes = [["/.env", /^[A-Z][A-Z0-9_]{2,}=/m, ".env"], ["/.git/config", /\[core\]/, ".git/config"], ["/.git/HEAD", /^ref: refs\//, ".git/HEAD"],
    ["/docker-compose.yml", /^services:/m, "docker-compose.yml"], [`/${svc}/.env`, /^[A-Z][A-Z0-9_]{2,}=/m, `${svc}/.env`], ["/serviceAccountKey.json", /"private_key"/, "serviceAccountKey.json"]];
  const hits = [];
  for (const [p, re, name] of probes) { const x = await req(p).catch(() => ({ status: 0, text: "" })); if (ok2xx(x.status) && re.test(x.text)) hits.push(name); }
  add("T20", "berkas rahasia/VCS tidak terpapar", hits.length ? "FAIL" : "PASS", hits.join(", "));

  // ---- rahasia di bundel frontend ----
  const html = await req(`/${svc}/`);
  const srcs = [...html.text.matchAll(/<script[^>]+src=["']([^"']+)["']/gi)].map((m) => m[1]).filter((s) => !/^(https?:)?\/\//.test(s) || s.startsWith(base)).slice(0, 15);
  const exact = o.secret ?? (o.secretEnv ? process.env[o.secretEnv] : undefined);
  const found = [];
  for (const src of ["", ...srcs]) {
    const text = src ? (await req(src.startsWith("/") ? src : `/${svc}/${src}`).catch(() => ({ text: "" }))).text : html.text;
    for (const [re, label] of SECRET_PATTERNS) if (re.test(text)) found.push(`${label}${src ? ` di ${src}` : ""}`);
    if (exact && exact.length >= 16 && text.includes(exact)) found.push(`client_secret PERSIS di ${src || "halaman"}`);
  }
  add("T21", "tidak ada rahasia di HTML/JS yang dikirim ke browser", found.length ? "FAIL" : "PASS", [...new Set(found)].join("; ") || `${srcs.length} skrip diperiksa`);

  // ---- kebocoran galat ----
  const err = await req(`/${svc}/api/%ff?x='"<`).catch(() => ({ text: "" }));
  add("T22", "galat tidak membocorkan stack trace / query", TRACE.test(err.text) ? "WARN" : "PASS");

  // ---- cookie yang pernah dikirim selama pemeriksaan ----
  const bad = [];
  for (const { c } of cookiesSeen) {
    const name = c.split("=")[0];
    if (https && !/;\s*secure/i.test(c)) bad.push(`${name}: tanpa Secure`);
    if (!/;\s*samesite=(lax|strict)/i.test(c)) bad.push(`${name}: SameSite bukan Lax/Strict`);
    if (!/;\s*httponly/i.test(c)) bad.push(`${name}: tanpa HttpOnly`);
    if (/;\s*domain=/i.test(c)) bad.push(`${name}: memakai Domain= (tidak host-only)`);
  }
  add("T23", "cookie yang diset aman (Secure, HttpOnly, SameSite, host-only)", bad.length ? "FAIL" : "PASS", bad.length ? [...new Set(bad)].join("; ") : cookiesSeen.length ? `${cookiesSeen.length} cookie diperiksa` : "tidak ada cookie diset pada probe anonim");
  return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { values: v } = parseArgs({ options: {
    base: { type: "string" }, service: { type: "string" }, issuer: { type: "string" }, "jwks-url": { type: "string" }, callback: { type: "string" },
    backchannel: { type: "string" }, "foreign-token-env": { type: "string" }, "secret-env": { type: "string" },
    widget: { type: "boolean" }, sensitive: { type: "boolean" }, json: { type: "boolean" }, yes: { type: "boolean" } } });
  if (!v.base || !v.service) { console.error("pakai: --base <url> --service <id> [opsi]  (lihat komentar di berkas ini)"); process.exit(2); }
  if (!v.yes) { console.error("Tambahkan --yes untuk menegaskan Anda berwenang menguji target ini (staging/layanan sendiri)."); process.exit(2); }
  const res = await runChecks({ base: v.base, service: v.service, issuer: v.issuer, jwksUrl: v["jwks-url"], callback: v.callback, backchannel: v.backchannel,
    foreignTokenEnv: v["foreign-token-env"], secretEnv: v["secret-env"], widget: v.widget, sensitive: v.sensitive });
  if (v.json) console.log(JSON.stringify(res, null, 2));
  else for (const r of res) console.log(`[${r.level.padEnd(4)}] ${r.id} ${r.title}${r.detail ? ` — ${r.detail}` : ""}`);
  const fails = res.filter((r) => r.level === "FAIL").length, warns = res.filter((r) => r.level === "WARN").length;
  if (!v.json) console.log(`\n${fails} FAIL, ${warns} WARN, ${res.filter((r) => r.level === "SKIP").length} SKIP`);
  process.exit(fails ? 1 : 0);
}
