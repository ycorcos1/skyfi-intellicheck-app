"use client";

import { BaseLayout } from "@/components/layout/BaseLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useRef, useState } from "react";
import { TopNav } from "./TopNav";

export interface ProtectedLayoutProps {
  children: ReactNode;
}

export function ProtectedLayout({ children }: ProtectedLayoutProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const redirectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hasRedirectedRef = useRef(false);
  const [hasInitialized, setHasInitialized] = useState(false);

  // Wait for initial auth load to complete before doing any redirects
  useEffect(() => {
    if (!isLoading && !hasInitialized) {
      // Auth has finished loading, mark as initialized
      const timer = setTimeout(() => {
        setHasInitialized(true);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isLoading, hasInitialized]);

  useEffect(() => {
    // Don't do anything until auth has initialized
    if (!hasInitialized || isLoading) {
      return;
    }

    // Clear any pending redirects
    if (redirectTimerRef.current) {
      clearTimeout(redirectTimerRef.current);
      redirectTimerRef.current = null;
    }

    // If authenticated, reset redirect flag and clear any pending redirects
    if (isAuthenticated) {
      hasRedirectedRef.current = false;
      if (redirectTimerRef.current) {
        clearTimeout(redirectTimerRef.current);
        redirectTimerRef.current = null;
      }
      return;
    }

    // Only redirect if not authenticated and not already redirected
    if (!isAuthenticated && !hasRedirectedRef.current && typeof window !== "undefined") {
      const currentPath = window.location.pathname;
      
      // Don't redirect if already on login page
      if (currentPath.startsWith("/login")) {
        hasRedirectedRef.current = false; // Reset if already on login
        return;
      }

      // Mark that we're redirecting to prevent loops
      hasRedirectedRef.current = true;
      
      // Use a longer delay to prevent rapid redirects and allow auth state to fully stabilize
      redirectTimerRef.current = setTimeout(() => {
        // Final check before redirecting
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
          router.replace("/login");
        }
        redirectTimerRef.current = null;
      }, 500); // Increased delay
    }

    return () => {
      if (redirectTimerRef.current) {
        clearTimeout(redirectTimerRef.current);
        redirectTimerRef.current = null;
      }
    };
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="auth-loading">
        <div className="auth-loading__spinner" aria-hidden />
        <p className="auth-loading__text">Preparing your workspace…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <TopNav />
      <div className="app-shell__content">
        <BaseLayout>{children}</BaseLayout>
      </div>
    </div>
  );
}

export default ProtectedLayout;

