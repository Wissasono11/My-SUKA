/**
 * Nama cookie sesi harus sama untuk portal-api (FastAPI) dan portal-web (Next).
 * Keduanya menurunkannya dari variabel ENV yang sama, bukan NODE_ENV, agar `npm start` + API dev tidak saling tidak cocok.
 * `SESSION_COOKIE_NAME` menimpa bila diisi (harus identik di kedua sisi).
 * Aman secara bawaan (sama dengan portal-api): hanya ENV=development|test yang non-produksi; ENV kosong/salah eja = produksi.
 */
export const isNonProduction = (env: Record<string, string | undefined> = process.env): boolean => env.ENV === "development" || env.ENV === "test";

export function sessionCookieName(env: Record<string, string | undefined> = process.env): string {
  if (env.SESSION_COOKIE_NAME) return env.SESSION_COOKIE_NAME;
  return isNonProduction(env) ? "mysuka_session" : "__Host-mysuka_session";
}
