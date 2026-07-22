import AxeBuilder from "@axe-core/playwright";
import {
  expect,
  test,
  type Locator,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";

import {
  PAPER_READINESS_ASSESSMENT_ID,
  PAPER_READINESS_CHECK_CODES,
  paperReadinessFixture,
} from "../src/tests/paper-readiness-fixture";

const MALFORMED_ASSESSMENT_ID = "not-a-canonical-assessment-id";
const MISSING_ASSESSMENT_ID = "a4fa93e3-1fa0-4d54-9d6e-4fe1d1a31404";
const CONFLICTING_ASSESSMENT_ID = "bd140068-b44b-4dad-9887-f64107e080dd";
const READINESS_PATH = "/v1/paper-shadow-readiness/";

type ReadinessRequest = {
  method: string;
  pathname: string;
};

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

async function routeReadinessGet(page: Page, requests: ReadinessRequest[]) {
  await page.route(`**${READINESS_PATH}**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    requests.push({ method: request.method(), pathname: url.pathname });

    if (request.method() !== "GET") {
      await route.abort("blockedbyclient");
      return;
    }

    const requestedId = decodeURIComponent(url.pathname.slice(READINESS_PATH.length));
    if (requestedId === MALFORMED_ASSESSMENT_ID) {
      await fulfillJson(route, { detail: "Typed readiness identifier rejected." }, 422);
      return;
    }
    if (requestedId === CONFLICTING_ASSESSMENT_ID) {
      await fulfillJson(route, { detail: "Immutable readiness lineage conflict." }, 409);
      return;
    }
    if (requestedId !== PAPER_READINESS_ASSESSMENT_ID) {
      await fulfillJson(route, { detail: "Persisted readiness evidence not found." }, 404);
      return;
    }
    await fulfillJson(route, paperReadinessFixture);
  });
}

async function waitForReadinessWorkspace(page: Page) {
  const workspace = page.locator("[data-readiness-surface='paper-only']");
  await expect(
    workspace.getByRole("heading", { level: 1, name: "Paper shadow readiness" }),
  ).toBeVisible({ timeout: 90_000 });
  await expect(workspace.getByLabel("Readiness assessment ID")).toBeEnabled();
  return workspace;
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

function durationMilliseconds(value: string) {
  return Math.max(
    ...value.split(",").map((duration) => {
      const normalized = duration.trim();
      if (!normalized) return 0;
      return normalized.endsWith("ms")
        ? Number.parseFloat(normalized)
        : Number.parseFloat(normalized) * 1_000;
    }),
  );
}

async function expectReducedMotion(target: Locator) {
  const motion = await target.evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      animationDuration: style.animationDuration,
      transitionDuration: style.transitionDuration,
    };
  });
  expect(durationMilliseconds(motion.animationDuration)).toBeLessThanOrEqual(0.011);
  expect(durationMilliseconds(motion.transitionDuration)).toBeLessThanOrEqual(0.011);
}

test("one keyboard action performs one GET and renders the exact paper-only evidence", async ({
  page,
}) => {
  const requests: ReadinessRequest[] = [];
  const unexpectedRequestMethods = recordUnexpectedRequestMethods(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await routeReadinessGet(page, requests);

  await page.goto("/paper/readiness", { waitUntil: "domcontentloaded" });
  const workspace = await waitForReadinessWorkspace(page);
  await expect(
    workspace.getByText("Simulated / Paper Only / No Advice", { exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByText(
      "No assessment loaded. Enter an immutable identifier to begin a read.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.waitForTimeout(150);
  expect(requests).toEqual([]);

  const assessmentInput = workspace.getByLabel("Readiness assessment ID");
  await assessmentInput.focus();
  await expect(assessmentInput).toBeFocused();
  await page.keyboard.type(PAPER_READINESS_ASSESSMENT_ID);
  await page.waitForTimeout(150);
  expect(requests).toEqual([]);

  await page.keyboard.press("Tab");
  const loadButton = workspace.getByRole("button", { name: "Load readiness evidence" });
  await expect(loadButton).toBeFocused();
  await page.keyboard.press("Enter");

  const resultHeading = workspace.getByRole("heading", {
    level: 2,
    name: `Assessment ${PAPER_READINESS_ASSESSMENT_ID}`,
  });
  await expect(resultHeading).toBeVisible();
  const resultFocus = workspace.locator("div[tabindex='-1']");
  await expect(resultFocus).toHaveCount(1);
  await expect(resultFocus).toBeFocused();
  expect(requests).toEqual([
    {
      method: "GET",
      pathname: `${READINESS_PATH}${PAPER_READINESS_ASSESSMENT_ID}`,
    },
  ]);
  await page.waitForTimeout(250);
  expect(requests).toHaveLength(1);

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
    workspace.getByText(paperReadinessFixture.outcome, { exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByRole("heading", { level: 3, name: "Eight ordered readiness checks" }),
  ).toBeVisible();

  const checks = workspace.getByTestId("readiness-checks").locator(":scope > li");
  await expect(checks).toHaveCount(8);
  expect(
    await checks.evaluateAll((items) =>
      items.map((item) => item.querySelector("strong")?.textContent?.trim()),
    ),
  ).toEqual([...PAPER_READINESS_CHECK_CODES]);
  for (const [index, expectedCheck] of paperReadinessFixture.checks.entries()) {
    const check = checks.nth(index);
    await expect(check.getByText(expectedCheck.status, { exact: true })).toBeVisible();
    await expect(check.getByText(expectedCheck.reason_code, { exact: true })).toBeVisible();
    await expect(check.getByText(expectedCheck.check_sha256, { exact: true })).toBeVisible();
  }

  await expect(
    workspace.getByRole("heading", { level: 3, name: "No execution authority" }),
  ).toBeVisible();
  for (const authorityLiteral of [
    "order_submission_authorized = false",
    "strategy_execution_eligible = false",
    "live_path_absent = true",
    "no_personalized_investment_advice = true",
    "no_real_performance_claimed = true",
  ]) {
    await expect(workspace.getByText(authorityLiteral, { exact: true })).toBeVisible();
  }

  await expect(workspace.locator("input")).toHaveCount(1);
  await expect(workspace.locator("button")).toHaveCount(1);
  await expect(workspace.locator("select, textarea, input[type='password']")).toHaveCount(0);
  await expect(
    workspace.locator(
      "input[name*='key' i], input[name*='secret' i], input[name*='credential' i], input[name*='account' i]",
    ),
  ).toHaveCount(0);
  await expect(
    workspace.getByRole("button", {
      name: /capture|credential|place order|submit order|cancel order|replace order|close position|refresh|retry/i,
    }),
  ).toHaveCount(0);

  expect(requests.every((request) => request.method === "GET")).toBe(true);
  expect(unexpectedRequestMethods).toEqual([]);
  await expectReducedMotion(loadButton);
  await expectNoHorizontalPageOverflow(page);
  await expectNoAxeViolations(page);
});

for (const failure of [
  {
    assessmentId: MISSING_ASSESSMENT_ID,
    heading: "Not found (404)",
    message: "No persisted readiness assessment exists for that identifier.",
    status: 404,
  },
  {
    assessmentId: CONFLICTING_ASSESSMENT_ID,
    heading: "Conflict (409)",
    message: "The persisted readiness evidence conflicts with its immutable lineage.",
    status: 409,
  },
] as const) {
  test(`a terminal ${failure.status} performs one GET without retry`, async ({
    page,
  }, testInfo: TestInfo) => {
    test.skip(
      testInfo.project.name !== "desktop",
      `Focused typed-${failure.status} behavior runs once on desktop.`,
    );
    const requests: ReadinessRequest[] = [];
    const unexpectedRequestMethods = recordUnexpectedRequestMethods(page);
    await routeReadinessGet(page, requests);

    await page.goto("/paper/readiness", { waitUntil: "domcontentloaded" });
    const workspace = await waitForReadinessWorkspace(page);
    await workspace.getByLabel("Readiness assessment ID").fill(failure.assessmentId);
    await page.waitForTimeout(150);
    expect(requests).toEqual([]);
    await workspace.getByRole("button", { name: "Load readiness evidence" }).click();

    const error = workspace.getByRole("alert");
    await expect(
      error.getByRole("heading", { level: 2, name: failure.heading }),
    ).toBeVisible();
    await expect(error).toContainText(failure.message);
    await expect(error).toBeFocused();
    expect(requests).toEqual([
      {
        method: "GET",
        pathname: `${READINESS_PATH}${failure.assessmentId}`,
      },
    ]);
    await page.waitForTimeout(250);
    expect(requests).toHaveLength(1);
    await expect(
      workspace.getByRole("button", { name: /retry|refresh|again/i }),
    ).toHaveCount(0);
    expect(unexpectedRequestMethods).toEqual([]);
    await expectNoHorizontalPageOverflow(page);
    await expectNoAxeViolations(page);
  });
}

test("a malformed nonempty ID receives one terminal 422 GET without retry", async ({
  page,
}, testInfo: TestInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Focused typed-422 behavior runs once on desktop.");
  const requests: ReadinessRequest[] = [];
  const unexpectedRequestMethods = recordUnexpectedRequestMethods(page);
  await routeReadinessGet(page, requests);

  await page.goto("/paper/readiness", { waitUntil: "domcontentloaded" });
  const workspace = await waitForReadinessWorkspace(page);
  const assessmentInput = workspace.getByLabel("Readiness assessment ID");
  await assessmentInput.fill(MALFORMED_ASSESSMENT_ID);
  await page.waitForTimeout(150);
  expect(requests).toEqual([]);

  await workspace.getByRole("button", { name: "Load readiness evidence" }).click();
  const error = workspace.getByRole("alert");
  await expect(error.getByRole("heading", { level: 2, name: "Validation (422)" })).toBeVisible();
  await expect(error).toContainText(
    "The assessment identifier was rejected by the typed API boundary.",
  );
  await expect(error).toBeFocused();
  expect(requests).toEqual([
    {
      method: "GET",
      pathname: `${READINESS_PATH}${MALFORMED_ASSESSMENT_ID}`,
    },
  ]);
  await page.waitForTimeout(250);
  expect(requests).toHaveLength(1);
  await expect(workspace.getByTestId("readiness-checks")).toHaveCount(0);
  await expect(
    workspace.getByRole("button", { name: /retry|refresh|again/i }),
  ).toHaveCount(0);
  expect(unexpectedRequestMethods).toEqual([]);
  await expectNoHorizontalPageOverflow(page);
  await expectNoAxeViolations(page);
});
