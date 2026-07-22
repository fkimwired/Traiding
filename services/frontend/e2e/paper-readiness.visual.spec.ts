import { expect, test, type Page, type Route } from "@playwright/test";
import path from "node:path";

import {
  PAPER_READINESS_ASSESSMENT_ID,
  blockedPaperReadinessFixture,
  paperReadinessFixture,
  type PaperReadinessArtifact,
} from "../src/tests/paper-readiness-fixture";

const READINESS_PATH = "/v1/paper-shadow-readiness/";
const stabilityStyles = path.join(__dirname, "visual-stability.css");
const scenarios = [
  {
    artifact: paperReadinessFixture,
    slug: "mock-complete",
  },
  {
    artifact: blockedPaperReadinessFixture,
    slug: "blocked",
  },
] as const;

function recordUnexpectedRequestMethods(page: Page) {
  const unexpected: string[] = [];
  page.on("request", (request) => {
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
      unexpected.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });
  return unexpected;
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: "application/json",
    headers: { "Access-Control-Allow-Origin": "*" },
    status,
  });
}

async function routeReadinessGet(
  page: Page,
  artifact: PaperReadinessArtifact,
  requests: string[],
) {
  await page.route(`**${READINESS_PATH}**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    requests.push(`${request.method()} ${url.pathname}`);
    if (request.method() !== "GET") {
      await route.abort("blockedbyclient");
      return;
    }
    const requestedId = decodeURIComponent(url.pathname.slice(READINESS_PATH.length));
    await fulfillJson(
      route,
      requestedId === PAPER_READINESS_ASSESSMENT_ID
        ? artifact
        : { detail: "Persisted readiness evidence not found." },
      requestedId === PAPER_READINESS_ASSESSMENT_ID ? 200 : 404,
    );
  });
}

async function expectNoHorizontalPageOverflow(page: Page) {
  const width = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  expect(width.document).toBeLessThanOrEqual(width.viewport + 1);
}

for (const scenario of scenarios) {
  for (const colorScheme of ["light", "dark"] as const) {
    test(`paper readiness ${scenario.slug} ${colorScheme} snapshot`, async ({ page }) => {
      const requests: string[] = [];
      const unexpectedRequestMethods = recordUnexpectedRequestMethods(page);
      await page.emulateMedia({ colorScheme, reducedMotion: "reduce" });
      await routeReadinessGet(page, scenario.artifact, requests);

      await page.goto("/paper/readiness", { waitUntil: "domcontentloaded" });
      const workspace = page.locator("[data-readiness-surface='paper-only']");
      await expect(
        workspace.getByRole("heading", { level: 1, name: "Paper shadow readiness" }),
      ).toBeVisible({ timeout: 90_000 });
      await workspace.getByLabel("Readiness assessment ID").fill(PAPER_READINESS_ASSESSMENT_ID);
      expect(requests).toEqual([]);
      await workspace.getByRole("button", { name: "Load readiness evidence" }).click();

      await expect(
        workspace.getByRole("heading", {
          level: 2,
          name: `Assessment ${PAPER_READINESS_ASSESSMENT_ID}`,
        }),
      ).toBeVisible();
      await expect(
        workspace.getByText("MOCK — local contract proof only", { exact: true }),
      ).toBeVisible();
      await expect(
        workspace.getByText("HISTORICAL READINESS EVIDENCE", { exact: true }),
      ).toBeVisible();
      await expect(
        workspace.getByText(/Browser time is not authority for currentness or expiry/),
      ).toBeVisible();
      await expect(
        workspace.getByText(scenario.artifact.outcome, { exact: true }).first(),
      ).toBeVisible();
      const checks = workspace.getByTestId("readiness-checks").locator(":scope > li");
      await expect(checks).toHaveCount(8);
      if (scenario.artifact.outcome === "BLOCKED") {
        const blocker = workspace.getByRole("alert");
        for (const reason of scenario.artifact.reason_codes) {
          await expect(blocker.getByText(reason, { exact: true })).toBeVisible();
        }
        const blockedCheck = checks.filter({
          hasText: "MARKET_CLOCK_OPEN",
        });
        await expect(blockedCheck.getByText("BLOCKED", { exact: true })).toBeVisible();
        await expect(
          blockedCheck.getByText("market_clock_closed_verbatim", { exact: true }),
        ).toBeVisible();
      }
      expect(requests).toEqual([
        `GET ${READINESS_PATH}${PAPER_READINESS_ASSESSMENT_ID}`,
      ]);
      expect(unexpectedRequestMethods).toEqual([]);
      await expectNoHorizontalPageOverflow(page);

      await page.evaluate(() => {
        document.querySelectorAll("nextjs-portal").forEach((portal) => portal.remove());
        document.querySelector(".skipLink")?.remove();
        if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
        window.scrollTo({ behavior: "auto", top: 0 });
      });
      await expect(page).toHaveScreenshot(
        `paper-readiness-${scenario.slug}-${colorScheme}.png`,
        {
          fullPage: true,
          stylePath: stabilityStyles,
        },
      );
    });
  }
}
