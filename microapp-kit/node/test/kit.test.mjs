import { test } from "node:test";
import assert from "node:assert/strict";
import { SignJWT, exportJWK, generateKeyPair, createLocalJWKSet } from "jose";
import * as kit from "../mysuka-sso.mjs";

const ISS = "https://mysuka.test", SVC = "sukaketemu", SECRET = "k".repeat(40);
const portal = await generateKeyPair("RS256"), attacker = await generateKeyPair("RS256");
const jwk = { ...(await exportJWK(portal.publicKey)), kid: "portal-1", alg: "RS256", use: "sig" };
const keys = createLocalJWKSet({ keys: [jwk] });
const cfg = { serviceId: SVC, issuer: ISS, jwksUrl: `${ISS}/.well-known/jwks.json`, exchangeUrl: `${ISS}/api/sso/exchange`, clientSecret: SECRET, production: true };
const verifier = () => kit.createVerifier(cfg, { keys });

async function tok({ key = portal.privateKey, alg = "RS256", kid = "portal-1", header = {}, ...over } = {}) {
  const now = Math.floor(Date.now() / 1000);
  const p = { iss: ISS, aud: SVC, iat: now, exp: now + 60, jti: crypto.randomUUID().replaceAll("-", ""), sub: "usr_abc", sid: "sid_abc", typ: "handoff", svc: SVC, user: { primary_role: "MAHASISWA" }, ...over };
  for (const k of Object.keys(p)) if (p[k] === null) delete p[k];
  return new SignJWT(p).setProtectedHeader({ alg, kid, ...header }).sign(key);
}
const logoutTok = (over = {}) => tok({ typ: undefined, svc: undefined, events: { [kit.BACKCHANNEL_EVENT]: {} }, header: { typ: "logout+jwt" }, ...over });
const rejects = (p, msg) => assert.rejects(p, (e) => e instanceof kit.SsoError && (!msg || msg.test(e.message)));

test("handoff sah, sekali pakai", async () => {
  const v = verifier(), t = await tok();
  const c = await v.verifyHandoff(t);
  assert.equal(c.sub, "usr_abc"); assert.equal(c.role, "MAHASISWA");
  await rejects(v.verifyHandoff(t), /replay/);
});

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const now = () => Math.floor(Date.now() / 1000);
const base = () => ({ iss: ISS, aud: SVC, iat: now(), exp: now() + 60, jti: "j".repeat(32), sub: "u", sid: "s", typ: "handoff", svc: SVC });
const cases = {
  "alg none": () => `${b64({ alg: "none", typ: "JWT" })}.${b64(base())}.`,
  "HS256 (kunci publik sebagai rahasia)": async () => {
    const { createHmac } = await import("node:crypto");
    const head = b64({ alg: "HS256", typ: "JWT", kid: "portal-1" }), body = b64(base());
    return `${head}.${body}.${createHmac("sha256", JSON.stringify(jwk)).update(`${head}.${body}`).digest("base64url")}`;
  },
  "ditandatangani penyerang": () => tok({ key: attacker.privateKey }),
  "kid tak dikenal": () => tok({ kid: "evil" }),
  "aud layanan lain": () => tok({ aud: "paas", svc: "paas" }),
  "aud daftar memuat layanan lain": () => tok({ aud: [SVC, "paas"] }),
  "iss lain": () => tok({ iss: "https://evil.example" }),
  "typ widget sebagai handoff": () => tok({ typ: "widget" }),
  "typ session sebagai handoff": () => tok({ typ: "session", aud: "mysuka-portal" }),
  "svc layanan lain": () => tok({ svc: "paas" }),
  "kedaluwarsa": () => tok({ iat: now() - 400, exp: now() - 200 }),
  "umur terlalu panjang": () => tok({ exp: now() + 86400 }),
  "tanpa jti": () => tok({ jti: null }),
  "tanpa sid": () => tok({ sid: null }),
  "sampah": () => "bukan.jwt.sama-sekali",
  "terlalu panjang": () => "a".repeat(9000),
  "kosong": () => "",
};
for (const [name, make] of Object.entries(cases)) test(`handoff palsu ditolak: ${name}`, async () => rejects(verifier().verifyHandoff(await make())));

test("widget tidak sekali pakai, typ & svc dikunci", async () => {
  const v = verifier(), t = await tok({ typ: "widget" });
  await v.verifyWidget(t); await v.verifyWidget(t);
  await rejects(v.verifyWidget(await tok({ typ: "handoff" })));
  await rejects(v.verifyWidget(await tok({ typ: "widget", svc: "paas" })));
});

test("logout token: sah, replay ditolak, cacat ditolak", async () => {
  const v = verifier(), t = await logoutTok();
  assert.equal((await v.verifyLogout(t)).sid, "sid_abc");
  await rejects(v.verifyLogout(t), /replay/);
  for (const over of [{ events: {} }, { events: null }, { nonce: "x" }, { sid: null }, { aud: "paas" }]) await rejects(verifier().verifyLogout(await logoutTok(over)));
  await rejects(verifier().verifyLogout(await tok({ events: { [kit.BACKCHANNEL_EVENT]: {} } }))); // header typ JWT biasa ditolak (jose: claim validation)
  await rejects(verifier().verifyHandoff(await logoutTok()));                                              // logout tidak boleh jadi login
});

test("konfigurasi menolak rahasia pendek dan http di produksi", () => {
  assert.throws(() => kit.validateConfig({ ...cfg, clientSecret: "pendek" }), kit.SsoError);
  assert.throws(() => kit.validateConfig({ ...cfg, issuer: "http://mysuka.example" }), /https/);
  kit.validateConfig({ ...cfg, issuer: "http://localhost:8000", jwksUrl: "http://localhost:8000/j", exchangeUrl: "http://localhost:8000/e" });
  assert.throws(() => kit.loadConfig({}), /belum lengkap/);
});

test("cookie sesi host-only di produksi; header sensitif; safeNext", () => {
  const c = kit.sessionCookie(cfg);
  assert.equal(c.name, "__Host-session"); assert.deepEqual(c.options, { httpOnly: true, secure: true, sameSite: "lax", path: "/" });
  assert.equal(kit.sessionCookie({ ...cfg, production: false }).name, "session");
  const h = kit.securityHeaders({ sensitive: true });
  assert.equal(h["Cache-Control"], "no-store"); assert.equal(h["Referrer-Policy"], "same-origin"); assert.match(h["Content-Security-Policy"], /frame-ancestors 'none'/);
  for (const bad of ["//evil.example", "https://evil.example", "/\\evil", "/a\nb", "", null]) assert.equal(kit.safeNext(bad, "/x"), "/x");
  assert.equal(kit.safeNext("/a?b=1"), "/a?b=1");
});

test("PKCE: challenge = base64url(sha256(verifier))", async () => {
  const { createHash } = await import("node:crypto");
  const { verifier: v, challenge } = kit.newPkce();
  assert.equal(createHash("sha256").update(v).digest("base64url"), challenge); assert.equal(challenge.length, 43);
});

test("exchange: tanpa redirect, respons tak sah ditolak", async () => {
  let seen;
  const ok = async (url, init) => { seen = { url, init }; return new Response(JSON.stringify({ token: "t", token_type: "Bearer" }), { status: 200 }); };
  assert.equal(await kit.exchangeCode(cfg, "c".repeat(30), "v".repeat(50), { fetchImpl: ok }), "t");
  assert.equal(seen.init.redirect, "error"); assert.equal(JSON.parse(seen.init.body).client_id, SVC);
  await rejects(kit.exchangeCode(cfg, "pendek"));
  for (const [status, body] of [[401, "{}"], [200, '{"token":"t"}'], [200, "bukan json"]]) {
    await rejects(kit.exchangeCode(cfg, "c".repeat(30), undefined, { fetchImpl: async () => new Response(body, { status }) }));
  }
  await rejects(kit.exchangeCode(cfg, "c".repeat(30), undefined, { fetchImpl: async () => { throw new TypeError("net"); } }), /exchange gagal/);
});

test("replay cache memori", () => {
  const c = new kit.MemoryReplayCache();
  assert.equal(c.seenBefore("a", 30), false); assert.equal(c.seenBefore("a", 30), true); assert.equal(c.seenBefore("b", 30), false);
});
