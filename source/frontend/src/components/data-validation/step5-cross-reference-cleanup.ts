import { DeduplicatedEntity, CrossReferenceError } from "./types";

/**
 * Return type for the validateCrossReferences function.
 */
export interface ValidateCrossReferencesResult {
  /** Entities after removing those with broken cross-references */
  readonly cleanedEntities: DeduplicatedEntity[];

  /** Cross-reference errors discovered during the cleanup phase */
  readonly crossReferenceErrors: CrossReferenceError[];
}

/**
 * Removes entities with broken cross-references based on provided error list.
 * Can be used after step4 (initial cleanup) and after step6 (backend validation cleanup).
 */
export const validateCrossReferences = (
  entities: DeduplicatedEntity[],
  crossReferenceErrors: CrossReferenceError[] = []
): ValidateCrossReferencesResult => {
  if (crossReferenceErrors.length === 0) {
    return { cleanedEntities: entities, crossReferenceErrors: [] };
  }

  // Create set of items to remove based on cross-reference errors
  const itemsToRemove = new Set<string>();
  crossReferenceErrors.forEach((error) => {
    itemsToRemove.add(`${error.entityName}:${error.uniqueKey}`);
  });

  // Remove entities with broken cross-references
  const cleanedEntities = entities.map((entity) => {
    const cleanedData: Record<string, Record<string, unknown>> = {};

    for (const [uniqueKey, item] of Object.entries(entity.data)) {
      const itemKey = `${entity.entityName}:${uniqueKey}`;
      if (!itemsToRemove.has(itemKey)) {
        cleanedData[uniqueKey] = item;
      }
    }

    return {
      ...entity,
      data: cleanedData,
    };
  });

  return { cleanedEntities, crossReferenceErrors };
};
