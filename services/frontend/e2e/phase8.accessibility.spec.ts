import AxeBuilder from "@axe-core/playwright";
import {
  expect,
  test,
  type Locator,
  type Page,
  type TestInfo,
} from "@playwright/test";

const modes = [
  { heading: "Idea Intake", path: "/ideas" },
  { heading: "Research Lab", path: "/research" },
  { heading: "Simulated Paper Status", path: "/paper" },
  { heading: "Risk / Compliance", path: "/risk" },
] as const;

// Phase 10 gives the paper mode its own dedicated accessibility contract. The inherited Phase 8
// suite remains active for the other modes and shared application behavior; older phase verifiers
// still exercise all four original modes.
const activePhase = process.env.FABLE5_VERIFY_PHASE ?? "22";
const inheritedModes = new Set([
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  "16",
  "17",
  "18",
  "19",
  "20",
  "21",
  "22",
]).has(activePhase)
  ? modes.filter((mode) => mode.path !== "/paper")
  : modes;

const lineageParameterNames = [
  "card_id",
  "mapping_id",
  "evaluation_report_id",
  "evaluation_outcome_id",
  "run_id",
  "assessment_id",
  "revocation_id",
] as const;

const syntheticFixtureArchetypes = [
  "Cross Sectional Ranking Claim",
  "Order Flow Claim",
  "Pairs Or Divergence Claim",
  "Social Or News Claim",
  "Trend Or Pattern Claim",
  "Unusual Options Claim",
] as const;

const cardAnatomy = [
  "Original post-derived claim",
  "Normalized interpretation",
  "Required data and testability",
  "Build, defer, or reject rationale",
  "Mock evaluation and cost sensitivity",
  "Deterministic research artifacts",
  "Risk / Compliance status",
  "SIMULATED paper status",
] as const;

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
  expect(width.document).toBeLessThanOrEqual(width.viewport);
}

async function retryEvidenceReadOnce(page: Page) {
  const loadingState = page.getByText(/Loading immutable evidence/i);
  await expect(loadingState).toHaveCount(0, {
    timeout: 90_000,
  });
  const retryableTransportAlert = page
    .getByRole("alert")
    .filter({
      hasText:
        /The API (?:request timed out before deterministic evidence was available|could not be reached)\./,
    })
    .first();
  if (await retryableTransportAlert.isVisible()) {
    await retryableTransportAlert
      .getByRole("button", { name: /^Retry (?:evidence load|read)$/ })
      .click();
    await expect(loadingState).toHaveCount(0, { timeout: 90_000 });
  }
}

async function waitForEvidence(page: Page) {
  await retryEvidenceReadOnce(page);
  await expect(page.locator("[data-visual-corpus='synthetic']")).toHaveCount(1);
  await expect(page.locator("a[href^='/lineage?']").first()).toBeVisible({
    timeout: 90_000,
  });
}

function recordWrites(page: Page) {
  const writes: string[] = [];
  page.on("request", (request) => {
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
      writes.push(`${request.method()} ${request.url()}`);
    }
  });
  return writes;
}

function skipUnlessDesktop(testInfo: TestInfo) {
  test.skip(testInfo.project.name !== "desktop", "Focused behavior runs once on desktop.");
}

async function visibleLineageHrefs(page: Page, scope?: Locator) {
  const values = await (scope ?? page)
    .locator("a[href^='/lineage?']:visible")
    .evaluateAll((links) => links.map((link) => link.getAttribute("href")));
  return [...new Set(values.filter((value): value is string => Boolean(value)))];
}

function expectKnownLineageHref(href: string) {
  const url = new URL(href, "http://fable5.local");
  expect(url.pathname).toBe("/lineage");
  expect(url.searchParams.size).toBeGreaterThan(0);
  for (const [name, value] of url.searchParams) {
    expect(lineageParameterNames).toContain(name);
    expect(value).not.toBe("");
  }
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

async function expectDisclosureWhenStageExists(
  page: Page,
  stageName: string | RegExp,
  disclosureName: string | RegExp,
) {
  const stage = page.locator(".lineageTimeline > li > div > strong").filter({
    hasText: stageName,
  });
  if ((await stage.count()) > 0) {
    await expect(
      page.getByText(disclosureName, { exact: typeof disclosureName === "string" }).first(),
    ).toBeVisible();
  }
}

async function expectResolvedLineage(page: Page) {
  await expect(page.getByRole("heading", { level: 1, name: "Lineage" })).toBeVisible();
  await retryEvidenceReadOnce(page);
  await expect(page.locator(".lineageTimeline")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/Loading source and extraction evidence/i)).toHaveCount(0, {
    timeout: 30_000,
  });
  await expect(page.getByRole("heading", { name: "Referenced result was not found" })).toHaveCount(
    0,
  );
  const lineageAlerts = page.locator(".timelineCard .blockerBanner[role='alert']");
  for (let index = 0; index < (await lineageAlerts.count()); index += 1) {
    const alert = lineageAlerts.nth(index);
    await expect(alert).toContainText("Historical timeline evidence was not resolved");
    await expect(alert.locator("xpath=ancestor::*[contains(@class, 'timelineCard')][1]")).toHaveAttribute(
      "data-blocking",
      "true",
    );
  }
  const lineageConflicts = page.locator(".lineageTimeline > li > div > strong").filter({
    hasText: /Fail-closed (?:ancestor|snapshot|evaluation|revocation) conflict/i,
  });
  for (let index = 0; index < (await lineageConflicts.count()); index += 1) {
    await expect(lineageConflicts.nth(index).locator("xpath=ancestor::li[1]")).toContainText(
      /No .*(?:shown|substituted|inferred)/i,
    );
  }
  await expect(
    page.locator(".lineageTimeline > li > div > strong").filter({
      hasText: "Fail-closed terminal state",
    }),
  ).toBeVisible();

  const url = new URL(page.url());
  const hasAncestorConflict = (await lineageConflicts.filter({
    hasText: "Fail-closed ancestor conflict",
  }).count()) > 0;
  const hasSourceAncestors = [
    "card_id",
    "mapping_id",
    "evaluation_report_id",
    "evaluation_outcome_id",
    "run_id",
    "assessment_id",
  ].some((name) => url.searchParams.has(name));
  if (hasSourceAncestors && !hasAncestorConflict) {
    for (const stage of ["Source input", "Extraction", "Normalized TradingIdeaCard"]) {
      await expect(
        page.locator(".lineageTimeline > li > div > strong").filter({ hasText: stage }),
      ).toBeVisible();
    }
  }
  if (
    !hasAncestorConflict &&
    [
      "mapping_id",
      "evaluation_report_id",
      "evaluation_outcome_id",
      "run_id",
      "assessment_id",
    ].some((name) => url.searchParams.has(name))
  ) {
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText: "Deterministic mapping",
      }),
    ).toBeVisible();
  }
  if (url.searchParams.has("run_id") || url.searchParams.has("assessment_id")) {
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText: "Research artifact",
      }),
    ).toBeVisible();
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText: /Point-in-time snapshot|Fail-closed snapshot conflict/,
      }).first(),
    ).toBeVisible();
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText:
          /Configuration, code, and evaluation|Fail-closed evaluation (?:terminal|conflict)/,
      }),
    ).toBeVisible();
  }
  if (
    url.searchParams.has("evaluation_report_id") ||
    url.searchParams.has("evaluation_outcome_id")
  ) {
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText: /Point-in-time snapshot|Fail-closed snapshot conflict/,
      }).first(),
    ).toBeVisible();
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText:
          /Configuration, code, and evaluation|Fail-closed evaluation (?:terminal|conflict)/,
      }),
    ).toBeVisible();
  }
  if (url.searchParams.has("assessment_id")) {
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText: "Approval assessment and historical evidence timeline",
      }),
    ).toBeVisible();
  }
  if (url.searchParams.has("revocation_id")) {
    await expect(
      page.locator(".lineageTimeline > li > div > strong").filter({
        hasText: "Authorization revocation",
      }),
    ).toBeVisible();
  }

  await expectDisclosureWhenStageExists(
    page,
    "Source input",
    "Inspect committed synthetic source text",
  );
  await expectDisclosureWhenStageExists(
    page,
    "Extraction",
    /^Inspect complete extraction record$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Normalized TradingIdeaCard",
    /^Inspect complete normalized card artifact$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Deterministic mapping",
    /^Inspect complete mapping artifact and rationale$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Point-in-time snapshot",
    /^Inspect complete snapshot artifact$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Configuration, code, and evaluation",
    /^Inspect complete evaluation artifact$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Fail-closed evaluation terminal",
    /^Inspect complete blocked evaluation artifact$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Research artifact",
    /^Inspect complete research artifact$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Approval assessment and historical evidence timeline",
    /^Inspect complete server evidence timeline$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Approval assessment and historical evidence timeline",
    /^Inspect complete (?:complete )?immutable domain audit artifact$/i,
  );
  await expectDisclosureWhenStageExists(
    page,
    "Authorization revocation",
    /^Inspect complete hash-bound domain audit evidence/i,
  );
}

for (const mode of inheritedModes) {
  test(`${mode.heading} landmarks, headings, names, and WCAG checks`, async ({ page }) => {
    const writes = recordWrites(page);
    await page.goto(mode.path, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { level: 1, name: mode.heading })).toBeVisible();
    await waitForEvidence(page);

    await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
    await expect(page.locator("main#main-content")).toHaveCount(1);
    await expect(page.getByRole("contentinfo")).toBeVisible();
    await expect(page.locator("h1")).toHaveCount(1);

    const headingLevels = await page
      .locator("main h1, main h2, main h3, main h4, main h5, main h6")
      .evaluateAll((headings) => headings.map((heading) => Number(heading.tagName.slice(1))));
    headingLevels.forEach((level, index) => {
      if (index > 0) expect(level - headingLevels[index - 1]).toBeLessThanOrEqual(1);
    });

    if (mode.path === "/paper") {
      await expect(page.locator("main form, main input, main select, main textarea")).toHaveCount(0);
      await expect(page.locator("main button")).toHaveCount(0);
      await expect(
        page.getByRole("link", {
          name: /buy|sell|submit|order ticket|quantity|side|fill|position|broker/i,
        }),
      ).toHaveCount(0);
    }

    await expectNoHorizontalPageOverflow(page);
    await expectNoAxeViolations(page);
    expect(writes).toEqual([]);
  });
}

test("each of the six synthetic idea archetypes exposes the complete honest anatomy", async ({
  page,
}, testInfo) => {
  skipUnlessDesktop(testInfo);
  const writes = recordWrites(page);
  await page.goto("/ideas", { waitUntil: "domcontentloaded" });
  await waitForEvidence(page);

  const cards = page.locator(".strategyCard[data-synthetic-fixture='true']");
  expect(await cards.count()).toBeGreaterThanOrEqual(syntheticFixtureArchetypes.length);
  await expect(page.locator(".strategyCard:not([data-synthetic-fixture='true'])")).toHaveCount(0);
  for (const archetype of syntheticFixtureArchetypes) {
    const matchingCards = cards.filter({
      has: page.getByRole("heading", { exact: true, level: 2, name: archetype }),
    });
    expect(await matchingCards.count()).toBeGreaterThanOrEqual(1);
    const card = matchingCards.first();
    await expect(card.locator("blockquote")).toBeVisible();
    for (const heading of cardAnatomy) {
      await expect(card.getByRole("heading", { level: 3, name: heading })).toBeVisible();
    }
    await expect(
      card
        .getByText(
          /^(?:BUILD_RESEARCH|DEFER|DEFER_READ_ONLY|REJECT_PLATFORM|NON_TESTABLE|No immutable mapping exists\. No build, defer, or reject verdict is inferred\.)$/,
        )
        .first(),
    ).toBeVisible();
    await expect(card.getByRole("heading", { level: 4, name: "Preserved ambiguity" })).toBeVisible();

    const mockSummary = card.locator("[aria-label='Server-owned mock backtest summary']");
    if ((await mockSummary.count()) > 0) {
      await expect(mockSummary.first()).toBeVisible();
      await expect(card.getByText(/COST_STRESS/).first()).toBeVisible();
    } else {
      await expect(card.getByText(/No linked mock evaluation exists/i)).toBeVisible();
    }
    await expect(
      card
        .getByText(/No linked research artifact exists|Trace research artifact/i)
        .first(),
    ).toBeVisible();
    await expect(
      card
        .getByText(/No linked Phase 7 assessment exists|Trace assessment artifact/i)
        .first(),
    ).toBeVisible();
    await expect(card.getByText("SIMULATED", { exact: true }).first()).toBeVisible();
    await expect(card.locator("a[href^='/lineage?card_id=']")).toBeVisible();
  }

  await page.goto("/research", { waitUntil: "domcontentloaded" });
  await waitForEvidence(page);
  const researchRuns = page.locator(".researchRunCard");
  const researchRunCount = await researchRuns.count();
  expect(researchRunCount).toBeGreaterThan(1);
  let passResearchCount = 0;
  for (let index = 0; index < researchRunCount; index += 1) {
    const run = researchRuns.nth(index);
    const status = (await run.locator(":scope > .cardHeader .statusBadge").textContent())?.trim();
    const configuration = (
      await run
        .locator("dt")
        .filter({ hasText: /^Configuration identity$/ })
        .first()
        .locator("xpath=following-sibling::dd[1]")
        .textContent()
    )?.trim();
    if (status === "PASS_RESEARCH") {
      passResearchCount += 1;
      expect(configuration).toBe("phase6-a-pass-v2");
    }
    if (configuration !== "phase6-a-pass-v2") expect(status).not.toBe("PASS_RESEARCH");
    if ((await run.getAttribute("data-blocking")) === "true") {
      await expect(run.locator(":scope > .blockerBanner")).toBeVisible();
    }
  }
  expect(passResearchCount).toBeGreaterThan(0);
  expect(writes).toEqual([]);
});

test("keyboard skip, real tab order, disclosure focus, and reduced motion", async ({
  page,
}, testInfo) => {
  skipUnlessDesktop(testInfo);
  const writes = recordWrites(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/ideas", { waitUntil: "domcontentloaded" });

  await page.keyboard.press("Tab");
  const skipLink = page.getByRole("link", { name: "Skip to main content" });
  await expect(skipLink).toBeFocused();
  await expectVisibleFocus(skipLink);
  await page.keyboard.press("Enter");
  const main = page.locator("main#main-content");
  await expect(main).toBeFocused();
  await expectVisibleFocus(main);
  await waitForEvidence(page);
  await expect(main).toBeFocused();

  let tabbedToSummary = false;
  for (let index = 0; index < 80; index += 1) {
    await page.keyboard.press("Tab");
    const activeTagName = await page.evaluate(() => document.activeElement?.tagName ?? "");
    expect(activeTagName).not.toBe("BODY");
    if (activeTagName === "SUMMARY") {
      tabbedToSummary = true;
      break;
    }
  }
  expect(tabbedToSummary).toBe(true);
  const focusedSummaryCandidate = page.locator("summary:focus");
  await expect(focusedSummaryCandidate).toHaveCount(1);
  const focusedSummaryIndex = await page.locator("summary").evaluateAll((summaries) =>
    summaries.findIndex((summary) => summary === document.activeElement),
  );
  expect(focusedSummaryIndex).toBeGreaterThanOrEqual(0);
  const focusedSummary = page.locator("summary").nth(focusedSummaryIndex);
  await expectVisibleFocus(focusedSummary);

  const disclosure = focusedSummary.locator("xpath=..");
  await page.keyboard.press("Enter");
  await expect(disclosure).toHaveAttribute("open", "");
  await page.keyboard.press("Enter");
  await expect(disclosure).not.toHaveAttribute("open", "");
  await expect(focusedSummary).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(focusedSummary).not.toBeFocused();
  await page.keyboard.press("Tab");
  await expect(focusedSummary).toBeFocused();

  const motion = await page.evaluate(() => ({
    animationDuration: getComputedStyle(document.body).animationDuration,
    scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
    transitionDuration: getComputedStyle(document.body).transitionDuration,
  }));
  const durationMilliseconds = (value: string) =>
    Math.max(
      ...value.split(",").map((duration) => {
        const normalized = duration.trim();
        if (!normalized) return 0;
        return normalized.endsWith("ms")
          ? Number.parseFloat(normalized)
          : Number.parseFloat(normalized) * 1_000;
      }),
    );
  expect(motion.scrollBehavior).toBe("auto");
  expect(durationMilliseconds(motion.animationDuration)).toBeLessThanOrEqual(0.011);
  expect(durationMilliseconds(motion.transitionDuration)).toBeLessThanOrEqual(0.011);
  expect(writes).toEqual([]);
});

for (const mode of inheritedModes) {
  test(`${mode.heading} loading, unavailable, and retry-focus states remain accessible`, async ({
    page,
  }, testInfo) => {
    skipUnlessDesktop(testInfo);
    const writes = recordWrites(page);
    let releaseInitialRequest = () => {};
    const initialRequestGate = new Promise<void>((resolve) => {
      releaseInitialRequest = resolve;
    });
    let releaseRetryRequest = () => {};
    const retryRequestGate = new Promise<void>((resolve) => {
      releaseRetryRequest = resolve;
    });
    let cardRequestCount = 0;
    await page.route("**/v1/cards*", async (route) => {
      cardRequestCount += 1;
      await (cardRequestCount === 1 ? initialRequestGate : retryRequestGate);
      await route.fulfill({
        body: JSON.stringify({ detail: "Synthetic unavailable state" }),
        contentType: "application/json",
        headers: { "Access-Control-Allow-Origin": "*" },
        status: 503,
      });
    });

    await page.goto(mode.path, { waitUntil: "domcontentloaded" });
    const loading = page.getByText(/Loading immutable evidence/i);
    await expect(loading).toBeVisible();
    await expect(loading).toHaveAttribute("role", "status");
    await expectNoAxeViolations(page);

    releaseInitialRequest();
    const unavailable = page
      .getByRole("main")
      .getByRole("alert")
      .filter({ hasText: /unavailable|could not be loaded/i })
      .first();
    await expect(unavailable).toBeVisible({ timeout: 30_000 });
    await expect(unavailable).toContainText(/unavailable|could not be loaded/i);
    await expectNoAxeViolations(page);

    const retryButton = page.getByRole("button", {
      name: /^Retry (?:evidence load|read)$/,
    });
    await retryButton.focus();
    await expect(retryButton).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByText(/Loading immutable evidence/i)).toBeVisible();
    releaseRetryRequest();
    await expect(unavailable).toBeVisible({ timeout: 30_000 });
    await expect(retryButton).toBeFocused();
    await expectVisibleFocus(retryButton);
    expect(writes).toEqual([]);
  });
}

test("every visible result has a direct lineage href and every parameter or branch shape resolves fail closed", async ({
  page,
}, testInfo) => {
  skipUnlessDesktop(testInfo);
  test.setTimeout(
    process.env.FABLE5_PHASE9_BROWSER_TIMEOUT_PROFILE === "1" ? 2_100_000 : 1_200_000,
  );
  const writes = recordWrites(page);
  const initialRepresentatives = new Map<string, { href: string; modePath: string }>();
  const representedParameters = new Set<string>();

  for (const mode of inheritedModes) {
    await page.goto(mode.path, { waitUntil: "domcontentloaded" });
    await waitForEvidence(page);
    const modeHrefs = await visibleLineageHrefs(page);
    expect(modeHrefs.length).toBeGreaterThan(0);
    modeHrefs.forEach(expectKnownLineageHref);

    const parametersRepresented = new Map<string, string>();
    for (const href of modeHrefs) {
      const parameters = new URL(href, "http://fable5.local").searchParams;
      for (const name of lineageParameterNames) {
        if (parameters.has(name) && !parametersRepresented.has(name)) {
          parametersRepresented.set(name, href);
        }
        if (parameters.has(name) && !initialRepresentatives.has(name)) {
          initialRepresentatives.set(name, { href, modePath: mode.path });
        }
        if (parameters.has(name)) representedParameters.add(name);
      }
    }
    const requiredParameters =
      mode.path === "/ideas"
        ? ["card_id", "mapping_id", "run_id"]
        : mode.path === "/research"
          ? ["run_id"]
          : mode.path === "/paper"
            ? ["assessment_id", "revocation_id"]
            : ["assessment_id", "revocation_id"];
    requiredParameters.forEach((name) => expect(parametersRepresented.has(name)).toBe(true));
    if (mode.path === "/ideas") {
      expect(
        parametersRepresented.has("evaluation_report_id") ||
          parametersRepresented.has("evaluation_outcome_id"),
      ).toBe(true);
    }
  }
  const branchRepresentatives = new Map<string, { href: string; parentHref: string }>();
  const resolvedInitialHrefs = new Set<string>();
  for (const { href, modePath } of initialRepresentatives.values()) {
    if (resolvedInitialHrefs.has(href)) continue;
    resolvedInitialHrefs.add(href);
    await page.goto(modePath, { waitUntil: "domcontentloaded" });
    await waitForEvidence(page);
    await page.locator(`a[href="${href}"]`).first().click();
    await page.waitForURL((url) => `${url.pathname}${url.search}` === href, {
      timeout: 30_000,
    });
    await expectResolvedLineage(page);

    const branchSection = page.locator(
      "section[aria-labelledby='lineage-branches-heading']",
    );
    if ((await branchSection.count()) === 0) continue;
    const exactBranches = await visibleLineageHrefs(page, branchSection);
    expect(exactBranches.length).toBeGreaterThan(0);
    exactBranches.forEach((branchHref) => {
      expectKnownLineageHref(branchHref);
      const branchUrl = new URL(branchHref, "http://fable5.local");
      for (const name of lineageParameterNames) {
        if (branchUrl.searchParams.has(name)) representedParameters.add(name);
      }
      const shape = [...branchUrl.searchParams.keys()].sort().join("+");
      if (!branchRepresentatives.has(shape)) {
        branchRepresentatives.set(shape, { href: branchHref, parentHref: href });
      }
    });
  }

  expect([...representedParameters].sort()).toEqual([...lineageParameterNames].sort());
  expect(branchRepresentatives.size).toBeGreaterThan(0);
  for (const { href, parentHref } of branchRepresentatives.values()) {
    await page.goto(parentHref, { waitUntil: "domcontentloaded" });
    await expectResolvedLineage(page);
    const branchSection = page.locator(
      "section[aria-labelledby='lineage-branches-heading']",
    );
    await branchSection.locator(`a[href="${href}"]`).click();
    await page.waitForURL((url) => `${url.pathname}${url.search}` === href, {
      timeout: 30_000,
    });
    await expectResolvedLineage(page);
  }
  expect(writes).toEqual([]);
});

test("resolved and fail-closed lineage states pass WCAG checks without substitution", async ({
  page,
}, testInfo) => {
  skipUnlessDesktop(testInfo);
  test.setTimeout(420_000);
  const writes = recordWrites(page);

  await page.goto("/risk", { waitUntil: "domcontentloaded" });
  await waitForEvidence(page);
  await page.locator("a[href*='assessment_id=']").first().click();
  await expectResolvedLineage(page);
  await expectNoAxeViolations(page);

  await page.goto(
    "/lineage?assessment_id=00000000-0000-5000-8000-000000000808",
    { waitUntil: "domcontentloaded" },
  );
  await expect(page.getByRole("heading", { name: "Referenced result was not found" })).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByRole("status")).toContainText(/No relationship was inferred/i);
  await expectNoAxeViolations(page);

  await page.goto("/ideas", { waitUntil: "domcontentloaded" });
  await waitForEvidence(page);
  const cardHref = await page.locator("a[href^='/lineage?card_id=']").first().getAttribute("href");
  expect(cardHref).not.toBeNull();
  const cardId = new URL(cardHref!, "http://localhost").searchParams.get("card_id");
  expect(cardId).not.toBeNull();
  await page.route(/\/v1\/source-versions\/[^/?]+/, async (route) => {
    await route.fulfill({
      body: JSON.stringify({ detail: "Synthetic source unavailable state" }),
      contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": "*" },
      status: 503,
    });
  });
  await page.locator(`a[href="${cardHref}"]`).first().click();
  await page.waitForURL((url) => `${url.pathname}${url.search}` === cardHref, {
    timeout: 30_000,
  });
  const sourceFailure = page
    .getByRole("main")
    .getByRole("alert")
    .filter({ hasText: /lineage stops at the last retrievable immutable identifier/i });
  await expect(sourceFailure).toContainText(/lineage stops at the last retrievable immutable identifier/i, {
    timeout: 90_000,
  });
  const normalizedCard = page
    .locator(".lineageTimeline > li")
    .filter({ hasText: "Normalized TradingIdeaCard" });
  await expect(normalizedCard).toBeVisible();
  await expect(normalizedCard).toContainText(`Card ID: ${cardId}`);
  await expect(normalizedCard.locator(".visualMask")).toHaveText(/^[a-f0-9]{64}$/);
  await normalizedCard.getByText("Inspect complete normalized card artifact").click();
  await expect(normalizedCard.locator("pre")).toContainText(`"card_id": "${cardId}"`);
  const cardArtifact = JSON.parse((await normalizedCard.locator("pre").textContent()) ?? "{}");
  expect(cardArtifact.extraction_request_id).toEqual(expect.any(String));
  const extractionEvidence = page.locator(".lineageTimeline > li", {
    has: page.getByText("Extraction", { exact: true }),
  });
  await expect(extractionEvidence).toContainText(
    `Request ID: ${cardArtifact.extraction_request_id}`,
  );
  await expect(extractionEvidence.locator(".visualMask")).toHaveText(/^[a-f0-9]{64}$/);
  await extractionEvidence.getByText("Inspect complete extraction record").click();
  await expect(extractionEvidence.locator("pre")).toContainText(
    `"extraction_request_id": "${cardArtifact.extraction_request_id}"`,
  );
  await expectNoAxeViolations(page);
  expect(writes).toEqual([]);
});

// Browser QA intentionally performs GET/HEAD/OPTIONS only. Reference-only create workflows are
// exercised by deterministic component integration tests with mocked generated-contract responses.
