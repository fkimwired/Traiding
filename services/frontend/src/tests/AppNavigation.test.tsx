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

    expect(screen.getByText("SIMULATED RESEARCH ENVIRONMENT")).toBeVisible();
    expect(screen.getByText("Paper trading is simulated")).toBeVisible();
    expect(screen.getByText("No execution capability")).toBeVisible();
    expect(screen.getByText("Not investment advice")).toBeVisible();
  });

  it("keeps paper status historical, simulated, and non-executable", () => {
    render(<PaperTradingPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Simulated Paper Status" }),
    ).toBeVisible();
    expect(screen.getByText("SIMULATED")).toBeVisible();
    expect(
      screen.getByText(/Historical synthetic evidence only\. No executable controls/),
    ).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(document.querySelector("form")).toBeNull();
  });
});
