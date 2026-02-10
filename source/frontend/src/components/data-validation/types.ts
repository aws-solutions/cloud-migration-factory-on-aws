import { EntitySchema } from "../../models";

/**
 * Base interface for entities containing common properties.
 */
interface BaseEntity {
  /** The name of the entity type (e.g., 'application', 'server') */
  readonly entityName: string;

  /** The schema definition containing attribute specifications */
  readonly schema: EntitySchema;
}

/**
 * Represents an entity with its schema and raw data before validation.
 * Contains potentially duplicate items that need to be processed.
 */
export interface EntityForValidation extends BaseEntity {
  /**
   * Raw data map where keys are unique identifiers and values are arrays of items.
   * Multiple items per key indicate duplicates from different sources (e.g., spreadsheets).
   */
  readonly data: Record<string, Record<string, unknown>[]>;
}

/**
 * Represents an entity after deduplication with merged data.
 * Each unique key now maps to a single consolidated record.
 */
export interface DeduplicatedEntity extends BaseEntity {
  /**
   * Deduplicated data map where each unique key maps to a single merged record.
   */
  readonly data: Record<string, Record<string, unknown>>;
}

/**
 * Base interface for validation errors containing common properties.
 */
interface BaseValidationError {
  /** The entity type where the error occurred */
  readonly entityName: string;

  /** The unique identifier of the entity with the error */
  readonly uniqueKey: string;

  /** The name of the attribute that failed validation */
  readonly attributeName: string;

  /** The actual value that failed validation */
  readonly value: unknown;

  /** Descriptive error message explaining the validation failure */
  readonly message: string;
}

/**
 * Represents a conflict found during deduplication when merging duplicate entities.
 */
export interface DeduplicationError extends BaseValidationError {
  /** Array of conflicting values found in other duplicate items */
  readonly conflictingValues: unknown[];
}

/**
 * Represents an error for missing or invalid required attributes.
 */
export type RequiredAttributeError = BaseValidationError;

/**
 * Represents validation errors from type checking and regex pattern validation.
 */
export type ValidationError = BaseValidationError;

/**
 * Represents an error for broken cross-references between entities.
 * Generated when an entity references another entity that doesn't exist or was removed.
 */
export interface CrossReferenceError extends BaseValidationError {
  /** The name of the cross-reference attribute (same as attributeName) */
  readonly crossReferenceAttributeName: string;

  /** The name of the entity type being referenced */
  readonly crossRefencedEntityName: string;
}

/**
 * Comprehensive validation results containing all types of validation issues.
 */
export interface ValidationIssues {
  /** Errors from conflicting values in required attributes during deduplication */
  readonly deduplicationErrors: DeduplicationError[];

  /** Warnings from conflicting values in optional attributes during deduplication */
  readonly deduplicationWarnings: DeduplicationError[];

  /** Errors from missing or invalid required attributes */
  readonly requiredAttributeErrors: RequiredAttributeError[];

  /** Errors from type validation and regex validation failures */
  readonly validationErrors: ValidationError[];

  /** Warnings from type validation and regex validation failures */
  readonly validationWarnings: ValidationError[];

  /** Errors for cross reference failures */
  readonly crossReferenceErrors: CrossReferenceError[];
}

/**
 * Represents the dependency graph showing which entity types reference other entity types.
 */
export interface EntityDependencyGraph {
  /** Map of entity type to set of entity types it references */
  readonly dependencies: Record<string, string[]>;
}

/**
 * Represents an entity that needs bidirectional relationship updates in the backend.
 */
export interface EntityToUpdate {
  /** The entity type name */
  readonly entityName: string;

  /** The unique identifier of the entity */
  readonly uniqueKey: string;

  /** The attribute name that contains the cross-reference */
  readonly attributeName: string;

  /** The referenced entity type */
  readonly referencedEntityType: string;

  /** The referenced entity key(s) */
  readonly referencedEntityKeys: string[];
}

/**
 * Nested structure for bidirectional relationship updates.
 * Format: { entityType: { entityKey: { referencedEntityType: [referencedKeys] } } }
 */
export type BidirectionalUpdates = Record<string, Record<string, Record<string, string[]>>>;

/**
 * Represents a backend validation request for cross-reference checking.
 */
export interface BackendValidationRequest {
  /** The entity type to validate against */
  readonly entityType: string;

  /** Set of reference keys to validate */
  readonly references: Set<string>;

  /** Validation items that need to be checked */
  readonly validationItems: Array<{
    entityName: string;
    uniqueKey: string;
    attributeName: string;
    referencedKeys: string[];
  }>;
}

/**
 * Return type for the main validateData function containing final results.
 */
export interface DataValidationResult {
  /** Final validated and processed entities with applied defaults and validation */
  readonly entities: DeduplicatedEntity[];

  /** Comprehensive validation results including all error types */
  readonly issues: ValidationIssues;

  /** Entity dependency graph showing cross-reference relationships */
  readonly dependencyGraph: EntityDependencyGraph;

  /** Entities that need bidirectional relationship updates in the backend using nested structure */
  readonly entitiesToUpdate: BidirectionalUpdates;

  /** Backend validation requests to be processed by main thread */
  readonly backendValidationRequests: BackendValidationRequest[];
}
