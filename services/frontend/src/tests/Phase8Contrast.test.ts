import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const styles = readFileSync(resolve(process.cwd(), "src/app/phase8.css"), "utf8");

function token(name: string) {
  const match = styles.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6})`, "i"));
  expect(match, `missing CSS token --${name}`).not.toBeNull();
  return match![1];
}

function relativeLuminance(hex: string) {
  const channels = [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16) / 255);
  const [red, green, blue] = channels.map((channel) =>
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(first: string, second: string) {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  return (
    (Math.max(firstLuminance, secondLuminance) + 0.05) /
    (Math.min(firstLuminance, secondLuminance) + 0.05)
  );
}

describe("Phase 8 non-text contrast tokens", () => {
  const surfaces = [
    "p8-canvas",
    "p8-paper",
    "p8-paper-strong",
    "p8-red-soft",
    "p8-green-soft",
    "p8-amber-soft",
    "p8-blue-soft",
  ];

  it("keeps at least one ring in the dual focus indicator above 3:1 on every surface", () => {
    const primary = token("p8-focus");
    const contrastRing = token("p8-focus-contrast");

    for (const surface of surfaces) {
      const background = token(surface);
      expect(
        Math.max(contrast(primary, background), contrast(contrastRing, background)),
        `focus indicator against --${surface}`,
      ).toBeGreaterThanOrEqual(3);
    }
    expect(styles).toMatch(
      /:focus-visible\s*{[^}]*box-shadow:\s*[^;]*var\(--p8-focus\)[^}]*outline:\s*[^;]*var\(--p8-focus-contrast\)/,
    );
  });

  it("keeps the shared control boundary above 3:1 against control and panel surfaces", () => {
    const boundary = token("p8-line-strong");

    for (const surface of surfaces) {
      expect(contrast(boundary, token(surface)), `control boundary against --${surface}`).toBeGreaterThanOrEqual(
        3,
      );
    }
    expect(styles).toMatch(
      /\.fieldGroup input,[\s\S]*?\.fieldGroup textarea\s*{[^}]*border:\s*1px solid var\(--p8-line-strong\)/,
    );
  });
});
