import { EntitySchema } from "../../models";
import { EntityDependencyGraph } from "./types";

/**
 * Builds entity dependency graph from schema definitions.
 *
 * @param entities - Array of schema definitions
 * @returns Entity dependency graph showing cross-reference relationships
 */
export const buildDependencyGraph = (schemas: EntitySchema[]): EntityDependencyGraph => {
  const dependencies: Record<string, string[]> = {};

  for (const schema of schemas) {
    const entityDependencies: string[] = [];
    for (const attr of schema.attributes) {
      if (attr.rel_entity && !entityDependencies.includes(attr.rel_entity)) {
        entityDependencies.push(attr.rel_entity);
      }
    }
    dependencies[schema.schema_name] = entityDependencies;
  }

  return { dependencies };
};
