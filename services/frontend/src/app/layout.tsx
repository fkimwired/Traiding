import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppNavigation } from "../components/AppNavigation";
import { SimulationBanner } from "../components/SimulationBanner";
import "./globals.css";
import "./phase8.css";

export const metadata: Metadata = {
  title: "Fable5 | Evidence before simulation",
  description:
    "A disciplined, synthetic research workspace for idea intake, evaluation, and governance review.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skipLink" href="#main-content">
          Skip to main content
        </a>
        <SimulationBanner />
        <AppNavigation />
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <footer className="siteFooter">
          <p>
            Fable5 presents deterministic synthetic research evidence. It does not provide
            personalized investment advice, real-performance claims, or execution capability.
          </p>
          <span>Paper status is historical and simulated.</span>
        </footer>
      </body>
    </html>
  );
}
