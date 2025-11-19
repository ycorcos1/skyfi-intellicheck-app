"use client";

import { BaseLayout } from "@/components/layout/BaseLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { TopNav } from "./TopNav";

export interface ProtectedLayoutProps {
  children: ReactNode;
}

export function ProtectedLayout({ children }: ProtectedLayoutProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Only redirect if we're not already on the login page to avoid loops
    if (!isLoading && !isAuthenticated && typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      router.replace("/login");
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

