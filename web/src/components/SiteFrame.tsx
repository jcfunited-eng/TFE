"use client";

import { useAuth, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/screener", label: "Screener" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/portfolio-advisor", label: "Portfolio" },
  { href: "/legal", label: "Legal" },
] as const;

type SiteFrameProps = {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  pageBackgroundImage?: string;
  hideHeader?: boolean;
};

export default function SiteFrame({
  children,
  title = "Tao Financial Engine",
  subtitle = "Calm Signals for Research Decisions",
  pageBackgroundImage = "/landing-zen.jpg",
  hideHeader = false,
}: SiteFrameProps) {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const { isSignedIn, isLoaded } = useAuth();

  return (
    <div
      className={`site-shell ${isHome ? "home-shell" : "inner-shell"}`}
      style={{ ["--page-bg-image" as string]: `url("${pageBackgroundImage}")` }}
    >
      {!hideHeader ? (
        <header className={`site-header ${isHome ? "site-header-home" : "site-header-inner"}`}>
          <div className="brand">
            <span className="brand-dot" aria-hidden="true" />
            <div>
              <p className="brand-title" style={{ fontSize: "1.23rem" }}>
                {title}
              </p>
              <p className="brand-subtitle" style={{ fontSize: "0.96rem" }}>
                {subtitle}
              </p>
            </div>
          </div>

          <nav className="site-nav" aria-label="Primary">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`site-nav-link ${active ? "active" : ""}`}
                  style={{ fontSize: "1.03rem" }}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="site-actions">
            <div className="site-utility-icons" aria-label="Utility links">
              <Link href="/help" className="site-icon-link" title="Help">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M9.8 9.1a2.2 2.2 0 0 1 4.4.2c0 1.8-2.2 2.1-2.2 3.8" />
                  <circle cx="12" cy="16.9" r="0.9" />
                </svg>
                <span className="sr-only">Help</span>
              </Link>

              <Link href="/support" className="site-icon-link" title="Support">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="3.5" y="6.5" width="17" height="11" rx="1.8" />
                  <path d="M4.4 8.1 12 13.2l7.6-5.1" />
                </svg>
                <span className="sr-only">Support</span>
              </Link>
            </div>

            {isLoaded ? (
              isSignedIn ? (
                <UserButton
                  userProfileMode="navigation"
                  userProfileUrl="/account"
                />
              ) : (
                <Link
                  href="/sign-in"
                  className="btn btn-ghost"
                  style={{ fontSize: "1.04rem", minHeight: 42, padding: "7px 12px" }}
                >
                  Sign In
                </Link>
              )
            ) : null}
          </div>
        </header>
      ) : null}

      <main className="site-main">{children}</main>
    </div>
  );
}
