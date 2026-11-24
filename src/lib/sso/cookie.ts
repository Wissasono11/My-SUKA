/**
 * Nama cookie sesi harus sama untuk portal-api (FastAPI) dan portal-web (Next).
 * Keduanya menurunkannya dari variabel ENV yang sama, bukan NODE_ENV, agar `npm start` + API dev tidak saling tidak cocok.
 * `SESSION_COOKIE_NAME` menimpa bila diisi (harus identik di kedua sisi).
 */
export function sessionCookieName(env: Record<string, string | undefined> = process.env): string {
  if (env.SESSION_COOKIE_NAME) return env.SESSION_COOKIE_NAME;
  return env.ENV === "production" ? "__Host-mysuka_session" : "mysuka_session";
}
