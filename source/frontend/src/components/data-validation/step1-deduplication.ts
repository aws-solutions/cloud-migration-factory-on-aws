import { EntityForValidation, DeduplicatedEntity, DeduplicationError } from "./types";

/**
 * Return type for the deduplicateEntities function.
 * Contains deduplicated entities and any conflicts found during the merge process.
 */
export interface DeduplicationResult {
  /** Entities after deduplication and merging, keyed by entity name */
  readonly deduplicatedEntities: Record<string, DeduplicatedEntity>;

  /** Warnings from conflicting attributes */
  readonly warnings: DeduplicationError[];
}

/**
 * Deduplicates entities by merging items with the same unique key.
 * When conflicts are found, creates warnings.
 *
 * @param entities - Array of entities with potentially duplicate data
 * @returns Object containing deduplicated entities, and warnings
 */
export const deduplicateEntities = (entities: EntityForValidation[]): DeduplicationResult => {
  // Initialize collections for tracking validation results
  const warnings: DeduplicationError[] = [];
  const deduplicatedEntities: Record<string, DeduplicatedEntity> = {};

  for (const entity of entities) {
    const mergedData: Record<string, Record<string, unknown>> = {};

    for (const [uniqueKey, items] of Object.entries(entity.data)) {
      mergedData[uniqueKey] = mergeItemsForUniqueKey(items, entity, uniqueKey, warnings);
    }

    deduplicatedEntities[entity.entityName] = {
      ...entity,
      data: mergedData,
    };
  }

  return { deduplicatedEntities, warnings };
};

/**
 * Handles deduplication for multi-value relationships by merging conflicting values.
 */
const handleMultivalueRelationshipDeduplication = (
  mergedItem: Record<string, unknown>,
  attrName: string,
  value: unknown
): void => {
  if (value === undefined || value === null) return;

  const existingValue = mergedItem[attrName];

  // Convert values to arrays, splitting semicolon-delimited strings
  const existingArray = Array.isArray(existingValue)
    ? existingValue
    : typeof existingValue === "string"
      ? existingValue
          .split(";")
          .map((v) => v.trim())
          .filter((v) => v !== "")
      : [existingValue];

  const newArray = Array.isArray(value)
    ? value
    : typeof value === "string"
      ? value
          .split(";")
          .map((v) => v.trim())
          .filter((v) => v !== "")
      : [value];

  // Merge arrays and remove duplicates
  const mergedArray = [...existingArray, ...newArray];
  const uniqueArray = [...new Set(mergedArray)];

  mergedItem[attrName] = uniqueArray;
};

/**
 * Merges all items with the same unique key, handling conflicts appropriately.
 */
const mergeItemsForUniqueKey = (
  items: Record<string, unknown>[],
  entity: EntityForValidation,
  uniqueKey: string,
  warnings: DeduplicationError[]
): Record<string, unknown> => {
  const mergedItem: Record<string, unknown> = {};

  for (const item of items) {
    for (const [attrName, value] of Object.entries(item)) {
      if (mergedItem[attrName] !== undefined && mergedItem[attrName] !== value) {
        const attribute = entity.schema.attributes.find((attr) => attr.name === attrName);
        if (!attribute) continue;

        const isMultiValueRelationship = attribute.rel_entity && attribute.type === "multivalue-relationship";

        if (isMultiValueRelationship) {
          handleMultivalueRelationshipDeduplication(mergedItem, attrName, value);
        } else {
          const conflictError: DeduplicationError = {
            entityName: entity.entityName,
            uniqueKey,
            attributeName: attrName,
            value: mergedItem[attrName],
            conflictingValues: [value],
            message: `Conflicting values for ${attribute.required ? "required" : "optional"} attribute '${attrName}': '${mergedItem[attrName]}' vs '${value}'`,
          };

          warnings.push(conflictError);
        }
      } else {
        mergedItem[attrName] = value;
      }
    }
  }

  return mergedItem;
};
