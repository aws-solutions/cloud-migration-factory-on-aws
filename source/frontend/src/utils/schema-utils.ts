/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { EntityName, EntitySchema } from "../models";
import { Schemas } from "./Constants";

/**
 * Normalizes an object against a schema by validating required attributes and removing attributes not in the schema,
 * e.g. those fields added by `resolveRelationshipValues` util function.
 * The id attribute is excluded from the required attributes check.
 * @param o - The object to normalize
 * @param schema - The entity schema to validate against
 * @param options - Configuration options for normalization
 * @param options.removeName - Whether to remove the `<entity>_name` from the normalized object. This is a workaround for a known
 * problem that the PUT API does not accept `<entity>_name` attribute with the same name. Defaults to false.
 * @param options.checkMissingRequiredAttributes - Whether to validate that all required attributes are present. Defaults to true.
 * @returns A new object with all defined values from the original
 * @throws Error if any required attributes are missing and checkMissingRequiredAttributes is true
 */
export function normalize<T extends Record<string, unknown>>(
  o: Record<string, unknown>,
  schema: EntitySchema,
  options: {
    removeName?: boolean;
    checkMissingRequiredAttributes?: boolean;
  } = { removeName: false, checkMissingRequiredAttributes: true }
): T {
  const attributeId = `${schema.schema_name}_id`;
  const attributeName = `${schema.schema_name}_name`;
  if (options.checkMissingRequiredAttributes) {
    const missingRequiredAttributes = schema.attributes.filter(
      (attribute) =>
        attribute.required &&
        attribute.name !== attributeId &&
        (Array.isArray(o[attribute.name])
          ? (o[attribute.name] as unknown[]).length === 0
          : o[attribute.name] === null || o[attribute.name] === undefined)
    );
    if (missingRequiredAttributes.length) {
      throw new Error(
        `Object ${JSON.stringify(o)} missing required attributes: ${missingRequiredAttributes.map((a) => a.name).join(", ")}`
      );
    }
  }

  const t = o as T;
  const allowedAttributes = options.removeName
    ? schema.attributes.filter((a) => a.name !== attributeName)
    : schema.attributes;
  return Object.entries(t).reduce<T>((acc, [key, value]) => {
    const attribute = allowedAttributes.find((att) => att.name === key);
    // Remove id attribute
    return attribute && attribute.name !== attributeId
      ? {
          ...acc,
          [key]: value,
        }
      : acc;
  }, {} as T);
}

/**
 * Returns true if the schema is a custom schema, false otherwise.
 * @param schema - The schema to check
 * @returns True if the schema is a custom schema, false otherwise
 */
export const isCustomSchema = (schema: EntitySchema): boolean => schema.schema_type === "custom";

/* Filters and simplifies schemas by removing attributes that are auto-generated
 * or not relevant for data import/mapping processes.
 *
 * @param remoteSchemas - The original schemas from the backend
 * @returns Filtered schemas with irrelevant attributes removed
 */
export const mappableEntitySchemas = (
  schemas: Readonly<Record<string, EntitySchema>>
): Record<string, EntitySchema> => {
  const builtInMappableEntities: Readonly<Partial<Record<EntityName, Partial<EntitySchema>>>> = {
    [Schemas.Application.name]: { friendly_name: Schemas.Application.friendlyName },
    [Schemas.Server.name]: { friendly_name: Schemas.Server.friendlyName },
    [Schemas.Database.name]: { friendly_name: Schemas.Database.friendlyName },
  };

  const globalUnmappableAttributeNames: ReadonlyArray<string> = [
    "move_group_id",
    "move_group_ids",
    "wave_id",
    "wave_ids",
    "wpm_job_id",
    "wpm_job_ids",
  ];

  const entityUnmappableAttributeNames: Readonly<Record<string, ReadonlyArray<string>>> = {
    application: ["rank", "complexity_score", "planning_status"],
  };

  return Object.entries(schemas).reduce<Record<string, EntitySchema>>((acc, [key, schema]) => {
    const builtInMappable = builtInMappableEntities[key as EntityName];
    if (builtInMappable || isCustomSchema(schema)) {
      acc[key] = {
        ...schema,
        ...builtInMappable,
        attributes: schema.attributes.filter(
          (attribute) =>
            !attribute.hidden &&
            !globalUnmappableAttributeNames.includes(attribute.name) &&
            !entityUnmappableAttributeNames[key as EntityName]?.includes(attribute.name)
        ),
      };
    }
    return acc;
  }, {});
};
