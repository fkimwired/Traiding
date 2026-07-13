import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppNavigation } from "../components/AppNavigation";
import { SimulationBanner } from "../components/SimulationBanner";

describe("Phase 1 navigation", () => {
  it("renders all four product modes as accessible links", () => {
    render(<AppNavigation />);

    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Idea Intake" })).toHaveAttribute("href", "/ideas");
    expect(screen.getByRole("link", { name: "Research Lab" })).toHaveAttribute(
      "href",
      "/research",
    );
    expect(screen.getByRole("link", { name: "Paper Trading" })).toHaveAttribute(
      "href",
      "/paper",
    );
    expect(screen.getByRole("link", { name: "Risk / Compliance" })).toHaveAttribute(
      "href",
      "/risk",
    );
  });

  it("keeps simulation and advice boundaries visible", () => {
    render(<SimulationBanner />);

    expect(screen.getByText("Paper trading is simulated")).toBeVisible();
    expect(screen.getByText("Not investment advice")).toBeVisible();
  });
});

