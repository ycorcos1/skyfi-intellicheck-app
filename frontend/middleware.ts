import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { decodeJwt } from "jose";

const AUTH_COOKIE_NAME = "skyfi-auth";
const PUBLIC_PATHS = new Set(["/login", "/favicon.ico", "/robots.txt"]);

type AuthStatus = "none" | "valid" | "expired" | "invalid";

function isPublicPath(pathname: string) {
  if (PUBLIC_PATHS.has(pathname)) {
    return true;
  }

  return pathname.startsWith("/_next") || pathname.startsWith("/static");
}

function getAuthStatus(request: NextRequest): AuthStatus {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;

  if (!token) {
    return "none";
  }

  try {
    const payload = decodeJwt(token);

    if (!payload.exp) {
      return "invalid";
    }

    const expiresAt = payload.exp * 1000;

    if (expiresAt <= Date.now()) {
      return "expired";
    }

    return "valid";
  } catch {
    return "invalid";
  }
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Allow static assets and public routes
  if (isPublicPath(pathname)) {
    const authStatus = getAuthStatus(request);

    // Only redirect from login to dashboard if we have a valid token
    // Add a check to prevent redirect loops by checking if we're already being redirected
    if (pathname === "/login" && authStatus === "valid") {
      // Check if there's a redirectTo parameter that points back to login (loop prevention)
      const redirectTo = request.nextUrl.searchParams.get("redirectTo");
      if (redirectTo && redirectTo.startsWith("/login")) {
        // Break the loop by redirecting to dashboard without the redirectTo param
        const redirectUrl = new URL("/dashboard", request.url);
        redirectUrl.searchParams.delete("redirectTo");
        return NextResponse.redirect(redirectUrl);
      }
      const redirectUrl = new URL("/dashboard", request.url);
      return NextResponse.redirect(redirectUrl);
    }

    return NextResponse.next();
  }

  const authStatus = getAuthStatus(request);

  if (authStatus === "valid") {
    return NextResponse.next();
  }

  // Prevent redirect loops: don't redirect if we're already going to login
  if (pathname === "/login") {
    return NextResponse.next();
  }

  const redirectUrl = new URL("/login", request.url);
  const redirectTo = `${pathname}${search ?? ""}`;

  // Only add redirectTo if it's not already login to prevent loops
  if (redirectTo && redirectTo !== "/login" && !redirectTo.startsWith("/login")) {
    redirectUrl.searchParams.set("redirectTo", redirectTo);
  }

  const response = NextResponse.redirect(redirectUrl);

  if (authStatus === "expired" || authStatus === "invalid") {
    response.cookies.delete(AUTH_COOKIE_NAME);
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt).*)"],
};

