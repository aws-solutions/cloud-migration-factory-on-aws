import { EntityForValidation, DataValidationResult } from "./types";
import { deduplicateEntities } from "./step1-deduplication";
import { createBidirectionalReferences } from "./step2-bidirectional-references";
import { buildDependencyGraph } from "./step3-dependency-graph";
import { validateAttributes } from "./step4-attribute-validation";
import { validateCrossReferences } from "./step5-cross-reference-cleanup";

/**
 * Main validation function that processes entities through deduplication, attribute validation,
 * type checking, and regex validation to produce clean, validated data.
 *
 * @param entities - Raw entities with potential duplicates and validation issues
 * @returns Object containing validated entities and comprehensive validation results including all error types
 */
export const validateData = (entities: EntityForValidation[]): DataValidationResult => {
  // Step 1: Deduplicate entities and identify conflicts
  // Merges duplicate items and creates errors/warnings for conflicting values
  const { deduplicatedEntities, warnings: dedupWarnings } = deduplicateEntities(entities);

  // Step 2: Create bidirectional cross-references
  // Automatically populate reverse references when entities reference each other
  const { errors: bidirectionalErrors } = createBidirectionalReferences(deduplicatedEntities);

  // Step 3: Build entity dependency graph
  // Analyzes schema definitions to create cross-reference relationship map
  const dependencyGraph = buildDependencyGraph(entities.map((entity) => entity.schema));

  // Step 4: Validate attributes and apply business rules
  // Applies defaults, validates required fields, type checking, regex validation, and checks cross-references
  const {
    validatedEntities,
    errors: attrErrors,
    validationErrors,
    validationWarnings,
    crossReferenceErrors,
    backendValidationRequests,
  } = validateAttributes(deduplicatedEntities);

  // Step 5: Initial cross-reference cleanup (no errors to clean up yet)
  // This step is now mainly a placeholder for consistency
  const { cleanedEntities } = validateCrossReferences(validatedEntities);

  // Step 6: Compile and return comprehensive results
  // Cross-reference cleanup will be done after backend validation with actual errors
  return {
    entities: cleanedEntities,
    issues: {
      deduplicationErrors: [],
      deduplicationWarnings: dedupWarnings,
      requiredAttributeErrors: attrErrors,
      validationErrors: [...validationErrors, ...bidirectionalErrors],
      validationWarnings,
      crossReferenceErrors,
    },
    dependencyGraph,
    entitiesToUpdate: {}, // Will be populated by backend validation
    backendValidationRequests,
  };
};

// Re-export types for convenience
export type {
  EntityForValidation,
  DataValidationResult,
  EntityDependencyGraph,
  DeduplicatedEntity,
  CrossReferenceError,
  DeduplicationError,
  RequiredAttributeError,
  ValidationError,
  ValidationIssues,
  EntityToUpdate,
} from "./types";

export { processBackendValidation } from "./step6-backend-validation";
export { validateCrossReferences } from "./step5-cross-reference-cleanup";
export { splitEntitiesByOperation } from "./step7-split-entities-by-operation";
