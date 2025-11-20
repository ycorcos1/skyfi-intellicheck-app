"use client";

import { CognitoUserSession } from "amazon-cognito-identity-js";
import { decodeJwt, JWTPayload } from "jose";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  getCurrentSession as getCurrentCognitoSession,
  refreshSession as refreshCognitoSession,
  signIn as cognitoSignIn,
  signOut as cognitoSignOut,
} from "@/lib/cognito";

const LOCAL_STORAGE_KEY = "skyfi.intellicheck.authTokens";
const AUTH_COOKIE_NAME = "skyfi-auth";
const REFRESH_THRESHOLD_MS = 60_000; // refresh 1 minute before expiration
const REFRESH_POLL_INTERVAL_MS = 30_000;

export interface AuthUser {
  id: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  name?: string; // Keep for backward compatibility
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function parseUser(session: CognitoUserSession): AuthUser {
  const idToken = session.getIdToken().getJwtToken();
  const payload = decodeJwt(idToken) as JWTPayload & {
    email?: string;
    name?: string;
    given_name?: string;
    family_name?: string;
    "cognito:username"?: string;
  };

  const firstName = payload.given_name;
  const lastName = payload.family_name;
  const fullName = firstName && lastName ? `${firstName} ${lastName}` : undefined;

  return {
    id: (payload.sub as string) ?? "",
    email: payload.email ?? payload["cognito:username"] ?? undefined,
    firstName,
    lastName,
    name: fullName ?? payload.name ?? payload["cognito:username"] ?? undefined,
  };
}

function persistSession(session: CognitoUserSession) {
  if (typeof window === "undefined") {
    return;
  }

  const tokens = {
    accessToken: session.getAccessToken().getJwtToken(),
    idToken: session.getIdToken().getJwtToken(),
    refreshToken: session.getRefreshToken().getToken(),
    expiresAt: session.getAccessToken().getExpiration() * 1000,
  };

  window.localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(tokens));
  writeAuthCookie(tokens.accessToken, tokens.expiresAt);
}

function clearPersistedSession() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(LOCAL_STORAGE_KEY);
  clearAuthCookie();
}

function writeAuthCookie(token: string, expiresAt: number) {
  if (typeof document === "undefined") {
    return;
  }

  const maxAgeSeconds = Math.max(Math.floor((expiresAt - Date.now()) / 1000), 0);
  const directives: string[] = [
    `${AUTH_COOKIE_NAME}=${token}`,
    "path=/",
    "sameSite=Lax",
  ];

  if (typeof window !== "undefined" && window.location.protocol === "https:") {
    directives.push("secure");
  }

  if (maxAgeSeconds > 0) {
    directives.push(`max-age=${maxAgeSeconds}`);
  }

  const cookieValue = directives.join("; ");

  document.cookie = cookieValue;
}

function clearAuthCookie() {
  if (typeof document === "undefined") {
    return;
  }

  const directives = [
    `${AUTH_COOKIE_NAME}=`,
    "path=/",
    "expires=Thu, 01 Jan 1970 00:00:00 GMT",
    "sameSite=Lax",
  ];

  if (typeof window !== "undefined" && window.location.protocol === "https:") {
    directives.push("secure");
  }

  document.cookie = directives.join("; ");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMounted, setIsMounted] = useState(false);
  const sessionRef = useRef<CognitoUserSession | null>(null);

  const applySession = useCallback((session: CognitoUserSession) => {
    sessionRef.current = session;
    persistSession(session);
    setUser(parseUser(session));
  }, []);

  const performLogout = useCallback(async () => {
    try {
      cognitoSignOut();
    } catch (error) {
      console.error("Failed to sign out from Cognito", error);
    } finally {
      sessionRef.current = null;
      clearPersistedSession();
      setUser(null);
    }
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      try {
        const { session } = await cognitoSignIn(email, password);
        // Verify session exists and has tokens
        if (!session || !session.getAccessToken() || !session.getIdToken()) {
          throw new Error("Invalid session received from Cognito");
        }
        applySession(session);
      } catch (error) {
        console.error("Login failed:", error);
        clearPersistedSession();
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    setIsLoading(true);
    await performLogout();
    setIsLoading(false);
  }, [performLogout]);

  const refreshSession = useCallback(async () => {
    try {
      const session = await refreshCognitoSession();
      applySession(session);
    } catch (error) {
      console.error("Failed to refresh Cognito session", error);
      await performLogout();
      throw error;
    }
  }, [applySession, performLogout]);

  const getAccessToken = useCallback(async () => {
    const currentSession = sessionRef.current;

    if (!currentSession) {
      return null;
    }

    const expiresAt = currentSession.getAccessToken().getExpiration() * 1000;
    const isExpired = expiresAt <= Date.now();

    if (!isExpired) {
      return currentSession.getAccessToken().getJwtToken();
    }

    try {
      const refreshed = await refreshCognitoSession();
      applySession(refreshed);
      return refreshed.getAccessToken().getJwtToken();
    } catch (error) {
      console.error("Failed to refresh access token", error);
      await performLogout();
      return null;
    }
  }, [applySession, performLogout]);

  // Mark component as mounted on client side
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Initialize session only after mount to prevent hydration mismatch
  useEffect(() => {
    if (!isMounted) {
      return;
    }

    let isMountedRef = true;

    const initialise = async () => {
      setIsLoading(true);
      try {
        const session = await getCurrentCognitoSession();
        if (session && isMountedRef) {
          applySession(session);
        } else if (isMountedRef) {
          clearPersistedSession();
          setUser(null);
        }
      } catch (error) {
        console.error("Unable to retrieve Cognito session", error);
        if (isMountedRef) {
          clearPersistedSession();
          setUser(null);
        }
      } finally {
        if (isMountedRef) {
          setIsLoading(false);
        }
      }
    };

    initialise();

    return () => {
      isMountedRef = false;
    };
  }, [applySession, isMounted]);

  // Token refresh polling
  useEffect(() => {
    if (typeof window === "undefined" || !isMounted) {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      const session = sessionRef.current;

      if (!session) {
        return;
      }

      const expiresAt = session.getAccessToken().getExpiration() * 1000;
      const timeUntilExpiry = expiresAt - Date.now();

      if (timeUntilExpiry <= REFRESH_THRESHOLD_MS) {
        try {
          const refreshed = await refreshCognitoSession();
          applySession(refreshed);
        } catch (error) {
          console.error("Automatic token refresh failed", error);
          // Don't logout on refresh failure - just log the error
          // This prevents redirect loops when API is down
          // The token will eventually expire and user will be redirected naturally
        }
      }
    }, REFRESH_POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [applySession, performLogout, isMounted]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      logout,
      refreshSession,
      getAccessToken,
    }),
    [user, isLoading, login, logout, refreshSession, getAccessToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}

export function useRequireAuth() {
  const context = useAuth();

  if (!context.isAuthenticated) {
    throw new Error("User is not authenticated");
  }

  return context;
}
