"use client";

import { BaseLayout } from "@/components/layout/BaseLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useRef } from "react";
import { TopNav } from "./TopNav";

export interface ProtectedLayoutProps {
  children: ReactNode;
}

export function ProtectedLayout({ children }: ProtectedLayoutProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const hasRedirectedRef = useRef(false);

  useEffect(() => {
    // Prevent redirect loops by tracking if we've already redirected
    if (hasRedirectedRef.current) {
      return;
    }

    // Only redirect if we're not already on the login page to avoid loops
    if (!isLoading && !isAuthenticated && typeof window !== "undefined") {
      const currentPath = window.location.pathname;
      
      // Don't redirect if already on login page
      if (currentPath.startsWith("/login")) {
        return;
      }

      // Mark that we're redirecting to prevent loops
      hasRedirectedRef.current = true;
      
      // Use a small delay to prevent rapid redirects
      const timer = setTimeout(() => {
        // Double-check we're still not authenticated and not on login page
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
          router.replace("/login");
        }
      }, 200);
      
      return () => {
        clearTimeout(timer);
      };
    }

    // Reset redirect flag when authenticated
    if (isAuthenticated) {
      hasRedirectedRef.current = false;
    }
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

