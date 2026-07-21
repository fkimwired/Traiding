import { expect, test, type Locator, type Page } from "@playwright/test";
import path from "node:path";

const stabilityStyles = path.join(__dirname, "visual-stability.css");

const modes = [
  {
    heading: "Idea Intake",
    path: "/ideas",
    slug: "idea-intake",
    target: ".strategyCard > .blockerBanner",
  },
  {
    heading: "Research Lab",
    path: "/research",
    slug: "research-lab",
    target:
      ".evidenceCard[data-blocking='true'] > .blockerBanner, .governanceCard[data-blocking='true'] > .blockerBanner",
  },
  {
    heading: "Simulated Paper Status",
    path: "/paper",
    slug: "simulated-paper-status",
    target: ".governanceCard[data-blocking='true'] > .blockerBanner",
  },
  {
    heading: "Risk / Compliance",
    path: "/risk",
    slug: "risk-compliance",
    target: ".governanceCard[data-blocking='true'] > .blockerBanner",
  },
] as const;

// Phase 10 intentionally supersedes the Phase 8 paper surface with one local mock-only
// simulation control. Its dedicated Phase 10 snapshots own that mode; the inherited suite keeps
// the other three modes and shared layout pinned to their accepted Phase 8 baselines.
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

function dynamicEvidence(page: Page): Locator[] {
  return [
    page.locator("time"),
    page.locator("code"),
    page.locator("pre"),
    page.locator("blockquote"),
    page.locator(".mono"),
    page.locator(".artifactHash"),
    page.locator(".visualMask"),
  ];
}

async function waitForCorpus(page: Page, target: string) {
  const loadingState = page.getByText(/loading immutable evidence/i);
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
  const negativeEvidence = page.locator(target).first();
  await expect(negativeEvidence).toBeVisible({ timeout: 90_000 });
  await expect(page.locator("[data-visual-corpus='synthetic']")).toHaveCount(1);
  return negativeEvidence;
}

for (const mode of inheritedModes) {
  test(`${mode.slug} responsive negative-state snapshot`, async ({ page }) => {
    const writes: string[] = [];
    page.on("request", (request) => {
      if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
        writes.push(`${request.method()} ${request.url()}`);
      }
    });

    await page.goto(mode.path, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { level: 1, name: mode.heading })).toBeVisible();
    const negativeEvidence = await waitForCorpus(page, mode.target);

    // A permitted transport retry restores focus to the main landmark and its
    // button click may scroll an error panel into view. Accessibility coverage
    // asserts that behavior separately; visual baselines always start from the
    // same unfocused, top-of-page viewport.
    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
      window.scrollTo({ behavior: "auto", left: 0, top: 0 });
    });
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

    if (mode.path === "/ideas") {
      expect(
        await page.locator(".strategyCard[data-synthetic-fixture='true']").count(),
      ).toBeGreaterThanOrEqual(6);
      await expect(page.locator(".strategyCard:not([data-synthetic-fixture='true'])")).toHaveCount(
        0,
      );
    }

    if (mode.path === "/paper" || mode.path === "/risk") {
      await expect(
        page.locator(".governanceCard .cardHeader h2.visualMask").first(),
      ).toHaveCSS("font-family", /monospace/);
    }

    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(hasHorizontalOverflow).toBe(false);
    expect(writes).toEqual([]);

    await expect(page).toHaveScreenshot(`${mode.slug}-mode.png`, {
      fullPage: false,
      mask: dynamicEvidence(page),
      maskColor: "#d9ddd8",
      stylePath: stabilityStyles,
    });

    await negativeEvidence.evaluate((element) => {
      element.scrollIntoView({ behavior: "auto", block: "center", inline: "nearest" });
    });
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    await expect(page).toHaveScreenshot(`${mode.slug}-negative.png`, {
      fullPage: false,
      mask: dynamicEvidence(page),
      maskColor: "#d9ddd8",
      stylePath: stabilityStyles,
    });
  });
}
