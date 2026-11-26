import { cookies } from "next/headers";
import { createRemoteJWKSet } from "jose";
import { verifySessionToken, type SsoUser } from "./verify";
import { sessionCookieName } from "./cookie";

export type { SsoUser } from "./verify";

let jwks: ReturnType<typeof createRemoteJWKSet> | null = null;
const remoteKeys = () => (jwks ??= createRemoteJWKSet(new URL(process.env.SSO_JWKS_URL ?? "http://127.0.0.1:8000/.well-known/jwks.json"), { cooldownDuration: 30_000, timeoutDuration: 2_000 }));

/** JWKS hanya membuktikan tanda tangan/kedaluwarsa, bukan pencabutan (logout). Tanyakan ke portal-api; gagal => tutup (null). */
async function sessionStillActive(token: string): Promise<boolean> {
  const api = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const res = await fetch(`${api}/api/sso/session`, { headers: { cookie: `${sessionCookieName()}=${token}` }, cache: "no-store", redirect: "manual", signal: AbortSignal.timeout(1500) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getSessionUser(): Promise<SsoUser | null> {
  const token = (await cookies()).get(sessionCookieName())?.value;
  if (!token) return null;
  const user = await verifySessionToken(token, remoteKeys());
  return user && (await sessionStillActive(token)) ? user : null;
}
