import { NextResponse, type NextRequest } from "next/server";

/**
 * Gateway guard untuk rute layanan. Cookie sesi portal TIDAK diteruskan ke upstream:
 * tiap micro-app punya sesinya sendiri hasil /sso-callback (kontrak 2.3), dan SISKA wajib terisolasi.
 */
const SESSION = /(?:^|;\s*)(?:__Host-)?mysuka_(?:session|oidc)=[^;]*/g;

export function middleware(req: NextRequest) {
  const headers = new Headers(req.headers);
  const cookie = headers.get("cookie");
  if (cookie) {
    const cleaned = cookie.replace(SESSION, "").replace(/^;\s*/, "").trim();
    if (cleaned) headers.set("cookie", cleaned); else headers.delete("cookie");
  }
  headers.delete("x-middleware-subrequest");
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: ["/(sukaketemu|campusfix|siska|archive|paas)", "/(sukaketemu|campusfix|siska|archive|paas)/:path*"] };
