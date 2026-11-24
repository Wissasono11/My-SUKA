import { cookies } from "next/headers";
import { createRemoteJWKSet } from "jose";
import { verifySessionToken, type SsoUser } from "./verify";
import { sessionCookieName } from "./cookie";

export type { SsoUser } from "./verify";

let jwks: ReturnType<typeof createRemoteJWKSet> | null = null;
const remoteKeys = () => (jwks ??= createRemoteJWKSet(new URL(process.env.SSO_JWKS_URL ?? "http://127.0.0.1:8000/.well-known/jwks.json"), { cooldownDuration: 30_000, timeoutDuration: 2_000 }));

export async function getSessionUser(): Promise<SsoUser | null> {
  const token = (await cookies()).get(sessionCookieName())?.value;
  return token ? verifySessionToken(token, remoteKeys()) : null;
}
