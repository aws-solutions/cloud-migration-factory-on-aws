/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { prioritizingRuleValidate, groupingRuleValidate } from "../../../vendor/validators.mjs";
import {
  EntitySchema,
  WPMGroupingRuleData,
  WPMPrioritizingRuleData,
  WPMRule,
  WPMRuleGenerationType,
  WPMRuleInDB,
} from "../../models";
import { UNEXPECTED_ERROR } from "../../resources/recordFunctions";

interface ErrorObject {
  keyword: string;
  instancePath: string;
  schemaPath: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  params: Record<string, any>;
  propertyName?: string;
  message?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  schema?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  parentSchema?: any;
  data?: unknown;
}

type ValidationContext = Readonly<{
  schemaNames: string[];
  schemas: Record<string, EntitySchema>;
}>;

type ValidationResult = Readonly<{
  errors?: ErrorObject[];
}>;

/**
 * Cast a string to `WPMRuleGenerationType` if possible otherwise fallback to the specified default value
 * @param param The string to be casted
 * @param defaultValue The default value
 * @returns result in {@link WPMRuleGenerationType} type
 */
export const castToRuleGenerationType = (
  param: string | null,
  defaultValue: WPMRuleGenerationType
): WPMRuleGenerationType => {
  if (param === null) return defaultValue;
  const paramUppercase = param.toUpperCase();
  if (paramUppercase === "PRIORITIZING") return "PRIORITIZING";
  else if (paramUppercase === "GROUPING") return "GROUPING";
  else return defaultValue;
};

const mapAjvErrorObjects = (errors: ErrorObject[] | null | undefined) => {
  const purgeAndJoin = (msgs: (string | undefined)[]) => msgs.filter((x) => !!x).join(": ");

  return (
    errors
      // Ignore conditional block level error messages
      ?.filter((error) => error.keyword !== "if")
      .map((error) => {
        const path = !error.instancePath
          ? ""
          : error.instancePath
              .replace(/^\//, "") // Remove leading slash
              .replace(/\/(\d+)\//g, "[$1].") // Convert numeric segments to array notation
              .replace(/\/(\d+)$/, "[$1]") // Handle numeric segment at the end
              .replace(/\//g, "."); // Convert remaining slashes to dots;

        if (["enum", "assetType", "assetKey"].includes(error.keyword)) {
          const { allowedValues } = error.params;
          return purgeAndJoin([path, `${error.message} [${allowedValues.join(", ")}]`]);
        }
        if (error.keyword === "additionalProperties") {
          const { additionalProperty } = error.params;
          return purgeAndJoin([path, `${error.message} '${additionalProperty}'`]);
        }
        return purgeAndJoin([path, error.message]);
      })
  );
};

export class RuleValidationError extends Error {
  constructor(public readonly errors: string[]) {
    super();
  }
}

// Supported built-in schemas
const SUPPORTED_SCHEMAS: ReadonlyArray<string> = ["app", "server", "database"];

/**
 * Validates a prioritizing rule and returns a properly typed PrioritizingRule object
 * @param parsedRule The rule to validate
 * @returns A validated PrioritizingRule object
 * @throws {RuleValidationError} When validation fails
 */
export const validatePrioritizingRule = (
  rule: unknown,
  schemas: Record<string, EntitySchema>
): WPMPrioritizingRuleData => {
  const customSchemaNames = Object.entries(schemas)
    .filter(([, schema]) => schema.schema_type === "custom")
    .map(([schemaName]) => schemaName);
  const schemaNames = [...SUPPORTED_SCHEMAS, ...customSchemaNames];
  const context: ValidationContext = { schemaNames, schemas };
  const valid = prioritizingRuleValidate.call(context, rule);
  // Type predicates not applied when called with fn.call https://github.com/microsoft/TypeScript/issues/57532
  if (valid) return rule as WPMPrioritizingRuleData;
  throw new RuleValidationError(
    mapAjvErrorObjects((prioritizingRuleValidate as ValidationResult).errors) ?? [UNEXPECTED_ERROR]
  );
};

/**
 * Validates a grouping rule against the JSON schema
 * @param rule The rule object to validate
 * @returns A validated GroupingRuleData object
 * @throws {RuleValidationError} When validation fails
 */
export const validateGroupingRule = (rule: unknown, schemas: Record<string, EntitySchema>): WPMGroupingRuleData => {
  const customSchemaNames = Object.entries(schemas)
    .filter(([, schema]) => schema.schema_type === "custom")
    .map(([schemaName]) => schemaName);
  const schemaNames = [...SUPPORTED_SCHEMAS, ...customSchemaNames];
  const context: ValidationContext = { schemaNames, schemas };
  const valid = groupingRuleValidate.call(context, rule);
  if (valid) return rule as WPMGroupingRuleData;
  throw new RuleValidationError(
    mapAjvErrorObjects((groupingRuleValidate as ValidationResult).errors) ?? [UNEXPECTED_ERROR]
  );
};

/**
 * Converts all numeric properties whose values stored as string in a rule to numbers
 * @param rule The rule to convert
 * @returns The converted rule
 */
export const convertNumericProperties = (rule: WPMRuleInDB): WPMRule => {
  const numericProperties = new Set(["sort_level", "lower_bound", "upper_bound", "complexity_score"]);
  // Given the small amount of rules and small size of rule JSON, the performance impact
  // of using JSON.parse would be negligible
  return rule.rule_type === "PRIORITIZING"
    ? JSON.parse(JSON.stringify(rule), (key, value) =>
        numericProperties.has(key) && typeof value === "string" ? +value : value
      )
    : rule;
};
