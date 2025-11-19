"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useMemo, useState } from "react";

function LoginForm() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo = useMemo(
    () => searchParams.get("redirectTo") ?? "/dashboard",
    [searchParams],
  );

  useEffect(() => {
    // Only redirect if authenticated and not submitting
    // Add a small delay to prevent immediate redirect loops
    if (isAuthenticated && !isSubmitting) {
      const timer = setTimeout(() => {
        // Only redirect if we're still authenticated and not already on the target page
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/dashboard")) {
      router.replace(redirectTo);
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated, isSubmitting, redirectTo, router]);

  const validateForm = useCallback(() => {
    if (!email || !password) {
      setError("Please enter both email and password.");
      return false;
    }
    return true;
  }, [email, password]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError(null);

      if (!validateForm()) {
        return;
      }

      setIsSubmitting(true);

      try {
        await login(email.trim(), password);
        router.replace(redirectTo);
      } catch (cause) {
        if (cause && typeof cause === "object" && "message" in cause) {
          const message = String((cause as { message?: string }).message);
          setError(message || "Unable to sign in. Check your credentials and try again.");
        } else {
          setError("Unable to sign in. Check your credentials and try again.");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [email, password, login, redirectTo, router, validateForm],
  );

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          SkyFi <span>IntelliCheck</span>
        </div>
        <h1 className="login-title">Login</h1>
        {error ? <div className="login-error">{error}</div> : null}
        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="login-field">
            <label className="login-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              className="login-input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
              placeholder="operator@skyfi.com"
              disabled={isSubmitting || isLoading}
            />
          </div>
          <div className="login-field">
            <label className="login-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              className="login-input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
              placeholder="Enter your password"
              disabled={isSubmitting || isLoading}
            />
          </div>
          <button
            type="submit"
            className="login-button"
            disabled={isSubmitting || isLoading}
          >
            {isSubmitting || isLoading ? "Signing In…" : "Sign In"}
          </button>
        </form>
        <p className="login-helper">
          Use your SkyFi operator credentials to access the verification dashboard.
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="login-page">
        <div className="login-card">
          <div className="login-logo">
            SkyFi <span>IntelliCheck</span>
          </div>
          <h1 className="login-title">Login</h1>
          <p>Loading...</p>
        </div>
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}

