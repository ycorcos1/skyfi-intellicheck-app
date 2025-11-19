"use client";

import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { usePathname } from "next/navigation";
import styles from "./TopNav.module.css";

function getInitials(firstName?: string | null, lastName?: string | null, fallback?: string | null) {
  if (firstName && lastName) {
    return `${firstName[0]?.toUpperCase()}${lastName[0]?.toUpperCase()}`;
  }
  if (firstName) {
    return firstName.slice(0, 2).toUpperCase();
  }
  if (fallback) {
    // Skip GUID/UUID-like strings (they contain hyphens and are long)
    const isGuid = /^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$/i.test(fallback);
    if (isGuid) {
      return "OP";
    }

    // Handle email addresses - extract from the part before @
    if (fallback.includes("@")) {
      const emailPrefix = fallback.split("@")[0];
      // Try to extract meaningful initials from email (e.g., "ycorcos26" -> "YC")
      const emailParts = emailPrefix.replace(/[0-9]/g, "").split(/[._-]/).filter(Boolean);
      if (emailParts.length >= 2) {
        return `${emailParts[0][0]?.toUpperCase()}${emailParts[1][0]?.toUpperCase()}`;
      }
      if (emailPrefix.length >= 2) {
        return emailPrefix.slice(0, 2).toUpperCase();
      }
    }

    // Handle regular names (space-separated)
    const letters = fallback
      .split(" ")
      .filter(Boolean)
      .map((segment) => segment[0]?.toUpperCase())
      .join("");
    if (letters.length >= 2) {
      return letters.slice(0, 2);
    }
    if (fallback.length >= 2) {
      return fallback.slice(0, 2).toUpperCase();
    }
  }
  return "OP";
}

const NAV_LINKS = [
  {
    href: "/dashboard",
    label: "Dashboard",
  },
];

export function TopNav() {
  const { user, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);
  const mobileMenuRef = useRef<HTMLDivElement | null>(null);
  const lastFocusedElementRef = useRef<HTMLElement | null>(null);
  const pathname = usePathname();

  const displayName = useMemo(() => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName} ${user.lastName}`;
    }
    // Skip GUID/UUID-like strings in user.name
    const isNameGuid = user?.name && /^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$/i.test(user.name);
    if (isNameGuid) {
      return user?.email ?? "Operator";
    }
    return user?.name ?? user?.email ?? "Operator";
  }, [user?.firstName, user?.lastName, user?.name, user?.email]);

  const initials = useMemo(
    () => getInitials(user?.firstName, user?.lastName, displayName),
    [user?.firstName, user?.lastName, displayName],
  );

  const closeMenu = useCallback(() => setIsMenuOpen(false), []);
  const closeMobileMenu = useCallback(() => setIsMobileMenuOpen(false), []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        event.target instanceof Node &&
        !menuRef.current.contains(event.target)
      ) {
        closeMenu();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [closeMenu]);

  useEffect(() => {
    if (!isMenuOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu();
        menuButtonRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [closeMenu, isMenuOpen]);

  const handleLogout = useCallback(async () => {
    closeMenu();
    closeMobileMenu();
    await logout();
  }, [closeMenu, closeMobileMenu, logout]);

  const handleMobileToggle = useCallback(() => {
    setIsMobileMenuOpen((open) => !open);
  }, []);

  useEffect(() => {
    if (!isMobileMenuOpen) {
      document.body.style.removeProperty("overflow");
      if (lastFocusedElementRef.current) {
        lastFocusedElementRef.current.focus({ preventScroll: true });
      }
      return;
    }

    lastFocusedElementRef.current = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    const focusableSelectors =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

    const focusFirstElement = () => {
      const focusableElements = mobileMenuRef.current?.querySelectorAll<HTMLElement>(focusableSelectors);
      if (focusableElements && focusableElements[0]) {
        focusableElements[0].focus();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!mobileMenuRef.current) {
        return;
      }

      const focusableElements = mobileMenuRef.current.querySelectorAll<HTMLElement>(focusableSelectors);
      if (event.key === "Escape") {
        event.preventDefault();
        closeMobileMenu();
        return;
      }

      if (event.key !== "Tab" || focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey) {
        if (activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else if (activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    focusFirstElement();
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [closeMobileMenu, isMobileMenuOpen]);

  const handleMobileOverlayClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        closeMobileMenu();
      }
    },
    [closeMobileMenu],
  );

  const renderNavLinks = (onNavigate?: () => void) =>
    NAV_LINKS.map((link) => {
      const isActive =
        pathname === link.href || (pathname?.startsWith(link.href) && pathname?.charAt(link.href.length) === "/");

      return (
        <Link
          key={link.href}
          href={link.href}
          className={isActive ? styles.navLinkActive : styles.navLink}
          aria-current={isActive ? "page" : undefined}
          onClick={onNavigate}
        >
          {link.label}
        </Link>
      );
    });

  return (
    <>
      <header className={styles.navbar} role="banner">
        <div className={styles.navContent}>
          <div className={styles.brandGroup}>
            <button
              type="button"
              className={styles.hamburger}
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-navigation"
              aria-label="Toggle navigation menu"
              onClick={handleMobileToggle}
            >
              <span aria-hidden className={styles.hamburgerBar} />
            </button>
            <Link href="/dashboard" className={styles.brand} aria-label="SkyFi IntelliCheck dashboard">
              <span>SkyFi</span>
              <span className={styles.brandAccent}>IntelliCheck</span>
            </Link>
          </div>

          <nav className={styles.primaryNav} aria-label="Primary navigation" id="primary-navigation">
            {renderNavLinks(closeMobileMenu)}
          </nav>
        </div>

        <div ref={menuRef} className={styles.userSection}>
          <button
            ref={menuButtonRef}
            type="button"
            className={styles.menuButton}
            aria-haspopup="menu"
            aria-expanded={isMenuOpen}
            aria-label={`User menu for ${displayName}`}
            onClick={() => setIsMenuOpen((open) => !open)}
          >
            {initials}
          </button>
          {isMenuOpen ? (
            <div role="menu" className={styles.menu}>
              <button type="button" className={styles.menuItem} onClick={handleLogout}>
                Log Out
              </button>
            </div>
          ) : null}
        </div>
      </header>

      {isMobileMenuOpen ? (
        <div
          className={styles.mobileOverlay}
          role="dialog"
          aria-modal="true"
          aria-labelledby="mobile-navigation-title"
          onClick={handleMobileOverlayClick}
        >
          <div ref={mobileMenuRef} className={styles.mobileMenu} id="mobile-navigation">
            <div className={styles.mobileMenuHeader}>
              <p id="mobile-navigation-title" className={styles.mobileMenuTitle}>
                Navigation
              </p>
              <button
                type="button"
                className={styles.mobileCloseButton}
                onClick={closeMobileMenu}
                aria-label="Close navigation menu"
              >
                ×
              </button>
            </div>

            <nav className={styles.mobileNav} aria-label="Primary navigation">
              {renderNavLinks(closeMobileMenu)}
            </nav>

            <div className={styles.mobileMenuFooter}>
              <button type="button" className={styles.mobileLogout} onClick={handleLogout}>
                Log Out
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export default TopNav;

