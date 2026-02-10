import { WorkBook, utils } from "xlsx";
import { EntityAttribute, HeaderToEntityAttributeMapping, EntitySchema } from "../../models";
import { SheetToEntityMapping } from "./data-source-types";
import { EntityForValidation } from "../data-validation";

/**
 * Custom error class for when a sheet is not found in the workbook.
 */
export class SheetNotFoundError extends Error {
  constructor(public readonly sheetName: string) {
    super(`Sheet ${sheetName} not found in workbook`);
    this.name = "SheetNotFoundError";
  }
}

/**
 * Creates entity-specific records from a row of data using the provided header mappings.
 *
 * @param headers - The mappings from headers to entity attributes
 * @param row - The row of data from the sheet
 * @param currentRowEntityIdentifiers - Array to collect entity identifiers
 * @returns A map of entity names to their specific records
 */
const createEntityRecords = (
  headers: HeaderToEntityAttributeMapping[],
  row: Record<string, unknown>,
  currentRowEntityIdentifiers: EntityAttribute[]
): Record<string, Record<string, unknown>> => {
  const entityRecords: Record<string, Record<string, unknown>> = {};

  for (const header of headers) {
    const { name, entityAttributes } = header;
    if (!name) {
      throw new Error(`Header name is not defined.`);
    }

    const value = row[name];
    for (const entityAttribute of entityAttributes) {
      const { entityName, attributeName } = entityAttribute;

      // Initialize entity record if it doesn't exist
      if (!entityRecords[entityName]) {
        entityRecords[entityName] = {};
      }

      // Add attribute to the specific entity record
      entityRecords[entityName][attributeName] = value;

      if (attributeName === `${entityName}_name` || (entityName === "application" && attributeName === "app_name")) {
        currentRowEntityIdentifiers.push(entityAttribute);
      }
    }
  }
  return entityRecords;
};

/**
 * Adds entity-specific records to the collected data map, organizing by entity type and identifier.
 *
 * @param currentRowEntityIdentifiers - Array of entity identifiers found in the records
 * @param collectedData - Record to collect data by entity type and identifier
 * @param entityRecords - The entity-specific records to add
 */
const addRecordsToCollection = (
  currentRowEntityIdentifiers: EntityAttribute[],
  collectedData: Record<string, Record<string, Record<string, unknown>[]>>,
  entityRecords: Record<string, Record<string, unknown>>
): void => {
  for (const rowEntityIdentifier of currentRowEntityIdentifiers) {
    const { attributeName, entityName } = rowEntityIdentifier;
    const entityRecord = entityRecords[entityName];

    if (!entityRecord) {
      continue;
    }

    const originalIdentifier = entityRecord[attributeName];

    // Skip records with invalid or empty identifiers
    if (originalIdentifier === undefined || originalIdentifier === null) {
      console.warn(
        `Skipping record for entity '${entityName}' with invalid identifier '${originalIdentifier}' (type: ${typeof originalIdentifier}). Attribute: ${attributeName}`
      );
      continue;
    }

    // Cast to string and update the object value to also be the trimmed string
    const entityIdentifier = String(originalIdentifier);

    // Trim whitespace from identifier
    const trimmedIdentifier = entityIdentifier.trim();
    entityRecord[attributeName] = trimmedIdentifier;

    // Skip records with empty identifiers after trimming
    if (trimmedIdentifier === "") {
      console.warn(
        `Skipping record for entity '${entityName}' with empty identifier after trimming. Attribute: ${attributeName}`
      );
      continue;
    }

    const data = collectedData[entityName];
    if (data) {
      const existingRecords = data[trimmedIdentifier];
      if (existingRecords) {
        existingRecords.push(entityRecord);
      } else {
        data[trimmedIdentifier] = [entityRecord];
      }
    } else {
      collectedData[entityName] = {
        [trimmedIdentifier]: [entityRecord],
      };
    }
  }
};

/**
 * Processes sheet data from a workbook according to the provided mappings.
 *
 * @param mappings - The mappings from sheet headers to entity attributes
 * @param workbook - The Excel workbook containing the data
 * @param schemas - Record of entity schemas keyed by entity name
 * @returns An array of EntityForValidation objects ready for validation
 * @throws SheetNotFoundError if a sheet is not found in the workbook
 * @throws Error if a header name is undefined, an entity identifier is not a string, or a schema is not found
 */
export const processSheetData = (
  mappings: SheetToEntityMapping[],
  workbook: WorkBook,
  schemas: Record<string, EntitySchema>
): EntityForValidation[] => {
  // Step 1: Collect data by entity type and identifier
  const collectedData: Record<string, Record<string, Record<string, unknown>[]>> = {};

  for (const mapping of mappings) {
    const { sheetName, headers } = mapping;

    const sheet = workbook.Sheets[sheetName];
    if (!sheet) {
      throw new SheetNotFoundError(sheetName);
    }

    const rows = utils.sheet_to_json(sheet) as Record<string, unknown>[];

    for (const row of rows) {
      const entityIdentifiers: EntityAttribute[] = [];
      const entityRecords = createEntityRecords(headers, row, entityIdentifiers);

      // Skip rows that don't map to any entity
      if (entityIdentifiers.length > 0) {
        addRecordsToCollection(entityIdentifiers, collectedData, entityRecords);
      }
    }
  }

  // Step 2: Convert collected data to EntityForValidation array
  const entitiesForValidation: EntityForValidation[] = [];

  for (const [entityName, entityData] of Object.entries(collectedData)) {
    // Verify schema exists for this entity type
    const schema = schemas[entityName];
    if (!schema) {
      throw new Error(`Schema not found for entity type: ${entityName}`);
    }

    // Filter out attributes not in schema
    const schemaAttributes = new Set(schema.attributes.map((attr) => attr.name));
    const filteredData: Record<string, Record<string, unknown>[]> = {};

    for (const [identifier, records] of Object.entries(entityData)) {
      filteredData[identifier] = records.map((record) => {
        const filteredRecord: Record<string, unknown> = {};
        for (const [attrName, value] of Object.entries(record)) {
          if (schemaAttributes.has(attrName)) {
            filteredRecord[attrName] = value;
          }
        }
        return filteredRecord;
      });
    }

    // Create EntityForValidation object
    entitiesForValidation.push({
      entityName,
      schema,
      data: filteredData,
    });
  }

  return entitiesForValidation;
};
