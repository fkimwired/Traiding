import {
  runtimeComponentSchemas,
  successfulJsonResponseSchemas,
  type SuccessfulJsonOperation,
} from "./runtime.generated";

type JsonSchema = Record<string, unknown>;

const PYDANTIC_DECIMAL_FIXED_PATTERN = String.raw`^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$`;
const FINITE_DECIMAL_STRING_PATTERN =
  /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/u;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function schemaRecord(value: unknown): JsonSchema | undefined {
  return isRecord(value) ? value : undefined;
}

function schemaList(value: unknown): JsonSchema[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const schemas = value.map(schemaRecord);
  return schemas.every((schema): schema is JsonSchema => Boolean(schema)) ? schemas : undefined;
}

function numberConstraint(schema: JsonSchema, name: string) {
  const value = schema[name];
  return typeof value === "number" ? value : undefined;
}

function isValidCalendarDate(year: number, month: number, day: number) {
  if (month < 1 || month > 12 || day < 1) return false;
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= daysInMonth[month - 1];
}

function matchesDate(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  return Boolean(
    match &&
      isValidCalendarDate(Number(match[1]), Number(match[2]), Number(match[3])),
  );
}

function matchesTime(value: string, timezoneRequired: boolean) {
  const match = /^(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-](\d{2}):(\d{2}))?$/.exec(value);
  if (!match || (timezoneRequired && !match[4])) return false;
  if (Number(match[1]) > 23 || Number(match[2]) > 59 || Number(match[3]) > 59) {
    return false;
  }
  return !match[4] || match[4] === "Z" || (Number(match[5]) <= 23 && Number(match[6]) <= 59);
}

function matchesFormat(format: unknown, value: string) {
  if (format === "uuid") {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  }
  if (format === "date-time") {
    const separator = value.indexOf("T");
    return (
      separator === 10 &&
      matchesDate(value.slice(0, separator)) &&
      matchesTime(value.slice(separator + 1), true)
    );
  }
  if (format === "date") return matchesDate(value);
  if (format === "time") return matchesTime(value, false);
  return true;
}

/** @internal Exported only for focused compatibility regression tests. */
export function matchesOpenApiStringPattern(pattern: string, value: string) {
  if (new RegExp(pattern, "u").test(value)) return true;

  // Pydantic serializes finite Decimal values as strings and may choose exponent
  // notation, while its generated fixed-notation pattern does not describe that
  // valid wire form. Keep this exception bound to that exact generated pattern.
  return (
    pattern === PYDANTIC_DECIMAL_FIXED_PATTERN &&
    FINITE_DECIMAL_STRING_PATTERN.test(value)
  );
}

function matchesDeclaredType(type: string, value: unknown) {
  if (type === "null") return value === null;
  if (type === "array") return Array.isArray(value);
  if (type === "object") return isRecord(value);
  if (type === "string") return typeof value === "string";
  if (type === "boolean") return typeof value === "boolean";
  if (type === "integer") return typeof value === "number" && Number.isInteger(value);
  if (type === "number") return typeof value === "number" && Number.isFinite(value);
  return false;
}

function sameJsonValue(left: unknown, right: unknown) {
  if (
    left === null ||
    right === null ||
    typeof left !== "object" ||
    typeof right !== "object"
  ) {
    return Object.is(left, right);
  }
  return JSON.stringify(left) === JSON.stringify(right);
}

function resolveReference(reference: string) {
  const prefix = "#/components/schemas/";
  if (!reference.startsWith(prefix)) return undefined;
  return schemaRecord(runtimeComponentSchemas[decodeURIComponent(reference.slice(prefix.length))]);
}

function matchesSchema(schema: JsonSchema, value: unknown, depth = 0): boolean {
  if (depth > 256) return false;

  if (typeof schema.$ref === "string") {
    const referenced = resolveReference(schema.$ref);
    return referenced ? matchesSchema(referenced, value, depth + 1) : false;
  }

  const allOf = schemaList(schema.allOf);
  if (allOf && !allOf.every((candidate) => matchesSchema(candidate, value, depth + 1))) {
    return false;
  }
  const anyOf = schemaList(schema.anyOf);
  if (anyOf && !anyOf.some((candidate) => matchesSchema(candidate, value, depth + 1))) {
    return false;
  }
  const oneOf = schemaList(schema.oneOf);
  if (
    oneOf &&
    oneOf.filter((candidate) => matchesSchema(candidate, value, depth + 1)).length !== 1
  ) {
    return false;
  }
  const disallowed = schemaRecord(schema.not);
  if (disallowed && matchesSchema(disallowed, value, depth + 1)) return false;

  if (Array.isArray(schema.enum) && !schema.enum.some((item) => sameJsonValue(item, value))) {
    return false;
  }
  if ("const" in schema && !sameJsonValue(schema.const, value)) return false;
  if (value === null && schema.nullable === true) return true;

  const declaredTypes =
    typeof schema.type === "string"
      ? [schema.type]
      : Array.isArray(schema.type) && schema.type.every((item) => typeof item === "string")
        ? schema.type
        : [];
  if (
    declaredTypes.length > 0 &&
    !declaredTypes.some((type) => matchesDeclaredType(type, value))
  ) {
    return false;
  }

  if (typeof value === "string") {
    const minimumLength = numberConstraint(schema, "minLength");
    const maximumLength = numberConstraint(schema, "maxLength");
    const codePointLength = Array.from(value).length;
    if (minimumLength !== undefined && codePointLength < minimumLength) return false;
    if (maximumLength !== undefined && codePointLength > maximumLength) return false;
    if (
      typeof schema.pattern === "string" &&
      !matchesOpenApiStringPattern(schema.pattern, value)
    ) {
      return false;
    }
    if (!matchesFormat(schema.format, value)) return false;
  }

  if (typeof value === "number") {
    const minimum = numberConstraint(schema, "minimum");
    const maximum = numberConstraint(schema, "maximum");
    const exclusiveMinimum = numberConstraint(schema, "exclusiveMinimum");
    const exclusiveMaximum = numberConstraint(schema, "exclusiveMaximum");
    if (minimum !== undefined && value < minimum) return false;
    if (maximum !== undefined && value > maximum) return false;
    if (exclusiveMinimum !== undefined && value <= exclusiveMinimum) return false;
    if (exclusiveMaximum !== undefined && value >= exclusiveMaximum) return false;
  }

  if (Array.isArray(value)) {
    const minimumItems = numberConstraint(schema, "minItems");
    const maximumItems = numberConstraint(schema, "maxItems");
    if (minimumItems !== undefined && value.length < minimumItems) return false;
    if (maximumItems !== undefined && value.length > maximumItems) return false;
    if (schema.uniqueItems === true) {
      for (let index = 0; index < value.length; index += 1) {
        if (value.slice(index + 1).some((item) => sameJsonValue(item, value[index]))) {
          return false;
        }
      }
    }
    const prefixItems = schemaList(schema.prefixItems) ?? [];
    for (let index = 0; index < prefixItems.length && index < value.length; index += 1) {
      if (!matchesSchema(prefixItems[index], value[index], depth + 1)) return false;
    }
    if (schema.items === false && value.length > prefixItems.length) return false;
    const itemSchema = schemaRecord(schema.items);
    if (
      itemSchema &&
      value
        .slice(prefixItems.length)
        .some((item) => !matchesSchema(itemSchema, item, depth + 1))
    ) {
      return false;
    }
  }

  if (isRecord(value)) {
    const required = Array.isArray(schema.required)
      ? schema.required.filter((name): name is string => typeof name === "string")
      : [];
    if (required.some((name) => !Object.hasOwn(value, name))) return false;
    const properties = schemaRecord(schema.properties) ?? {};
    for (const [name, propertySchemaValue] of Object.entries(properties)) {
      if (!Object.hasOwn(value, name)) continue;
      const propertySchema = schemaRecord(propertySchemaValue);
      if (!propertySchema || !matchesSchema(propertySchema, value[name], depth + 1)) return false;
    }
    const additionalPropertyNames = Object.keys(value).filter(
      (name) => !Object.hasOwn(properties, name),
    );
    if (schema.additionalProperties === false && additionalPropertyNames.length > 0) return false;
    const additionalProperties = schemaRecord(schema.additionalProperties);
    if (
      additionalProperties &&
      additionalPropertyNames.some(
        (name) => !matchesSchema(additionalProperties, value[name], depth + 1),
      )
    ) {
      return false;
    }
  }

  return true;
}

export function validateOpenApiResponse(
  operation: SuccessfulJsonOperation,
  status: number,
  value: unknown,
) {
  const schema = schemaRecord(successfulJsonResponseSchemas[operation][String(status)]);
  return schema ? matchesSchema(schema, value) : false;
}

export type { SuccessfulJsonOperation };
