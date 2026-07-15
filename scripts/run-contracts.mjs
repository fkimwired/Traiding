import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const root = resolve(import.meta.dirname, "..");
const mode = process.argv[2];
if (!new Set(["generate", "check"]).has(mode)) {
  process.stderr.write("Usage: node scripts/run-contracts.mjs <generate|check>\n");
  process.exit(2);
}

const candidates = [
  process.env.VIRTUAL_ENV
    ? join(process.env.VIRTUAL_ENV, process.platform === "win32" ? "Scripts/python.exe" : "bin/python")
    : null,
  join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
  process.platform === "win32" ? "python.exe" : "python",
].filter(Boolean);
const python = candidates.find(
  (candidate) =>
    (!candidate.includes("/") && !candidate.includes("\\")) || existsSync(candidate),
);

if (!python) {
  process.stderr.write(
    "Python was not found. Create .venv and install .[dev] with requirements.lock.\n",
  );
  process.exit(1);
}

const exportArguments = ["scripts/export_openapi.py"];
if (mode === "check") exportArguments.push("--check");
const exported = spawnSync(python, exportArguments, { cwd: root, encoding: "utf8", stdio: "inherit" });
if (exported.status !== 0) process.exit(exported.status ?? 1);

const contractRoot = join(root, "packages", "contracts");
const commands =
  mode === "check"
    ? [[join(contractRoot, "scripts", "check-generated.mjs")]]
    : [
        [
          join(root, "node_modules", "openapi-typescript", "bin", "cli.js"),
          "openapi.json",
          "--output",
          "src/api.generated.ts",
        ],
        [join(contractRoot, "scripts", "generate-runtime.mjs")],
      ];

for (const command of commands) {
  const generated = spawnSync(process.execPath, command, {
    cwd: contractRoot,
    encoding: "utf8",
    stdio: "inherit",
  });
  if (generated.error) {
    process.stderr.write(`${generated.error.message}\n`);
  }
  if (generated.status !== 0) process.exit(generated.status ?? 1);
}
