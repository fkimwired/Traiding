import { describe, expect, it } from "vitest";

import { matchesOpenApiStringPattern } from "../../../../packages/contracts/src/validate-response";

const PYDANTIC_DECIMAL_FIXED_PATTERN = String.raw`^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$`;

describe("generated OpenAPI response string-pattern compatibility", () => {
  it.each(["0", "-0.25", ".5", "5."])(
    "accepts a valid fixed-notation Decimal string: %s",
    (value) => {
      expect(matchesOpenApiStringPattern(PYDANTIC_DECIMAL_FIXED_PATTERN, value)).toBe(true);
    },
  );

  it.each([
    "1E-7",
    "1.5623501573662992737949E-7",
    "-0.25e+12",
    ".5e2",
    "5.e0",
  ])("accepts a finite scientific-notation Decimal string: %s", (value) => {
    expect(matchesOpenApiStringPattern(PYDANTIC_DECIMAL_FIXED_PATTERN, value)).toBe(true);
  });

  it.each([
    "1E",
    "1E+",
    "1E-",
    "1E+-2",
    "1e2e3",
    "E2",
    ".E2",
    "NaN",
    "Infinity",
    "-Infinity",
  ])("rejects a malformed or non-finite Decimal string: %s", (value) => {
    expect(matchesOpenApiStringPattern(PYDANTIC_DECIMAL_FIXED_PATTERN, value)).toBe(false);
  });

  it("does not relax any other generated string pattern", () => {
    expect(matchesOpenApiStringPattern("^[A-Z]+$", "ABC")).toBe(true);
    expect(matchesOpenApiStringPattern("^[A-Z]+$", "1E-7")).toBe(false);
  });
});
