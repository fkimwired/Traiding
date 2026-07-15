"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { navigationItems } from "../lib/navigation";

export function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary navigation" className="primaryNavigation">
      <Link className="brand" href="/" aria-label="Fable5 home">
        <span className="brandMark" aria-hidden="true">
          F5
        </span>
        <span>
          <strong>Fable5</strong>
          <small>Evidence workspace</small>
        </span>
      </Link>
      <div className="navLinks">
        {navigationItems.map((item) => (
          <Link
            aria-current={pathname === item.href ? "page" : undefined}
            key={item.href}
            href={item.href}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
