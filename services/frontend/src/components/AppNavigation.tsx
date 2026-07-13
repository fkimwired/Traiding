import Link from "next/link";

export const navigationItems = [
  { href: "/ideas", label: "Idea Intake" },
  { href: "/research", label: "Research Lab" },
  { href: "/paper", label: "Paper Trading" },
  { href: "/risk", label: "Risk / Compliance" },
] as const;

export function AppNavigation() {
  return (
    <nav aria-label="Primary navigation" className="primaryNavigation">
      <Link className="brand" href="/" aria-label="Fable5 home">
        <span className="brandMark" aria-hidden="true">
          F5
        </span>
        <span>
          <strong>Fable5</strong>
          <small>Research control plane</small>
        </span>
      </Link>
      <div className="navLinks">
        {navigationItems.map((item) => (
          <Link key={item.href} href={item.href}>
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

