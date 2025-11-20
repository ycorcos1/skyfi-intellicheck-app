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
  const { pathname } = request.nextUrl;

  // Allow static assets and public routes - let client-side handle auth
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // For protected routes, only do a basic check
  // Let the client-side ProtectedLayout handle the actual redirect logic
  // This prevents server/client auth state mismatches
  const authStatus = getAuthStatus(request);

  // Only redirect if we have an expired/invalid token AND we're not already on login
  // This is a safety check - the client will handle the actual auth flow
  if (authStatus === "expired" || authStatus === "invalid") {
    if (pathname !== "/login") {
      const redirectUrl = new URL("/login", request.url);
      const response = NextResponse.redirect(redirectUrl);
      response.cookies.delete(AUTH_COOKIE_NAME);
      return response;
    }
  }

  // For all other cases, let the client handle it
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt).*)"],
};

