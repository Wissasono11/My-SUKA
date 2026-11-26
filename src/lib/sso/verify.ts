import { jwtVerify, type JWTVerifyGetKey } from "jose";

export type PrimaryRole = "MAHASISWA" | "DOSEN" | "STAF" | "ADMIN";
export interface SsoUser {
  id: string; nim_nip: string; email: string; name: string;
  primary_role: PrimaryRole; faculty: string; department: string; picture_url?: string;
}

/** Audience token SESI portal. Token serah-terima layanan memakai aud = id layanan dan ditolak di sini. */
export const SESSION_AUDIENCE = "mysuka-portal";
export const issuer = () => (process.env.SSO_ISSUER ?? process.env.APP_BASE_URL ?? "http://localhost:3000").replace(/\/+$/, "");

/** Token ditandatangani portal-api (FastAPI). Next hanya memverifikasi lewat JWKS; tidak memegang kunci privat. */
export async function verifySessionToken(token: string, keys: JWTVerifyGetKey, expectedIssuer = issuer()): Promise<SsoUser | null> {
  try {
    const { payload } = await jwtVerify(token, keys, { issuer: expectedIssuer, audience: SESSION_AUDIENCE, algorithms: ["RS256"], requiredClaims: ["exp", "iat", "sub", "jti", "sid"] });
    if (payload.typ !== "session" || typeof payload.sid !== "string") return null; // tolak token serah-terima/widget
    const user = payload.user as SsoUser | undefined;
    return user && typeof user.id === "string" && typeof user.email === "string"
      ? { ...user, picture_url: typeof user.picture_url === "string" && user.picture_url.startsWith("https://") ? user.picture_url : undefined }
      : null;
  } catch {
    return null;
  }
}
