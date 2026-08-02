import { NextRequest, NextResponse } from "next/server";

// Defense-in-depth only: the real RBAC gate is the API (process isolation +
// require_role + row checks). This just avoids flashing protected UI before
// a 401 comes back, and bounces unauthenticated visitors to /login.
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === "/login") return NextResponse.next();

  // api-admin sets "admin_access_token" (namespaced per api-public/api-admin
  // instance — see settings.ACCESS_TOKEN_COOKIE in the API — so a customer
  // and staff session on the same "localhost" host can't clobber each
  // other's cookie). This was still checking the old shared "access_token"
  // name, so it never saw a session as logged-in post-login and bounced
  // straight back to /login every time — a login-then-redirect loop with
  // otherwise-correct credentials.
  const hasSession = request.cookies.has("admin_access_token");
  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
