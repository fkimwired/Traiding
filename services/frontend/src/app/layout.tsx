import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppNavigation } from "../components/AppNavigation";
import { SimulationBanner } from "../components/SimulationBanner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fable5 Research Platform",
  description: "Disciplined strategy research and simulated paper trading.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <SimulationBanner />
        <AppNavigation />
        <main>{children}</main>
      </body>
    </html>
  );
}

