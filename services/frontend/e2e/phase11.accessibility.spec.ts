import AxeBuilder from "@axe-core/playwright";
import { validateOpenApiResponse } from "@fable5/contracts";
import {
  expect,
  test,
  type Download,
  type Locator,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";

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
import {
  phase11BlockedEvidenceBundle,
  phase11CompletedEvidenceBundle,
  phase11EvidenceBundleFor,
  phase11EvidenceFilename,
  type LocalSimulationEvidenceBundle,
} from "./phase11.fixtures";

const EVIDENCE_OPERATION =
  "GET /v1/local-simulations/{simulation_run_id}/evidence-bundle" as const;

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
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Origin": "*",
    },
    status: 204,
  });
}

async function routeAssessmentEvidence(page: Page) {
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

async function routeSimulationEvidence(
  page: Page,
  artifacts: PaperSimulationArtifact[],
  evidenceRequests: string[],
  bundleForArtifact: (
    artifact: PaperSimulationArtifact,
  ) => LocalSimulationEvidenceBundle | undefined = phase11EvidenceBundleFor,
) {
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

    const segments = url.pathname.split("/").filter(Boolean);
    const evidenceRequested = segments.at(-1) === "evidence-bundle";
    const simulationRunId = decodeURIComponent(
      segments.at(evidenceRequested ? -2 : -1) ?? "",
    );
    const artifact = artifacts.find(
      (candidate) => candidate.simulation_run_id === simulationRunId,
    );
    if (!artifact) {
      await fulfillJson(route, { detail: "Synthetic artifact not found." }, 404);
      return;
    }
    if (!evidenceRequested) {
      await fulfillJson(route, artifact);
      return;
    }

    evidenceRequests.push(`${request.method()} ${url.pathname}`);
    const bundle = bundleForArtifact(artifact);
    await new Promise((resolve) => globalThis.setTimeout(resolve, 40));
    await fulfillJson(
      route,
      bundle ?? { detail: "Synthetic evidence bundle not found." },
      bundle ? 200 : 404,
    );
  });
}

async function waitForPaperWorkspace(page: Page) {
  await expect(page.getByRole("heading", { level: 1, name: "Simulated Paper Status" })).toBeVisible();
  await expect(page.getByLabel("Approval assessment")).toBeEnabled({ timeout: 90_000 });
  await expect(page.locator("[data-visual-corpus='synthetic']")).toHaveCount(1, {
    timeout: 90_000,
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

async function downloadText(download: Download) {
  const stream = await download.createReadStream();
  if (!stream) throw new Error("Playwright did not expose the local evidence download stream.");
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8");
}

async function prepareAndDownload(
  page: Page,
  artifact: PaperSimulationArtifact,
  expectedBundle: LocalSimulationEvidenceBundle,
  evidenceRequests: string[],
) {
  const card = page.getByRole("article", { name: artifact.simulation_run_id });
  await expect(card).toBeVisible({ timeout: 30_000 });
  const disclosure = card.locator("details.simulationArtifactDisclosure");
  const summary = disclosure.getByText("Inspect exact persisted simulation artifact JSON", {
    exact: true,
  });
  await summary.focus();
  await expect(summary).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(disclosure).toHaveAttribute("open", "");

  const region = disclosure.getByRole("region", { name: "Prepare local evidence bundle" });
  const prepare = region.getByRole("button", { name: "Prepare evidence bundle" });
  await prepare.focus();
  await expect(prepare).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(region).toHaveAttribute("aria-busy", "true");
  await expect(region.getByText("Validated historical bundle ready.")).toBeVisible();
  await expect(region).toHaveAttribute("aria-busy", "false");
  await expect(prepare).toBeFocused();

  const filename = phase11EvidenceFilename(expectedBundle);
  const verifierCommand =
    `python scripts/verify_local_simulation_evidence.py --bundle "${filename}" ` +
    `--expected-bundle-sha256 ${expectedBundle.bundle_sha256}`;
  await expect(region.getByText(expectedBundle.bundle_schema_version, { exact: true })).toBeVisible();
  await expect(region.getByText(filename, { exact: true })).toBeVisible();
  await expect(region.getByText(expectedBundle.bundle_sha256, { exact: true })).toBeVisible();
  await expect(region.getByText(verifierCommand, { exact: true })).toBeVisible();
  if (artifact.outcome === "BLOCKED") {
    await expect(
      region.getByText(/BLOCKED historical evidence: zero simulated ledger entries/),
    ).toBeVisible();
  }

  const requestCountBeforeDownload = evidenceRequests.length;
  await page.keyboard.press("Tab");
  const downloadButton = region.getByRole("button", { name: "Download validated JSON" });
  await expect(downloadButton).toBeFocused();
  const downloadPromise = page.waitForEvent("download");
  await page.keyboard.press("Enter");
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(filename);
  const contents = await downloadText(download);
  expect(contents).not.toContain("\r");
  expect(contents.endsWith("\n")).toBe(true);
  expect(contents.endsWith("\n\n")).toBe(false);
  const downloadedBundle: unknown = JSON.parse(contents);
  expect(validateOpenApiResponse(EVIDENCE_OPERATION, 200, downloadedBundle)).toBe(true);
  expect(downloadedBundle).toEqual(expectedBundle);
  expect((downloadedBundle as LocalSimulationEvidenceBundle).bundle_sha256).toBe(
    expectedBundle.bundle_sha256,
  );
  expect((downloadedBundle as LocalSimulationEvidenceBundle).simulation_artifact_sha256).toBe(
    artifact.artifact_sha256,
  );
  expect((downloadedBundle as LocalSimulationEvidenceBundle).simulation).toEqual(artifact);
  expect(evidenceRequests).toHaveLength(requestCountBeforeDownload);
}

test("completed and blocked historical bundles prepare and download accessibly with one GET each", async ({
  page,
}) => {
  const artifacts = [phase10BlockedArtifact, phase10CompletedArtifact];
  const evidenceRequests: string[] = [];
  const writes: string[] = [];
  page.on("request", (request) => {
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
      writes.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await routeAssessmentEvidence(page);
  await routeSimulationEvidence(page, artifacts, evidenceRequests);

  await page.goto("/paper", { waitUntil: "domcontentloaded" });
  await waitForPaperWorkspace(page);
  await prepareAndDownload(
    page,
    phase10CompletedArtifact,
    phase11CompletedEvidenceBundle,
    evidenceRequests,
  );
  await prepareAndDownload(
    page,
    phase10BlockedArtifact,
    phase11BlockedEvidenceBundle,
    evidenceRequests,
  );

  expect(evidenceRequests).toEqual([
    `GET /v1/local-simulations/${phase10CompletedArtifact.simulation_run_id}/evidence-bundle`,
    `GET /v1/local-simulations/${phase10BlockedArtifact.simulation_run_id}/evidence-bundle`,
  ]);
  expect(writes).toEqual([]);
  await expectReducedMotion(page.locator(".localEvidenceExport").first());
  await expectNoHorizontalPageOverflow(page);
  await expectNoAxeViolations(page);
});

test("a schema-valid bundle for a different artifact fails closed", async ({
  page,
}, testInfo: TestInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Focused mismatch behavior runs once on desktop.");
  const evidenceRequests: string[] = [];
  const writes: string[] = [];
  let downloads = 0;
  page.on("download", () => {
    downloads += 1;
  });
  page.on("request", (request) => {
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) {
      writes.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });
  await routeAssessmentEvidence(page);
  await routeSimulationEvidence(
    page,
    [phase10CompletedArtifact],
    evidenceRequests,
    () => phase11BlockedEvidenceBundle,
  );

  await page.goto("/paper", { waitUntil: "domcontentloaded" });
  await waitForPaperWorkspace(page);
  const card = page.getByRole("article", {
    name: phase10CompletedArtifact.simulation_run_id,
  });
  const disclosure = card.locator("details.simulationArtifactDisclosure");
  await disclosure.locator("summary").click();
  const region = disclosure.getByRole("region", { name: "Prepare local evidence bundle" });
  await region.getByRole("button", { name: "Prepare evidence bundle" }).click();

  await expect(region.getByRole("alert")).toContainText(
    "does not match this exact persisted simulation artifact",
  );
  await expect(region.getByRole("button", { name: "Download validated JSON" })).toHaveCount(0);
  expect(evidenceRequests).toEqual([
    `GET /v1/local-simulations/${phase10CompletedArtifact.simulation_run_id}/evidence-bundle`,
  ]);
  expect(downloads).toBe(0);
  expect(writes).toEqual([]);
  await expectNoAxeViolations(page);
});
