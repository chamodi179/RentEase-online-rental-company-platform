import { NextRequest, NextResponse } from "next/server";

// Defense-in-depth only: the real RBAC gate is the API (process isolation +
// require_role + row checks). This just avoids flashing protected UI before
// a 401 comes back, and bounces unauthenticated visitors to /login.
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === "/login") return NextResponse.next();

  const hasSession = request.cookies.has("access_token");
  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
