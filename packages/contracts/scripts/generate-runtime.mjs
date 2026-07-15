import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const contractRoot = resolve(import.meta.dirname, "..");
const outputPath = resolve(contractRoot, process.argv[2] ?? "src/runtime.generated.ts");
const openapi = JSON.parse(readFileSync(resolve(contractRoot, "openapi.json"), "utf8"));

function enumValues(schemaName) {
  const values = openapi?.components?.schemas?.[schemaName]?.enum;
  if (!Array.isArray(values) || values.some((value) => typeof value !== "string")) {
    throw new Error(`OpenAPI schema ${schemaName} does not expose a string enum.`);
  }
  return values;
}

const sourceTypes = enumValues("SourceType");
const sourceAuthorities = enumValues("SourceAuthority");
const userIntakeSourceTypes = sourceTypes.filter((value) => value !== "synthetic_fixture");
if (userIntakeSourceTypes.length !== sourceTypes.length - 1) {
  throw new Error("OpenAPI SourceType must contain exactly one reserved synthetic_fixture value.");
}

const httpMethods = new Set(["delete", "get", "patch", "post", "put"]);
const successfulJsonResponseSchemas = {};
for (const path of Object.keys(openapi.paths ?? {}).sort()) {
  const pathItem = openapi.paths[path];
  for (const method of Object.keys(pathItem).sort()) {
    if (!httpMethods.has(method)) continue;
    const responseSchemas = {};
    const responses = pathItem[method]?.responses ?? {};
    for (const status of Object.keys(responses).sort()) {
      if (!/^2\d\d$/.test(status)) continue;
      const schema = responses[status]?.content?.["application/json"]?.schema;
      if (schema) responseSchemas[status] = schema;
    }
    if (Object.keys(responseSchemas).length > 0) {
      successfulJsonResponseSchemas[`${method.toUpperCase()} ${path}`] = responseSchemas;
    }
  }
}

const referencedComponentNames = new Set();
function collectComponentReferences(value) {
  if (!value || typeof value !== "object") return;
  if (typeof value.$ref === "string") {
    const prefix = "#/components/schemas/";
    if (!value.$ref.startsWith(prefix)) {
      throw new Error(`Unsupported OpenAPI runtime response reference: ${value.$ref}`);
    }
    const componentName = decodeURIComponent(value.$ref.slice(prefix.length));
    if (!referencedComponentNames.has(componentName)) {
      const component = openapi.components?.schemas?.[componentName];
      if (!component) throw new Error(`Missing OpenAPI component schema ${componentName}.`);
      referencedComponentNames.add(componentName);
      collectComponentReferences(component);
    }
  }
  for (const child of Object.values(value)) collectComponentReferences(child);
}
collectComponentReferences(successfulJsonResponseSchemas);
const runtimeComponentSchemas = Object.fromEntries(
  [...referencedComponentNames]
    .sort()
    .map((componentName) => [componentName, openapi.components.schemas[componentName]]),
);
const successfulJsonOperations = Object.keys(successfulJsonResponseSchemas);
const successfulJsonResponseTypeEntries = Object.entries(successfulJsonResponseSchemas).map(
  ([operation, responses]) => {
    const separator = operation.indexOf(" ");
    const method = operation.slice(0, separator).toLowerCase();
    const path = operation.slice(separator + 1);
    const responseTypes = Object.keys(responses).map(
      (status) =>
        `paths[${JSON.stringify(path)}][${JSON.stringify(method)}]["responses"][${Number(status)}]["content"]["application/json"]`,
    );
    return `  ${JSON.stringify(operation)}: ${responseTypes.join(" | ")};`;
  },
);

const contents = `// This file is generated from FastAPI/Pydantic OpenAPI. Do not edit by hand.
import type { paths } from "./api.generated";

export const sourceTypes = ${JSON.stringify(sourceTypes, null, 2)} as const;

// synthetic_fixture is reserved for the committed server-owned acceptance corpus.
export const userIntakeSourceTypes = ${JSON.stringify(userIntakeSourceTypes, null, 2)} as const;

export const sourceAuthorities = ${JSON.stringify(sourceAuthorities, null, 2)} as const;

export const successfulJsonOperations = ${JSON.stringify(successfulJsonOperations, null, 2)} as const;
export type SuccessfulJsonOperation = (typeof successfulJsonOperations)[number];
export type SuccessfulJsonResponseByOperation = {
${successfulJsonResponseTypeEntries.join("\n")}
};

export const successfulJsonResponseSchemas: Record<
  SuccessfulJsonOperation,
  Record<string, unknown>
> = ${JSON.stringify(successfulJsonResponseSchemas, null, 2)};

export const runtimeComponentSchemas: Record<string, unknown> = ${JSON.stringify(runtimeComponentSchemas, null, 2)};
`;

writeFileSync(outputPath, contents, "utf8");
