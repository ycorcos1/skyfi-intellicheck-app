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
      }, 500); // Increased delay to ensure session is fully established
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
        console.error("Login error:", cause);
        
        // Handle Cognito-specific errors
        let errorMessage = "Unable to sign in. Check your credentials and try again.";
        
        if (cause && typeof cause === "object") {
          const error = cause as { message?: string; code?: string; name?: string };
          
          // Extract error message
          if (error.message) {
            errorMessage = error.message;
          }
          
          // Handle specific Cognito error codes
          if (error.code === "NotAuthorizedException") {
            errorMessage = "Incorrect email or password. Please try again.";
          } else if (error.code === "UserNotFoundException") {
            errorMessage = "User not found. Please check your email address.";
          } else if (error.code === "UserNotConfirmedException") {
            errorMessage = "Your account is not confirmed. Please contact an administrator.";
          } else if (error.code === "TooManyRequestsException") {
            errorMessage = "Too many login attempts. Please try again later.";
          } else if (error.name === "NetworkError" || error.message?.includes("Network")) {
            errorMessage = "Network error. Please check your connection and try again.";
          }
        }
        
        setError(errorMessage);
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

