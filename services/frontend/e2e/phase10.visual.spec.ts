import { expect, test, type Locator, type Page, type Route } from "@playwright/test";
import path from "node:path";

import {
  phase10AssessmentSummaryFor,
  phase10BlockedArtifact,
  phase10BlockedAssessment,
  phase10CompletedArtifact,
  phase10SourceAssessment,
  phase10SummaryFor,
  phase10SyntheticCard,
  phase10TimelineFor,
  type PaperSimulationArtifact,
} from "./phase10.fixtures";

const stabilityStyles = path.join(__dirname, "visual-stability.css");

const cases = [
  {
    artifact: phase10CompletedArtifact,
    outcome: phase10CompletedArtifact.outcome,
    runId: phase10CompletedArtifact.simulation_run_id,
    slug: "completed",
  },
  {
    artifact: phase10BlockedArtifact,
    outcome: phase10BlockedArtifact.outcome,
    runId: phase10BlockedArtifact.simulation_run_id,
    slug: "blocked",
  },
] as const;

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: "application/json",
    headers: { "Access-Control-Allow-Origin": "*" },
    status,
  });
}

async function fulfillCorsPreflight(route: Route) {
  await route.fulfill({
    headers: {
      "Access-Control-Allow-Headers": "content-type",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Origin": "*",
    },
    status: 204,
  });
}

async function routePhase10AssessmentEvidence(page: Page) {
  const emptyCollectionPaths = [
    "/v1/mappings",
    "/v1/data-snapshots",
    "/v1/evaluation-reports",
    "/v1/evaluation-outcomes",
    "/v1/research-runs",
    "/v1/approval-revocations",
  ];
  for (const path of emptyCollectionPaths) {
    await page.route(`**${path}**`, async (route) => {
      if (route.request().method() === "OPTIONS") {
        await fulfillCorsPreflight(route);
        return;
      }
      await fulfillJson(route, []);
    });
  }

  await page.route("**/v1/cards**", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await fulfillCorsPreflight(route);
      return;
    }
    await fulfillJson(route, [phase10SyntheticCard]);
  });

  const assessments = [phase10SourceAssessment, phase10BlockedAssessment];
  await page.route("**/v1/approval-assessments**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await fulfillCorsPreflight(route);
      return;
    }
    if (request.method() !== "GET") {
      await route.abort("blockedbyclient");
      return;
    }
    if (url.pathname === "/v1/approval-assessments") {
      await fulfillJson(route, assessments.map(phase10AssessmentSummaryFor));
      return;
    }
    const segments = url.pathname.split("/");
    const timelineRequested = segments.at(-1) === "evidence-timeline";
    const assessmentId = decodeURIComponent(segments.at(timelineRequested ? -2 : -1) ?? "");
    const assessment = assessments.find((candidate) => candidate.assessment_id === assessmentId);
    await fulfillJson(
      route,
      assessment
        ? timelineRequested
          ? phase10TimelineFor(assessment)
          : assessment
        : { detail: "Synthetic assessment fixture not found." },
      assessment ? 200 : 404,
    );
  });
}

async function routeArtifact(page: Page, artifact: PaperSimulationArtifact) {
  await page.route("**/v1/local-simulations**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await fulfillCorsPreflight(route);
      return;
    }
    if (request.method() !== "GET") {
      await route.abort("blockedbyclient");
      return;
    }
    if (url.pathname === "/v1/local-simulations") {
      await fulfillJson(route, [phase10SummaryFor(artifact)]);
      return;
    }
    const requestedId = decodeURIComponent(url.pathname.split("/").at(-1) ?? "");
    await fulfillJson(
      route,
      requestedId === artifact.simulation_run_id
        ? artifact
        : { detail: "Synthetic artifact not found." },
      requestedId === artifact.simulation_run_id ? 200 : 404,
    );
  });
}

function dynamicEvidence(page: Page): Locator[] {
  return [
    page.locator("time"),
    page.locator("code"),
    page.locator("pre"),
    page.locator(".mono"),
    page.locator(".artifactHash"),
    page.locator(".visualMask"),
    page.locator(".simulationCheckEvidence"),
  ];
}

for (const scenario of cases) {
  test(`phase10 ${scenario.slug} local mock snapshot`, async ({ page }) => {
    const artifact = scenario.artifact;
    const writes: string[] = [];
    page.on("request", (request) => {
      if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
        writes.push(`${request.method()} ${request.url()}`);
      }
    });
    await routePhase10AssessmentEvidence(page);
    await routeArtifact(page, artifact);

    await page.goto("/paper", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { level: 1, name: "Simulated Paper Status" })).toBeVisible();
    const artifactCard = page.getByRole("article", { name: scenario.runId });
    await expect(artifactCard).toBeVisible({ timeout: 90_000 });
    await expect(page.locator("[data-visual-corpus='synthetic']")).toHaveCount(1, {
      timeout: 90_000,
    });
    await expect(artifactCard.getByText(scenario.outcome, { exact: true }).first()).toBeVisible();
    if (scenario.outcome === "BLOCKED") {
      await expect(artifactCard).toHaveAttribute("data-blocking", "true");
      await expect(artifactCard.getByText("BLOCKED - zero ledger entries", { exact: true })).toBeVisible();
    } else {
      await expect(artifactCard.getByText("SIMULATED_FILLED", { exact: true })).toBeVisible();
    }

    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(hasHorizontalOverflow).toBe(false);
    expect(writes).toEqual([]);

    const stickyNavigationHeight = await page
      .locator(".primaryNavigation")
      .evaluate((element) => element.getBoundingClientRect().height);
    await artifactCard.evaluate((element, navigationHeight) => {
      const cardTop = window.scrollY + element.getBoundingClientRect().top;
      window.scrollTo({
        behavior: "auto",
        top: Math.max(0, cardTop - navigationHeight - 16),
      });
    }, stickyNavigationHeight);
    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    });
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    await expect(artifactCard.locator(".cardHeader").first()).toBeInViewport();
    await expect(artifactCard.getByText(scenario.outcome, { exact: true }).first()).toBeInViewport();
    await expect(page).toHaveScreenshot(`phase10-${scenario.slug}.png`, {
      fullPage: false,
      mask: dynamicEvidence(page),
      maskColor: "#d9ddd8",
      stylePath: stabilityStyles,
    });
  });
}
