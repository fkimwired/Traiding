import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppNavigation } from "../components/AppNavigation";
import { SimulationBanner } from "../components/SimulationBanner";
import PaperTradingPage from "../app/paper/page";

describe("platform navigation and simulation boundary", () => {
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

  it("keeps the paper surface non-actionable before the governed paper phase", () => {
    render(<PaperTradingPage />);

    expect(screen.getByText("No broker adapter or order path exists.")).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(document.querySelector("form")).toBeNull();
  });
});
