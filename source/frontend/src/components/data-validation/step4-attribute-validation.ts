import { Attribute, EntitySchema } from "../../models";
import { DeduplicatedEntity, RequiredAttributeError, ValidationError, CrossReferenceError } from "./types";
// UserApiClient cannot be used in Web Worker context

/**
 * Return type for the validateAttributes function containing comprehensive validation results.
 * Includes validated entities and all types of validation errors and warnings.
 */
export interface AttributeValidationResult {
  /** Entities after attribute validation, default value application, and type/regex validation */
  readonly validatedEntities: DeduplicatedEntity[];

  /** Errors from missing required attributes or failed cross-reference validations */
  readonly errors: RequiredAttributeError[];

  /** Errors from type checking and regex pattern validation failures */
  readonly validationErrors: ValidationError[];

  /** Warnings from type validation and regex validation failures */
  readonly validationWarnings: ValidationError[];

  /** Errors for cross reference failures */
  readonly crossReferenceErrors: CrossReferenceError[];

  /** Backend validation requests to be processed by main thread */
  readonly backendValidationRequests: BackendValidationRequest[];
}

interface BackendValidationRequest {
  entityType: string;
  references: Set<string>;
  validationItems: Array<{
    entityName: string;
    uniqueKey: string;
    attributeName: string;
    referencedKeys: string[];
  }>;
}

/**
 * Validates that a value matches the expected data type from the schema.
 * Accepts both native types and string representations (e.g., "25" for number, "true" for boolean).
 */
const validateType = (value: unknown, expectedType: string): boolean => {
  if (value === null || value === undefined) return true;

  const stringValue = String(value);

  switch (expectedType.toLowerCase()) {
    case "string":
      return true;
    case "number":
      if (typeof value === "number" && !isNaN(value)) return true;
      if (typeof value === "string") {
        const num = Number(stringValue);
        return !isNaN(num) && isFinite(num);
      }
      return false;
    case "boolean":
    case "checkbox":
      if (typeof value === "boolean") return true;
      if (typeof value === "string") {
        return stringValue.toLowerCase() === "true" || stringValue.toLowerCase() === "false";
      }
      return false;
    case "date":
      if (value instanceof Date) return !isNaN(value.getTime());
      if (typeof value === "string") {
        const date = new Date(stringValue);
        return !isNaN(date.getTime());
      }
      return false;
    case "json":
      if (typeof value === "object" && !Array.isArray(value)) return true;
      if (typeof value === "string") {
        try {
          JSON.parse(value);
          return true;
        } catch {
          return false;
        }
      }
      return false;
    case "object":
      return typeof value === "object" && !Array.isArray(value);
    case "list":
    case "tag":
    case "relationship":
    case "embedded_entity":
    case "policy":
    case "policies":
    case "groups":
    case "status":
    case "multivalue-string":
    case "array":
      return true;
    default:
      return true;
  }
};

/**
 * Validates that a value matches the specified regex pattern.
 */
const validateRegex = (value: unknown, pattern: string): boolean => {
  if (value === null || value === undefined) return true;
  try {
    const regex = new RegExp(pattern);
    return regex.test(String(value));
  } catch {
    return false;
  }
};

/**
 * Validates that a value matches one of the allowed values from a list attribute.
 */
const validateListValue = (
  value: unknown,
  listValues: string,
  isMultiSelect?: boolean
): { isValid: boolean; invalidValues: string[] } => {
  if (value === null || value === undefined || value === "") {
    return { isValid: true, invalidValues: [] };
  }

  const allowedValues = listValues.split(",").map((val) => val.trim().toLowerCase());
  const invalidValues: string[] = [];

  if (isMultiSelect && Array.isArray(value)) {
    for (const item of value) {
      const itemStr = String(item).toLowerCase();
      if (!allowedValues.includes(itemStr)) {
        invalidValues.push(String(item));
      }
    }
  } else {
    const valueStr = String(value).toLowerCase();
    if (!allowedValues.includes(valueStr)) {
      invalidValues.push(String(value));
    }
  }

  return {
    isValid: invalidValues.length === 0,
    invalidValues,
  };
};

/**
 * Normalizes entity names for cross-reference lookups.
 */
const normalizeEntityName = (entityName: string): string => {
  return entityName === "app" ? "application" : entityName;
};

/**
 * Checks for fields in the item that are not defined in the schema.
 */
const checkExtraFields = (
  item: Record<string, unknown>,
  schemaAttributeNames: Set<string>,
  entityName: string,
  uniqueKey: string,
  validationWarnings: ValidationError[]
): void => {
  for (const [fieldName, fieldValue] of Object.entries(item)) {
    if (!schemaAttributeNames.has(fieldName)) {
      validationWarnings.push({
        entityName,
        uniqueKey,
        attributeName: fieldName,
        value: fieldValue,
        message: `Field '${fieldName}' is not defined in the schema`,
      });
    }
  }
};

/**
 * Validates that required attributes have values.
 */
const validateRequiredAttribute = (
  attribute: Attribute,
  currentValue: unknown,
  entityName: string,
  uniqueKey: string,
  requiredAttributeErrors: RequiredAttributeError[]
): boolean => {
  if (attribute.required && (currentValue === undefined || currentValue === null || currentValue === "")) {
    requiredAttributeErrors.push({
      entityName,
      uniqueKey,
      attributeName: attribute.name,
      value: currentValue || "",
      message: `Required attribute '${attribute.name}' is missing or empty`,
    });
    return false;
  }
  return true;
};

/**
 * Validates that the attribute value matches the expected data type.
 */
const validateAttributeType = (
  attribute: Attribute,
  currentValue: unknown,
  entityName: string,
  uniqueKey: string,
  validationErrors: ValidationError[],
  validationWarnings: ValidationError[]
): boolean => {
  if (!attribute.type || validateType(currentValue, attribute.type)) return true;

  const error: ValidationError = {
    entityName,
    uniqueKey,
    attributeName: attribute.name,
    value: currentValue,
    message: `Expected type '${attribute.type}' but got '${typeof currentValue}'`,
  };

  if (attribute.required) {
    validationErrors.push(error);
    return false;
  } else {
    validationWarnings.push(error);
    return true;
  }
};

/**
 * Validates that list attribute values match allowed options.
 */
const validateAttributeList = (
  attribute: Attribute,
  currentValue: unknown,
  entityName: string,
  uniqueKey: string,
  validationErrors: ValidationError[],
  validationWarnings: ValidationError[]
): boolean => {
  if (attribute.type !== "list" || !attribute.listvalue) return true;

  const { isValid, invalidValues } = validateListValue(currentValue, attribute.listvalue, attribute.listMultiSelect);

  if (isValid) return true;

  const error: ValidationError = {
    entityName,
    uniqueKey,
    attributeName: attribute.name,
    value: currentValue,
    message:
      invalidValues.length > 1
        ? `Values [${invalidValues.join(", ")}] do not match any of the allowed values: ${attribute.listvalue}`
        : `Value '${invalidValues[0]}' does not match any of the allowed values: ${attribute.listvalue}`,
  };

  if (attribute.required) {
    validationErrors.push(error);
    return false;
  } else {
    validationWarnings.push(error);
    return true;
  }
};

/**
 * Validates that attribute values match the specified regex pattern.
 */
const validateAttributeRegex = (
  attribute: Attribute,
  currentValue: unknown,
  entityName: string,
  uniqueKey: string,
  validationErrors: ValidationError[],
  validationWarnings: ValidationError[]
): boolean => {
  if (!attribute.validation_regex) return true;

  let regexValid = true;
  const invalidValues: string[] = [];

  if (Array.isArray(currentValue) && (attribute.type === "list" || attribute.type === "multivalue-string")) {
    for (const item of currentValue) {
      if (!validateRegex(item, attribute.validation_regex)) {
        regexValid = false;
        invalidValues.push(String(item));
      }
    }
  } else {
    if (!validateRegex(currentValue, attribute.validation_regex)) {
      regexValid = false;
      invalidValues.push(String(currentValue));
    }
  }

  if (regexValid) return true;

  const error: ValidationError = {
    entityName,
    uniqueKey,
    attributeName: attribute.name,
    value: currentValue,
    message:
      invalidValues.length > 1
        ? `Values [${invalidValues.join(", ")}] do not match required pattern: ${attribute.validation_regex}`
        : attribute.validation_regex_msg ||
          `Value ${invalidValues[0]} does not match required pattern: ${attribute.validation_regex}`,
  };

  if (attribute.required) {
    validationErrors.push(error);
    return false;
  } else {
    validationWarnings.push(error);
    return true;
  }
};

/**
 * Validates that tag values are properly formatted objects.
 */
const validateAttributeTag = (
  attribute: Attribute,
  currentValue: unknown,
  entityName: string,
  uniqueKey: string,
  validationErrors: ValidationError[],
  validationWarnings: ValidationError[]
): boolean => {
  if (attribute.type !== "tag" || !currentValue) return true;

  if (!Array.isArray(currentValue)) {
    const error: ValidationError = {
      entityName,
      uniqueKey,
      attributeName: attribute.name,
      value: currentValue,
      message: "Tags must be an array of objects with key and value properties",
    };

    if (attribute.required) {
      validationErrors.push(error);
      return false;
    } else {
      validationWarnings.push(error);
      return true;
    }
  }

  const invalidTags: string[] = [];
  for (const tag of currentValue) {
    if (
      typeof tag !== "object" ||
      tag === null ||
      typeof tag.key !== "string" ||
      typeof tag.value !== "string" ||
      tag.key.trim() === "" ||
      tag.value.trim() === ""
    ) {
      invalidTags.push(JSON.stringify(tag));
    }
  }

  if (invalidTags.length === 0) return true;

  const error: ValidationError = {
    entityName,
    uniqueKey,
    attributeName: attribute.name,
    value: currentValue,
    message: `Invalid tag objects. Expected [{key: string, value: string}]. Invalid tags: ${invalidTags.join(", ")}`,
  };

  if (attribute.required) {
    validationErrors.push(error);
    return false;
  } else {
    validationWarnings.push(error);
    return true;
  }
};

/**
 * Validates cross-references between entities, collecting backend validation needs.
 */
const collectCrossReferencesForValidation = (
  attribute: Attribute,
  currentValue: unknown,
  entityName: string,
  uniqueKey: string,
  deduplicatedEntities: Record<string, DeduplicatedEntity>,
  backendValidationRequests: Map<string, BackendValidationRequest>
) => {
  if (!attribute.rel_entity || !currentValue) return;

  const normalizedRelEntity = normalizeEntityName(attribute.rel_entity);
  const relatedEntity = deduplicatedEntities[normalizedRelEntity];
  const valuesToCheck = Array.isArray(currentValue) ? currentValue : [currentValue];
  const missingReferences: string[] = [];

  if (!relatedEntity) {
    // Entity type doesn't exist in current file - need to check all references in backend
    missingReferences.push(...valuesToCheck.map(String));
  } else {
    // Entity type exists, check individual references
    for (const value of valuesToCheck) {
      if (!relatedEntity.data[String(value)]) {
        // Cross-reference not found in current file - need to check in backend
        missingReferences.push(String(value));
      }
    }
  }

  if (missingReferences.length > 0) {
    // Collect backend validation request
    if (!backendValidationRequests.has(normalizedRelEntity)) {
      backendValidationRequests.set(normalizedRelEntity, {
        entityType: normalizedRelEntity,
        references: new Set(),
        validationItems: [],
      });
    }

    const request = backendValidationRequests.get(normalizedRelEntity);
    if (request) {
      missingReferences.forEach((ref) => request.references.add(ref));
      request.validationItems.push({
        entityName,
        uniqueKey,
        attributeName: attribute.name,
        referencedKeys: missingReferences,
      });
    }
  }
};

/**
 * Processes multivalue strings and tags by converting them to appropriate formats.
 */
const processMultivalueStrings = (item: Record<string, unknown>, schema: EntitySchema): void => {
  for (const attribute of schema.attributes) {
    const value = item[attribute.name];

    // Convert list type values to strings
    if (value && attribute.type === "list") {
      if (Array.isArray(value)) {
        item[attribute.name] = value.map((v) => String(v));
      } else {
        item[attribute.name] = String(value);
      }
    } else if (value && attribute.type === "tag" && typeof value === "string") {
      const tagString = value.trim();
      if (tagString === "") {
        item[attribute.name] = [];
      } else {
        const cleanTagString = tagString.endsWith(";") ? tagString.slice(0, -1) : tagString;
        item[attribute.name] = cleanTagString
          .split(";")
          .map((tag) => {
            const [key, val] = tag.split("=");
            return { key: key?.trim() || "", value: val?.trim() || "" };
          })
          .filter((tag) => tag.key !== "" || tag.value !== "");
      }
    } else if (
      value &&
      (attribute.type === "multivalue-string" ||
        attribute.type === "multivalue-relationship" ||
        (attribute.type === "list" && attribute.listMultiSelect))
    ) {
      if (typeof value === "string") {
        item[attribute.name] = value
          .split(";")
          .map((v) => v.trim())
          .filter((v) => v !== "");
      } else if (Array.isArray(value)) {
        item[attribute.name] = value.map((v) => String(v).trim()).filter((v) => v !== "");
      }
    }
  }
};

/**
 * Validates a single entity item against its schema.
 */
const validateSingleItem = (
  item: Record<string, unknown>,
  entity: DeduplicatedEntity,
  uniqueKey: string,
  deduplicatedEntities: Record<string, DeduplicatedEntity>,
  errors: {
    requiredAttributeErrors: RequiredAttributeError[];
    validationErrors: ValidationError[];
    validationWarnings: ValidationError[];
  },
  backendValidationRequests: Map<string, BackendValidationRequest>
): boolean => {
  const schemaAttributeNames = new Set(entity.schema.attributes.map((attr) => attr.name));
  let isValidItem = true;

  processMultivalueStrings(item, entity.schema);
  checkExtraFields(item, schemaAttributeNames, entity.entityName, uniqueKey, errors.validationWarnings);

  for (const attribute of entity.schema.attributes) {
    if (item[attribute.name] === undefined && attribute.default !== undefined) {
      item[attribute.name] = attribute.default;
    }

    // Handle server_os_family field - set to TBC if value is not in allowed list
    if (attribute.name === "server_os_family" && attribute.listvalue) {
      const allowedValues = attribute.listvalue.split(",").map((val) => val.trim().toLowerCase());
      const currentVal = String(item[attribute.name]).toLowerCase();
      if (!allowedValues.includes(currentVal)) {
        item[attribute.name] = "TBC";
      }
    }

    const currentValue = item[attribute.name];
    const hasValue = currentValue !== undefined && currentValue !== null && currentValue !== "";

    if (
      !validateRequiredAttribute(attribute, currentValue, entity.entityName, uniqueKey, errors.requiredAttributeErrors)
    ) {
      isValidItem = false;
    }

    if (hasValue) {
      if (
        !validateAttributeType(
          attribute,
          currentValue,
          entity.entityName,
          uniqueKey,
          errors.validationErrors,
          errors.validationWarnings
        )
      ) {
        isValidItem = false;
      }
      if (
        !validateAttributeList(
          attribute,
          currentValue,
          entity.entityName,
          uniqueKey,
          errors.validationErrors,
          errors.validationWarnings
        )
      ) {
        isValidItem = false;
      }
      if (
        !validateAttributeRegex(
          attribute,
          currentValue,
          entity.entityName,
          uniqueKey,
          errors.validationErrors,
          errors.validationWarnings
        )
      ) {
        isValidItem = false;
      }
      if (
        !validateAttributeTag(
          attribute,
          currentValue,
          entity.entityName,
          uniqueKey,
          errors.validationErrors,
          errors.validationWarnings
        )
      ) {
        isValidItem = false;
      }

      collectCrossReferencesForValidation(
        attribute,
        currentValue,
        entity.entityName,
        uniqueKey,
        deduplicatedEntities,
        backendValidationRequests
      );
    }
  }

  return isValidItem;
};

/**
 * Validates all entity attributes through comprehensive validation.
 */
export const validateAttributes = (
  deduplicatedEntities: Record<string, DeduplicatedEntity>
): AttributeValidationResult => {
  const errors = {
    requiredAttributeErrors: [] as RequiredAttributeError[],
    validationErrors: [] as ValidationError[],
    validationWarnings: [] as ValidationError[],
    crossReferenceErrors: [] as CrossReferenceError[],
  };
  const backendValidationRequests = new Map<string, BackendValidationRequest>();
  const validatedEntities: DeduplicatedEntity[] = [];

  // First pass: collect all validation needs
  for (const entity of Object.values(deduplicatedEntities)) {
    const validatedData: Record<string, Record<string, unknown>> = {};

    for (const [uniqueKey, item] of Object.entries(entity.data)) {
      if (validateSingleItem(item, entity, uniqueKey, deduplicatedEntities, errors, backendValidationRequests)) {
        validatedData[uniqueKey] = item;
      }
    }

    validatedEntities.push({ ...entity, data: validatedData });
  }

  return {
    validatedEntities,
    errors: errors.requiredAttributeErrors,
    validationErrors: errors.validationErrors,
    validationWarnings: errors.validationWarnings,
    crossReferenceErrors: errors.crossReferenceErrors,
    backendValidationRequests: Array.from(backendValidationRequests.values()),
  };
};
