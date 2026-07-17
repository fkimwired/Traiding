import AxeBuilder from "@axe-core/playwright";
import type { components } from "@fable5/contracts";
import {
  expect,
  test,
  type Locator,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";

import {
  PHASE10_BLOCKED_RUN_ID as BLOCKED_RUN_ID,
  PHASE10_COMPLETED_IDEMPOTENCY_KEY,
  PHASE10_COMPLETED_RUN_ID as COMPLETE_RUN_ID,
  PHASE10_SOURCE_ASSESSMENT_ID as SOURCE_ASSESSMENT_ID,
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

type PaperSimulationCreateRequest = components["schemas"]["PaperSimulationCreateRequest"];

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
    if (!assessment) {
      await fulfillJson(route, { detail: "Synthetic assessment fixture not found." }, 404);
      return;
    }
    await fulfillJson(route, timelineRequested ? phase10TimelineFor(assessment) : assessment);
  });
}

async function routeSimulationHistory(page: Page, artifacts: PaperSimulationArtifact[]) {
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
      await fulfillJson(route, artifacts.map(phase10SummaryFor));
      return;
    }
    const simulationRunId = decodeURIComponent(url.pathname.split("/").at(-1) ?? "");
    const artifact = artifacts.find((candidate) => candidate.simulation_run_id === simulationRunId);
    await fulfillJson(route, artifact ?? { detail: "Synthetic artifact not found." }, artifact ? 200 : 404);
  });
}

async function expectNoAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
}

async function expectNoHorizontalPageOverflow(page: Page) {
  const width = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  expect(width.document).toBeLessThanOrEqual(width.viewport + 1);
}

async function expectVisibleFocus(target: Locator) {
  const focus = await target.evaluate((element) => {
    const style = window.getComputedStyle(element);
    const rectangle = element.getBoundingClientRect();
    return {
      boxShadow: style.boxShadow,
      outlineStyle: style.outlineStyle,
      outlineWidth: Number.parseFloat(style.outlineWidth),
      visible: rectangle.width > 0 && rectangle.height > 0 && style.visibility !== "hidden",
    };
  });
  expect(focus.visible).toBe(true);
  expect(focus.outlineStyle !== "none" && focus.outlineWidth > 0).toBe(true);
  expect(focus.boxShadow).not.toBe("none");
}

function skipUnlessDesktop(testInfo: TestInfo) {
  test.skip(testInfo.project.name !== "desktop", "Focused behavior runs once on desktop.");
}

async function waitForPaperWorkspace(page: Page) {
  await expect(page.getByRole("heading", { level: 1, name: "Simulated Paper Status" })).toBeVisible();
  await expect(page.getByLabel("Approval assessment")).toBeEnabled({ timeout: 90_000 });
  await expect(page.locator("[data-visual-corpus='synthetic']")).toHaveCount(1, {
    timeout: 90_000,
  });
}

test("completed and blocked local mock artifacts preserve boundaries and WCAG", async ({ page }) => {
  const completed = phase10CompletedArtifact;
  const blocked = phase10BlockedArtifact;
  const writes: string[] = [];
  page.on("request", (request) => {
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
      writes.push(`${request.method()} ${request.url()}`);
    }
  });
  await routePhase10AssessmentEvidence(page);
  await routeSimulationHistory(page, [blocked, completed]);

  await page.goto("/paper", { waitUntil: "domcontentloaded" });
  await waitForPaperWorkspace(page);

  const simulationForm = page
    .getByRole("heading", { name: "Run a local mock simulation" })
    .locator("xpath=ancestor::section[1]");
  await expect(simulationForm.getByLabel("Approval assessment")).toBeVisible();
  await expect(
    simulationForm.getByRole("button", { name: "Run deterministic local simulation" }),
  ).toBeVisible();
  await expect(simulationForm.locator("input, textarea")).toHaveCount(0);
  await expect(simulationForm.locator("select")).toHaveCount(1);

  const completedCard = page.getByRole("article", { name: COMPLETE_RUN_ID });
  await expect(completedCard).toBeVisible({ timeout: 30_000 });
  await expect(completedCard.getByText("SIMULATED_COMPLETE", { exact: true })).toBeVisible();
  await expect(
    completedCard.getByText("SIMULATED / LOCAL MOCK", { exact: true }).first(),
  ).toBeVisible();
  await expect(completedCard.getByText("SIMULATED_FILLED", { exact: true })).toBeVisible();
  await expect(completedCard.locator(".simulationLedgerEntry")).toHaveCount(1);
  await expect(
    completedCard.getByRole("link", { name: "Trace source to artifact" }),
  ).toHaveAttribute(
    "href",
    `/lineage?assessment_id=${SOURCE_ASSESSMENT_ID}&simulation_run_id=${COMPLETE_RUN_ID}`,
  );

  const blockedCard = page.getByRole("article", { name: BLOCKED_RUN_ID });
  await expect(blockedCard).toBeVisible();
  await expect(blockedCard).toHaveAttribute("data-blocking", "true");
  await expect(blockedCard.getByText("BLOCKED", { exact: true }).first()).toBeVisible();
  await expect(blockedCard.getByText("BLOCKED - zero ledger entries", { exact: true })).toBeVisible();
  await expect(blockedCard.locator(".simulationLedgerEntry")).toHaveCount(0);
  await expect(
    blockedCard.getByText("transition_approval_not_fresh", { exact: true }).first(),
  ).toBeVisible();

  await expect(page.getByText("LIVE PATH ABSENT", { exact: true })).toBeVisible();
  await expect(page.getByText("NO PERSONALIZED ADVICE", { exact: true })).toBeVisible();
  await expect(page.getByText(/This is not investment advice/i)).toBeVisible();
  await expect(page.locator("a[href*='broker'], a[href*='order'], form[action]")).toHaveCount(0);
  await expectNoHorizontalPageOverflow(page);
  await expectNoAxeViolations(page);
  expect(writes).toEqual([]);
});

test("selection fails closed and an unavailable request retries with one exact idempotency key", async ({
  page,
}, testInfo) => {
  skipUnlessDesktop(testInfo);
  const requestBodies: PaperSimulationCreateRequest[] = [];
  const writes: string[] = [];
  page.on("request", (request) => {
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
      writes.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });

  await routePhase10AssessmentEvidence(page);
  await page.route("**/v1/local-simulations**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await fulfillCorsPreflight(route);
      return;
    }
    if (url.pathname !== "/v1/local-simulations") {
      await fulfillJson(route, { detail: "Synthetic artifact not found." }, 404);
      return;
    }
    if (request.method() === "GET") {
      await fulfillJson(route, []);
      return;
    }
    const body = request.postDataJSON() as PaperSimulationCreateRequest;
    requestBodies.push(body);
    if (requestBodies.length === 1) {
      await fulfillJson(route, { detail: "Synthetic retry fixture." }, 503);
      return;
    }
    await fulfillJson(
      route,
      phase10CompletedArtifact,
      201,
    );
  });

  await page.addInitScript((idempotencyKey) => {
    Object.defineProperty(globalThis.crypto, "randomUUID", {
      configurable: true,
      value: () => idempotencyKey,
    });
  }, PHASE10_COMPLETED_IDEMPOTENCY_KEY);

  await page.goto("/paper", { waitUntil: "domcontentloaded" });
  await waitForPaperWorkspace(page);

  const assessment = page.getByLabel("Approval assessment");
  const submit = page.getByRole("button", { name: "Run deterministic local simulation" });
  const blockedValue = await assessment
    .locator("option")
    .filter({ hasText: "known blocker" })
    .first()
    .getAttribute("value");
  expect(blockedValue).not.toBeNull();
  await assessment.selectOption(blockedValue!);
  await expect(page.getByRole("alert").filter({ hasText: "Known blocking evidence" })).toBeVisible();
  await expect(submit).toBeDisabled();
  expect(requestBodies).toEqual([]);

  const eligibleValue = SOURCE_ASSESSMENT_ID;
  await expect(assessment.locator(`option[value="${eligibleValue}"]`)).toContainText(
    "eligible for server revalidation",
  );
  await assessment.selectOption(eligibleValue);
  await expect(submit).toBeEnabled();
  await assessment.focus();
  await expect(assessment).toBeFocused();
  await expectVisibleFocus(assessment);
  await page.keyboard.press("Tab");
  await expect(submit).toBeFocused();
  await expectVisibleFocus(submit);
  await page.keyboard.press("Enter");

  const submissionAlert = page
    .getByRole("alert")
    .filter({ hasText: "Local simulation was not accepted" });
  await expect(submissionAlert).toBeVisible();
  await expect(submissionAlert).toBeFocused();
  const retry = submissionAlert.getByRole("button", { name: "Retry exact simulation request" });
  await page.keyboard.press("Tab");
  await expect(retry).toBeFocused();
  await expectVisibleFocus(retry);
  await page.keyboard.press("Enter");

  const result = page.getByRole("article", { name: COMPLETE_RUN_ID });
  await expect(result).toBeVisible({ timeout: 30_000 });
  await expect(result).toBeFocused();
  await expect(result.getByText("SIMULATED_COMPLETE", { exact: true })).toBeVisible();
  expect(requestBodies).toHaveLength(2);
  expect(requestBodies[1]).toEqual(requestBodies[0]);
  expect(Object.keys(requestBodies[0] ?? {}).sort()).toEqual([
    "approval_assessment_id",
    "simulation_idempotency_key",
  ]);
  expect(requestBodies[0]?.approval_assessment_id).toBe(eligibleValue);
  expect(requestBodies[0]?.simulation_idempotency_key).toBe(
    PHASE10_COMPLETED_IDEMPOTENCY_KEY,
  );
  expect(writes).toEqual([
    "POST /v1/local-simulations",
    "POST /v1/local-simulations",
  ]);
  await expectNoAxeViolations(page);
});
