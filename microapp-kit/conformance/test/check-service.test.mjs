// Pemeriksa harus: (1) GAGAL untuk layanan rentan yang sengaja dibuat salah, (2) LULUS untuk layanan yang memakai kit.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { SignJWT, createLocalJWKSet, exportJWK, generateKeyPair } from "jose";
import * as kit from "../../node/mysuka-sso.mjs";
import { runChecks } from "../check-service.mjs";

const ISS = "https://mysuka.test", SVC = "sukaketemu", SECRET = "s".repeat(40);
const portal = await generateKeyPair("RS256");
const jwk = { ...(await exportJWK(portal.publicKey)), kid: "portal-1", alg: "RS256", use: "sig" };
const cfg = { serviceId: SVC, issuer: ISS, jwksUrl: `${ISS}/jwks`, exchangeUrl: `${ISS}/ex`, clientSecret: SECRET, production: true };
const verifier = kit.createVerifier(cfg, { keys: createLocalJWKSet({ keys: [jwk] }) });

const servers = [];
const listen = (handler) => new Promise((res) => { const s = http.createServer(handler).listen(0, "127.0.0.1", () => { servers.push(s); res(`http://127.0.0.1:${s.address().port}`); }); });
after(() => servers.forEach((s) => s.close()));
const readBody = (req) => new Promise((r) => { let d = ""; req.on("data", (c) => (d += c)); req.on("end", () => r(d)); });

// ---- layanan RENTAN: semua kesalahan umum sekaligus ----
const vulnerable = await listen(async (req, res) => {
  const url = new URL(req.url, "http://x");
  res.setHeader("X-Powered-By", "Express 4.17.1");
  res.setHeader("Access-Control-Allow-Origin", req.headers.origin ?? "*");
  res.setHeader("Access-Control-Allow-Credentials", "true");
  if (url.pathname === "/.env") return res.end("SSO_CLIENT_SECRET=abc\nDB_URL=mongodb://x\n");
  if (url.pathname === "/app.js") return res.end(`const cfg={client_secret:"${"q".repeat(40)}"};`);
  if (url.pathname.endsWith("/api/widget/summary")) { res.setHeader("content-type", "application/json"); return res.end('{"status":"success","data":{}}'); } // terima SEMUA bearer
  if (url.pathname.endsWith("/api/backchannel-logout")) { await readBody(req); return res.end("{}"); }
  if (url.pathname.endsWith("/sso-callback")) {
    res.setHeader("Set-Cookie", "sid=abc123; Path=/; Domain=.example.com");
    res.statusCode = 302; res.setHeader("Location", url.searchParams.get("next") ?? "/"); return res.end();
  }
  if (url.pathname.includes("/api/%ff") || req.url.includes("%ff")) return res.end("Error\n    at handler (/srv/node_modules/x/index.js:10:5)");
  res.setHeader("content-type", "text/html"); res.end(`<html><script src="/app.js"></script></html>`);
});

// ---- layanan AMAN: memakai kit ----
const hardened = await listen(async (req, res) => {
  const url = new URL(req.url, "http://x");
  for (const [k, v] of Object.entries(kit.securityHeaders({ sensitive: true, hsts: false }))) res.setHeader(k, v);
  const deny = (code = 401) => { res.statusCode = code; res.end("{}"); };
  if (url.pathname.endsWith("/api/widget/summary")) {
    try { await verifier.verifyWidget((req.headers.authorization ?? "").replace(/^Bearer /i, "")); res.end('{"status":"success"}'); } catch { deny(); }
    return;
  }
  if (url.pathname.endsWith("/api/backchannel-logout")) {
    const t = new URLSearchParams(await readBody(req)).get("logout_token");
    try { await verifier.verifyLogout(t ?? ""); res.end("{}"); } catch { deny(400); }
    return;
  }
  if (url.pathname.endsWith("/sso-callback")) return deny(401); // tanpa exchange sah: tidak ada sesi, tidak ada redirect
  if (url.pathname === "/.env" || url.pathname === "/.git/config") return deny(404);
  res.setHeader("content-type", "text/html"); res.end(`<html><script src="/app.js"></script></html>`);
});
const widgetTokenFor = (svc) => {
  const now = Math.floor(Date.now() / 1000);
  return new SignJWT({ iss: ISS, aud: svc, iat: now, exp: now + 60, jti: crypto.randomUUID().replaceAll("-", ""), sub: "usr_x", sid: "sid_x", typ: "widget", svc, user: {} })
    .setProtectedHeader({ alg: "RS256", kid: "portal-1" }).sign(portal.privateKey);
};
const common = { service: SVC, issuer: ISS, widget: true, backchannel: `/${SVC}/api/backchannel-logout`, sensitive: true, secret: SECRET };
const level = (res, id) => res.find((r) => r.id === id)?.level;

test("layanan rentan: pemeriksa menandai semua kesalahan utama sebagai FAIL", async () => {
  const res = await runChecks({ ...common, base: vulnerable, foreignToken: await widgetTokenFor("paas") });
  for (const id of ["T01", "T02", "T03", "T05", "T06", "T08", "T09", "T10", "T11", "T12", "T13", "T18", "T20", "T21", "T23"]) {
    assert.equal(level(res, id), "FAIL", `${id} seharusnya FAIL: ${JSON.stringify(res.find((r) => r.id === id))}`);
  }
  assert.equal(level(res, "T16"), "WARN"); assert.equal(level(res, "T22"), "WARN");
});

test("layanan aman (kit): tidak ada FAIL, token layanan lain ditolak karena aud", async () => {
  const res = await runChecks({ ...common, base: hardened, foreignToken: await widgetTokenFor("paas") });
  const fails = res.filter((r) => r.level === "FAIL");
  assert.deepEqual(fails, [], JSON.stringify(fails));
  assert.equal(level(res, "T05"), "PASS"); assert.equal(level(res, "T10"), "PASS"); assert.equal(level(res, "T21"), "PASS");
  // kontrol positif: token layanan ini sendiri DITERIMA, jadi penolakan T05 benar-benar karena aud
  const ok = await fetch(`${hardened}/${SVC}/api/widget/summary`, { headers: { authorization: `Bearer ${await widgetTokenFor(SVC)}` } });
  assert.equal(ok.status, 200);
});

test("tanpa --issuer uji token palsu di-SKIP, bukan lulus palsu", async () => {
  const res = await runChecks({ ...common, issuer: undefined, base: vulnerable });
  assert.deepEqual(["T02", "T03", "T04"].map((id) => level(res, id)), ["SKIP", "SKIP", "SKIP"]);
});
