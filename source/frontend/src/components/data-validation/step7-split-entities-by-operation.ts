import { DeduplicatedEntity } from "./types";

/**
 * Splits entities into 2 categories (Create and Update) by checking for their existence in backend
 */
export const splitEntitiesByOperation = (
  entities: DeduplicatedEntity[],
  existingItemsBySchema: Map<string, Record<string, unknown>[]>
): {
  entitiesToCreate: DeduplicatedEntity[];
  entitiesToUpdate: DeduplicatedEntity[];
} => {
  const entitiesToCreate: DeduplicatedEntity[] = [];
  const entitiesToUpdate: DeduplicatedEntity[] = [];

  const entitiesByType = new Map<string, DeduplicatedEntity[]>();

  for (const entity of entities) {
    const entityType = entity.entityName;
    if (!entitiesByType.has(entityType)) {
      entitiesByType.set(entityType, []);
    }
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    entitiesByType.get(entityType)!.push(entity);
  }

  for (const [entityName, entitiesList] of entitiesByType.entries()) {
    const apiEntityType = entityName === "application" ? "app" : entityName;
    const nameField = `${apiEntityType}_name`;
    const allItems = existingItemsBySchema.get(apiEntityType) || [];

    // Create the lookup set once per entity type for efficiency
    const existingItemNames = new Set(allItems.map((item: Record<string, unknown>) => item[nameField]).filter(Boolean));

    for (const entity of entitiesList) {
      try {
        // Create separate entities for items that exist vs don't exist in backend
        const existingItems: Record<string, Record<string, unknown>> = {};
        const newItems: Record<string, Record<string, unknown>> = {};

        for (const [entityKey, entityValue] of Object.entries(entity.data)) {
          if (existingItemNames.has(entityKey)) {
            existingItems[entityKey] = entityValue;
          } else {
            newItems[entityKey] = entityValue;
          }
        }

        // Create entity for items that need to be updated
        if (Object.keys(existingItems).length > 0) {
          entitiesToUpdate.push({
            entityName: entity.entityName,
            schema: entity.schema,
            data: existingItems,
          });
        }

        // Create entity for items that need to be created
        if (Object.keys(newItems).length > 0) {
          entitiesToCreate.push({
            entityName: entity.entityName,
            schema: entity.schema,
            data: newItems,
          });
        }
      } catch (error) {
        console.error(`Error processing entity ${entity.entityName}:`, error);
        // Default to create operation if there's an error
        entitiesToCreate.push(entity);
      }
    }
  }

  return {
    entitiesToCreate,
    entitiesToUpdate,
  };
};
