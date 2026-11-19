import { BackendValidationRequest, CrossReferenceError, BidirectionalUpdates, DeduplicatedEntity } from "./types";
import { validateCrossReferences } from "./step5-cross-reference-cleanup";

/**
 * Internal function for backend validation requests.
 */
const processBackendValidationInternal = async (
  backendValidationRequests: BackendValidationRequest[],
  existingItemsBySchema: Map<string, Record<string, unknown>[]>
): Promise<{
  crossReferenceErrors: CrossReferenceError[];
  entitiesToUpdate: BidirectionalUpdates;
}> => {
  const crossReferenceErrors: CrossReferenceError[] = [];
  const entitiesToUpdate: BidirectionalUpdates = {};

  for (const request of backendValidationRequests) {
    const references = Array.from(request.references);
    let validReferences: Set<string>;

    try {
      const apiEntityType = request.entityType === "application" ? "app" : request.entityType;
      const allItems = existingItemsBySchema.get(apiEntityType) || [];
      const itemDict = new Set(
        allItems
          .map((item: Record<string, unknown>) => {
            const nameField = request.entityType === "application" ? "app_name" : `${request.entityType}_name`;
            return item[nameField];
          })
          .filter(Boolean)
      );

      validReferences = new Set(references.filter((ref) => itemDict.has(ref)));
    } catch (error) {
      console.log(error);
      validReferences = new Set();
    }

    for (const validationItem of request.validationItems) {
      const validRefs = validationItem.referencedKeys.filter((ref) => validReferences.has(ref));
      const invalidRefs = validationItem.referencedKeys.filter((ref) => !validReferences.has(ref));

      for (const ref of invalidRefs) {
        crossReferenceErrors.push({
          entityName: validationItem.entityName,
          uniqueKey: validationItem.uniqueKey,
          attributeName: validationItem.attributeName,
          value: ref,
          crossReferenceAttributeName: validationItem.attributeName,
          crossRefencedEntityName: request.entityType,
          message: `${request.entityType} with unique key ${ref} does not exist`,
        });
      }

      if (validRefs.length > 0) {
        // Create nested format
        for (const validRef of validRefs) {
          const entityType = request.entityType;

          if (!entitiesToUpdate[entityType]) {
            entitiesToUpdate[entityType] = {};
          }
          if (!entitiesToUpdate[entityType][validRef]) {
            entitiesToUpdate[entityType][validRef] = {};
          }
          if (!entitiesToUpdate[entityType][validRef][validationItem.entityName]) {
            entitiesToUpdate[entityType][validRef][validationItem.entityName] = [];
          }
          if (!entitiesToUpdate[entityType][validRef][validationItem.entityName].includes(validationItem.uniqueKey)) {
            entitiesToUpdate[entityType][validRef][validationItem.entityName].push(validationItem.uniqueKey);
          }
        }
      }
    }
  }

  return { crossReferenceErrors, entitiesToUpdate };
};

/**
 * Processes backend validation and performs post-validation cross-reference cleanup.
 */
export const processBackendValidation = async (
  entities: DeduplicatedEntity[],
  backendValidationRequests: BackendValidationRequest[],
  existingItemsBySchema: Map<string, Record<string, unknown>[]>
): Promise<{
  cleanedEntities: DeduplicatedEntity[];
  crossReferenceErrors: CrossReferenceError[];
  entitiesToUpdate: BidirectionalUpdates;
}> => {
  const { crossReferenceErrors, entitiesToUpdate } = await processBackendValidationInternal(
    backendValidationRequests,
    existingItemsBySchema
  );
  const { cleanedEntities } = validateCrossReferences(entities, crossReferenceErrors);

  return { cleanedEntities, crossReferenceErrors, entitiesToUpdate };
};
