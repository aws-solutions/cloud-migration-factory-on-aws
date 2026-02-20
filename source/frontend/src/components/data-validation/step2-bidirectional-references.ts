import { DeduplicatedEntity, ValidationError } from "./types";

/**
 * Return type for the createBidirectionalReferences function.
 */
export interface BidirectionalReferenceResult {
  /** Entities with bidirectional cross-references added */
  readonly entities: Record<string, DeduplicatedEntity>;

  /** Errors from conflicting single-value cross-references */
  readonly errors: ValidationError[];
}

/**
 * Normalizes entity names for cross-reference lookups.
 */
const normalizeEntityName = (entityName: string): string => {
  return entityName === "app" ? "application" : entityName;
};

/**
 * Creates bidirectional cross-references between entities.
 * If entity A references entity B, and B has a cross-reference attribute to A's type,
 * automatically populate B's reference to A.
 */
export const createBidirectionalReferences = (
  deduplicatedEntities: Record<string, DeduplicatedEntity>
): BidirectionalReferenceResult => {
  const errors: ValidationError[] = [];

  // Iterate through all entities to find cross-references
  for (const [entityName, entity] of Object.entries(deduplicatedEntities)) {
    // Process each item within the entity
    for (const [uniqueKey, item] of Object.entries(entity.data)) {
      // Check each attribute for cross-references
      for (const attribute of entity.schema.attributes) {
        // Skip if not a cross-reference or no value present
        if (!attribute.rel_entity || !item[attribute.name]) continue;

        // Find the related entity being referenced
        const normalizedRelEntity = normalizeEntityName(attribute.rel_entity);
        const relatedEntity = deduplicatedEntities[normalizedRelEntity];
        if (!relatedEntity) continue;

        // Look for reverse reference attribute in the related entity's schema
        const reverseAttr = relatedEntity.schema.attributes.find(
          (attr) => attr.rel_entity && normalizeEntityName(attr.rel_entity) === entityName
        );
        if (!reverseAttr) continue; // No reverse reference attribute found

        // Handle both single values and arrays of references
        const referencedKeys = Array.isArray(item[attribute.name])
          ? (item[attribute.name] as unknown[])
          : [item[attribute.name]];

        // Process each referenced key
        for (const refKey of referencedKeys) {
          const relatedItem = relatedEntity.data[String(refKey)];
          if (!relatedItem) continue; // Referenced item doesn't exist

          const currentValue = relatedItem[reverseAttr.name];
          // Check if the reverse attribute supports multiple values
          const isMultiValue = Boolean(reverseAttr.listMultiSelect) ?? false;

          if (isMultiValue) {
            // For multi-value attributes, add to array if not already present
            const currentArray = Array.isArray(currentValue) ? currentValue : currentValue ? [currentValue] : [];
            if (!currentArray.includes(uniqueKey)) {
              currentArray.push(uniqueKey);
              relatedItem[reverseAttr.name] = currentArray;
            }
          } else {
            // For single-value attributes, check for conflicts
            if (currentValue && currentValue !== uniqueKey) {
              // Conflict: attribute already has a different value
              errors.push({
                entityName: normalizedRelEntity,
                uniqueKey: String(refKey),
                attributeName: reverseAttr.name,
                value: currentValue,
                message: `Cannot create bidirectional reference: attribute '${reverseAttr.name}' already has value '${currentValue}', cannot set to '${uniqueKey}'`,
              });
            } else if (!currentValue) {
              // No existing value, safe to set the reverse reference
              relatedItem[reverseAttr.name] = uniqueKey;
            }
            // If currentValue === uniqueKey, bidirectional reference already exists
          }
        }
      }
    }
  }

  return { entities: deduplicatedEntities, errors };
};
