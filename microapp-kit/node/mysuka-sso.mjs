// Kit keamanan SSO My-SUKA untuk backend layanan Node (Express, Fastify, Nuxt/Nitro, Next route handler).
// Satu berkas, satu dependensi (`jose`). Semua pemeriksaan gagal tertutup: algoritma dikunci RS256, iss, aud (persis id
// layanan), typ, svc, exp, iat, umur maksimum, jti sekali pakai, serta aturan OIDC Back-Channel Logout.
// Salin berkas ini ke layanan Anda dan JANGAN menulis ulang verifikasinya sendiri.
import { createHash, randomBytes } from "node:crypto";
import { createRemoteJWKSet, decodeProtectedHeader, jwtVerify } from "jose";

export const BACKCHANNEL_EVENT = "http://schemas.openid.net/event/backchannel-logout";
const MAX_TOKEN_LIFETIME = 120; // detik; portal menerbitkan 60
const CLOCK_TOLERANCE = 5;

export class SsoError extends Error {
  constructor(message) { super(message); this.name = "SsoError"; }
}

export function loadConfig(env = process.env) {
  const need = ["SSO_SERVICE_ID", "SSO_ISSUER", "SSO_JWKS_URL", "SSO_EXCHANGE_URL", "SSO_CLIENT_SECRET"];
  const missing = need.filter((k) => !env[k]);
  if (missing.length) throw new SsoError(`environment belum lengkap: ${missing.join(", ")}`);
  const cfg = {
    serviceId: env.SSO_SERVICE_ID, issuer: env.SSO_ISSUER.replace(/\/+$/, ""), jwksUrl: env.SSO_JWKS_URL,
    exchangeUrl: env.SSO_EXCHANGE_URL, clientSecret: env.SSO_CLIENT_SECRET,
    production: !["development", "test"].includes((env.ENV ?? env.NODE_ENV ?? "production").toLowerCase()),
  };
  validateConfig(cfg);
  return cfg;
}

export function validateConfig(cfg) {
  if (!cfg.clientSecret || cfg.clientSecret.length < 32) throw new SsoError("SSO_CLIENT_SECRET minimal 32 karakter");
  for (const [name, value] of [["SSO_ISSUER", cfg.issuer], ["SSO_JWKS_URL", cfg.jwksUrl], ["SSO_EXCHANGE_URL", cfg.exchangeUrl]]) {
    let u; try { u = new URL(value); } catch { throw new SsoError(`${name} bukan URL yang valid`); }
    const local = ["localhost", "127.0.0.1", "portal-api"].includes(u.hostname);
    if (!["https:", "http:"].includes(u.protocol)) throw new SsoError(`${name} bukan URL yang valid`);
    if (cfg.production && u.protocol !== "https:" && !local) throw new SsoError(`${name} wajib https di produksi`);
  }
}

// ---------------------------------------------------------------------------------- anti-replay (`jti`)
export class MemoryReplayCache {
  #seen = new Map(); #max;
  constructor(max = 50_000) { this.#max = max; }
  /** Atomik (satu event loop): true bila sudah pernah dicatat; bila belum, catat selama ttl detik. */
  seenBefore(key, ttl) {
    const now = Date.now();
    if (this.#seen.size >= this.#max) {
      for (const [k, exp] of this.#seen) if (exp <= now) this.#seen.delete(k);
      while (this.#seen.size >= this.#max) this.#seen.delete(this.#seen.keys().next().value);
    }
    const exp = this.#seen.get(key);
    if (exp !== undefined && exp > now) return true;
    this.#seen.set(key, now + ttl * 1000);
    return false;
  }
}

/** Redis (ioredis / node-redis v4+): SET NX EX. Wajib untuk >1 instance. */
export class RedisReplayCache {
  constructor(client, prefix = "sso:jti:") { this.client = client; this.prefix = prefix; }
  async seenBefore(key, ttl) { return (await this.client.set(this.prefix + key, "1", { NX: true, EX: ttl })) === null; }
}

// ---------------------------------------------------------------------------------- verifikasi token
export function createVerifier(cfg, { keys, replay } = {}) {
  validateConfig(cfg);
  const getKey = keys ?? createRemoteJWKSet(new URL(cfg.jwksUrl), { cooldownDuration: 30_000, timeoutDuration: 3_000 });
  const seen = replay ?? new MemoryReplayCache();

  async function decode(token, { headerTyp } = {}) {
    if (typeof token !== "string" || !token || token.length > 8192) throw new SsoError("token kosong atau terlalu panjang");
    let payload;
    try {
      if (decodeProtectedHeader(token).alg !== "RS256") throw new SsoError("alg bukan RS256"); // tolak none/HS*/ES*
      ({ payload } = await jwtVerify(token, getKey, {
        algorithms: ["RS256"], issuer: cfg.issuer, audience: cfg.serviceId, clockTolerance: CLOCK_TOLERANCE,
        requiredClaims: ["exp", "iat", "iss", "aud", "sub", "jti"], ...(headerTyp ? { typ: headerTyp } : {}),
      }));
    } catch (e) {
      if (e instanceof SsoError) throw e;
      throw new SsoError(`token ditolak: ${e?.code ?? e?.name ?? "error"}`);
    }
    if (payload.aud !== cfg.serviceId) throw new SsoError("aud bukan layanan ini"); // jose menerima daftar aud; wajib persis satu
    if (typeof payload.jti !== "string" || typeof payload.sub !== "string") throw new SsoError("jti/sub bukan string");
    if (payload.exp - payload.iat > MAX_TOKEN_LIFETIME) throw new SsoError("umur token melebihi batas");
    return payload;
  }
  const once = async (payload, scope) => {
    const ttl = Math.max(1, Math.ceil(payload.exp - Date.now() / 1000) + CLOCK_TOLERANCE + 1);
    if (await seen.seenBefore(`${scope}:${payload.jti}`, ttl)) throw new SsoError("jti sudah dipakai (replay)");
  };
  const claims = (p) => ({ sub: p.sub, sid: typeof p.sid === "string" ? p.sid : "", role: p.user?.primary_role ?? null, user: p.user ?? {}, jti: p.jti, raw: p });

  return {
    /** JWT hasil POST /api/sso/exchange. Sekali pakai. */
    async verifyHandoff(token) {
      const p = await decode(token);
      if (p.typ !== "handoff" || p.svc !== cfg.serviceId) throw new SsoError("bukan token handoff untuk layanan ini");
      if (typeof p.sid !== "string" || !p.sid) throw new SsoError("sid tidak ada");
      await once(p, "handoff");
      return claims(p);
    },
    /** Bearer pada GET /<layanan>/api/widget/summary. Tidak sekali pakai. */
    async verifyWidget(token) {
      const p = await decode(token);
      if (p.typ !== "widget" || p.svc !== cfg.serviceId) throw new SsoError("bukan token widget untuk layanan ini");
      return claims(p);
    },
    /** `logout_token` pada POST /<layanan>/api/backchannel-logout (OIDC BCL 1.0 §2.6). */
    async verifyLogout(token) {
      const p = await decode(token, { headerTyp: "logout+jwt" });
      if (!p.events || typeof p.events !== "object" || !(BACKCHANNEL_EVENT in p.events)) throw new SsoError("events tidak memuat backchannel-logout");
      if ("nonce" in p) throw new SsoError("logout token tidak boleh memuat nonce");
      if (typeof p.sid !== "string" || !p.sid) throw new SsoError("sid tidak ada");
      await once(p, "logout");
      return claims(p);
    },
  };
}

// ---------------------------------------------------------------------------------- exchange + PKCE
export function newPkce() {
  const verifier = randomBytes(48).toString("base64url");
  return { verifier, challenge: createHash("sha256").update(verifier).digest("base64url") };
}

export async function exchangeCode(cfg, code, codeVerifier, { fetchImpl = fetch } = {}) {
  if (typeof code !== "string" || code.length < 20 || code.length > 200) throw new SsoError("code tidak valid");
  let res;
  try {
    res = await fetchImpl(cfg.exchangeUrl, {
      method: "POST", headers: { "content-type": "application/json" }, redirect: "error", // rahasia tak boleh ikut ke host lain
      body: JSON.stringify({ code, client_id: cfg.serviceId, client_secret: cfg.clientSecret, ...(codeVerifier ? { code_verifier: codeVerifier } : {}) }),
      signal: AbortSignal.timeout(3000),
    });
  } catch (e) { throw new SsoError(`exchange gagal: ${e?.name ?? "error"}`); }
  if (res.status !== 200) throw new SsoError(`exchange ditolak: ${res.status}`);
  const data = await res.json().catch(() => null);
  if (!data || typeof data.token !== "string" || data.token_type !== "Bearer") throw new SsoError("respons exchange tidak sah");
  return data.token;
}

// ---------------------------------------------------------------------------------- cookie, header, redirect
/** Produksi: __Host- (Secure, Path=/, tanpa Domain => host-only), HttpOnly, SameSite=Lax. Jangan pernah mengisi `domain`. */
export function sessionCookie(cfg, name = "session") {
  return { name: cfg.production ? `__Host-${name}` : name, options: { httpOnly: true, secure: cfg.production, sameSite: "lax", path: "/" } };
}

export function securityHeaders({ sensitive = false, hsts = true } = {}) {
  const h = {
    "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
    "Referrer-Policy": sensitive ? "same-origin" : "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()", "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
  };
  if (hsts) h["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains";
  if (sensitive) h["Cache-Control"] = "no-store";
  return h;
}

/** Middleware Express: pasang PALING ATAS. Juga mematikan X-Powered-By. */
export function expressSecurity(opts) {
  const h = securityHeaders(opts);
  return (req, res, next) => { res.removeHeader("X-Powered-By"); for (const [k, v] of Object.entries(h)) res.setHeader(k, v); next(); };
}

export function safeNext(value, fallback = "/") {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") || /[\u0000-\u001f]/.test(value)) return fallback;
  return value;
}
