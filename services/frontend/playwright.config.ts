import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL;

if (!baseURL) {
  throw new Error(
    "PLAYWRIGHT_BASE_URL is required. Run against the deterministic Phase 8 acceptance corpus.",
  );
}

const baseHost = new URL(baseURL).hostname;
if (!new Set(["127.0.0.1", "localhost", "host.docker.internal"]).has(baseHost)) {
  throw new Error("Phase 8 browser QA only runs against an isolated local acceptance stack.");
}

const updatesRequested = process.env.FABLE5_UPDATE_SNAPSHOTS === "1";
if (updatesRequested && process.env.FABLE5_VISUAL_CORPUS !== "synthetic") {
  throw new Error("Snapshot updates require the explicit synthetic-corpus guard.");
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  timeout: 240_000,
  workers: 1,
  expect: {
    timeout: 15_000,
    toHaveScreenshot: {
      animations: "disabled",
      caret: "hide",
      maxDiffPixelRatio: 0,
      scale: "css",
    },
  },
  outputDir: "./.next/playwright-results",
  reporter: [["list"]],
  snapshotPathTemplate:
    "{testDir}/__screenshots__/{testFilePath}/{arg}-{projectName}-{platform}{ext}",
  updateSnapshots: updatesRequested ? "all" : "none",
  use: {
    baseURL,
    colorScheme: "light",
    locale: "en-US",
    serviceWorkers: "block",
    timezoneId: "UTC",
    trace: "off",
  },
  projects: [
    {
      name: "mobile",
      use: {
        ...devices["Desktop Chrome"],
        deviceScaleFactor: 1,
        isMobile: true,
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: "tablet",
      use: {
        ...devices["Desktop Chrome"],
        deviceScaleFactor: 1,
        isMobile: true,
        viewport: { width: 820, height: 1_180 },
      },
    },
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        deviceScaleFactor: 1,
        viewport: { width: 1_440, height: 1_000 },
      },
    },
  ],
});
