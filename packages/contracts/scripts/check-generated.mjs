import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const temporaryDirectory = mkdtempSync(join(tmpdir(), "fable5-contracts-"));
const temporaryOutput = join(temporaryDirectory, "api.generated.ts");
const executable = resolve(process.cwd(), "../../node_modules/openapi-typescript/bin/cli.js");

try {
  const result = spawnSync(
    process.execPath,
    [executable, "openapi.json", "--output", temporaryOutput],
    { cwd: process.cwd(), encoding: "utf8" },
  );
  if (result.status !== 0) {
    process.stderr.write(result.stderr || result.stdout);
    process.exit(result.status ?? 1);
  }

  const committed = readFileSync("src/api.generated.ts", "utf8").replaceAll("\r\n", "\n");
  const generated = readFileSync(temporaryOutput, "utf8").replaceAll("\r\n", "\n");
  if (committed !== generated) {
    process.stderr.write(
      "Generated TypeScript contracts are stale. Run `npm run contracts:generate`.\n",
    );
    process.exit(1);
  }
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
