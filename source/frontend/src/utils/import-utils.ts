/* eslint-disable */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import * as XLSX from "xlsx";
import { getChanges, validateTags, validateValue } from "../resources/main";
import { Attribute, EntitySchema } from "../models/EntitySchema";
import { checkAttributeRequiredConditions, getRequiredAttributes } from "../resources/recordFunctions";
import { EntityId } from "../api_clients/userApiClient";
import UserApiClient from "../api_clients/userApiClient";
import { CompletionNotification } from "../models/CompletionNotification";

type ImportAttribute = {
  attribute: {
    type: any;
    validation_regex?: any;
    validation_regex_msg?: any;
    requiredTags?: any;
  };
  lookup_attribute_name: string;
};

//Function to remove null key values from json object array.
export function removeNullKeys(dataJson: Record<string, any>[]) {
  for (const dataItem of dataJson) {
    for (const key in dataItem) {
      if (dataItem[key] === null || dataItem[key] === "") {
        delete dataItem[key];
      }
    }
  }
  return dataJson;
}

export function splitIntoEntities(
  dataJson: Record<string, any>[],
  schemas: Record<string, EntitySchema>
): Record<string, any>[] {
  const result: Record<string, any>[] = [];

  for (const dataRow of dataJson) {
    // Group attributes by schema
    const entitiesBySchema: Record<string, Record<string, any>> = {};
    // Track which attributes belong to which schemas for validation filtering
    const attributesBySchema: Record<string, string[]> = {};

    // Process each attribute in the data row
    for (const [key, value] of Object.entries(dataRow)) {
      // Skip validation and import metadata
      if (key.startsWith("__")) {
        continue;
      }

      // Determine which schema(s) this attribute belongs to
      let attributeName = key;
      let foundInAnySchema = false;

      // Find which schema(s) contain this attribute
      for (const [schemaName, schema] of Object.entries(schemas)) {
        if (schema.schema_type !== "user") continue;

        // Check if this schema has an attribute with this name
        const hasAttribute = schema.attributes.some((attr) => {
          // Basic name match
          if (attr.name === attributeName) {
            return true;
            // Relationship match
          } else if (attr.type === "relationship" || attr.type === "multivalue-relationship") {
            return attr.rel_display_attribute === attributeName;
          } else {
            return false;
          }
        });

        if (hasAttribute) {
          foundInAnySchema = true;
          if (!entitiesBySchema[schemaName]) {
            entitiesBySchema[schemaName] = {};
            attributesBySchema[schemaName] = [];
          }
          entitiesBySchema[schemaName][key] = value;
          attributesBySchema[schemaName].push(key);
        }
      }

      // If attribute wasn't found in any schema, we need to preserve it and its validation warnings
      if (!foundInAnySchema) {
        // Add to all schemas or create a default entity if no schemas have been created yet
        if (Object.keys(entitiesBySchema).length === 0) {
          // No schemas matched yet, create a default entity to hold unmatched attributes
          const defaultSchema = "__unmatched__";
          entitiesBySchema[defaultSchema] = {};
          attributesBySchema[defaultSchema] = [];
        }

        // Add the unmatched attribute to all existing schema entities
        for (const schemaName of Object.keys(entitiesBySchema)) {
          entitiesBySchema[schemaName][key] = value;
          attributesBySchema[schemaName].push(key);
        }
      }
    }

    // Helper function to filter validation messages for a specific entity
    const filterValidationForEntity = (originalValidation: any, entityAttributes: string[]) => {
      if (!originalValidation) return originalValidation;

      const filteredValidation = { ...originalValidation };

      // Filter errors and warnings to only include those relevant to this entity's attributes
      if (originalValidation.errors) {
        filteredValidation.errors = originalValidation.errors.filter((error: any) =>
          entityAttributes.includes(error.attribute)
        );
      }

      if (originalValidation.warnings) {
        filteredValidation.warnings = originalValidation.warnings.filter((warning: any) =>
          entityAttributes.includes(warning.attribute)
        );
      }

      if (originalValidation.informational) {
        filteredValidation.informational = originalValidation.informational.filter((info: any) =>
          entityAttributes.includes(info.attribute)
        );
      }

      return filteredValidation;
    };

    // Create separate entity records for each schema that has data
    for (const [schemaName, entityData] of Object.entries(entitiesBySchema)) {
      // Skip the special unmatched schema if other schemas exist
      if (schemaName === "__unmatched__" && Object.keys(entitiesBySchema).length > 1) {
        continue;
      }

      // Only create entity if it contains key attribute (except for unmatched schema)
      const hasKeyAttribute = Object.keys(entityData).some((key) => {
        const schemaShortName = schemaName === "application" ? "app" : schemaName;
        return key === schemaShortName + "_name" || key === schemaShortName + "_id";
      });

      if (hasKeyAttribute || Object.keys(entitiesBySchema).length === 1 || schemaName === "__unmatched__") {
        // Copy entity data
        const entityRecord = { ...entityData };

        // Copy over metadata fields with filtered validation
        for (const [key, value] of Object.entries(dataRow)) {
          if (key.startsWith("__")) {
            if (key === "__validation") {
              // Filter validation messages to only include those relevant to this entity
              entityRecord[key] = filterValidationForEntity(value, attributesBySchema[schemaName] || []);
            } else {
              entityRecord[key] = value;
            }
          }
        }
        entityRecord["__schema"] = schemaName;

        result.push(entityRecord);
      }
    }

    // If no entities were created (no user schemas matched), add the original row
    if (Object.keys(entitiesBySchema).length === 0) {
      result.push({ ...dataRow });
    }
  }

  return result;
}

export function mergeDuplicates(
  dataJson: Record<string, any>[],
  schemas: Record<string, EntitySchema>
): Record<string, any>[] {
  const entityMap = new Map<string, Record<string, any>>();

  // Process each data item
  for (const dataItem of dataJson) {
    // Determine which schema this entity belongs to
    let entitySchema: string | null = null;
    let entityKey: string | null = null;

    if (dataItem["__schema"]) {
      const schemaName = dataItem["__schema"];
      const tempSchemaName = schemaName === "application" ? "app" : schemaName;
      const nameKey = tempSchemaName + "_name";
      const idKey = tempSchemaName + "_id";

      if (dataItem[nameKey] || dataItem[idKey]) {
        entitySchema = schemaName;
        entityKey = createEntityKey(schemaName, dataItem);
      }
    }

    // If no schema found, add the item as-is
    if (!entitySchema || !entityKey) {
      entityMap.set(JSON.stringify(dataItem), dataItem);
      continue;
    }

    // Check if we already have an entity with this key
    if (entityMap.has(entityKey)) {
      const existingEntity = entityMap.get(entityKey)!;
      const mergedEntity = mergeEntityData(existingEntity, dataItem, schemas[entitySchema]);
      entityMap.set(entityKey, mergedEntity);
    } else {
      entityMap.set(entityKey, { ...dataItem });
    }
  }

  return Array.from(entityMap.values());
}

// Helper function to merge two entity records
function mergeEntityData(
  existing: Record<string, any>,
  incoming: Record<string, any>,
  schema: EntitySchema
): Record<string, any> {
  const merged = { ...existing };

  // Get all multivalue-relationship attributes for this schema
  const multivalueRelationshipAttrs = schema.attributes.filter((attr) => attr.type === "multivalue-relationship");

  // Helper function to convert semicolon-delimited string to array
  const stringToArray = (str: string): string[] => {
    return str
      .split(";")
      .map((item) => item.trim())
      .filter((item) => item !== "");
  };

  // Helper function to convert array to semicolon-delimited string
  const arrayToString = (arr: string[]): string => {
    return arr.join(";");
  };

  // Merge each property from incoming into existing
  for (const [key, value] of Object.entries(incoming)) {
    if (key.startsWith("__")) {
      // Handle metadata fields - preserve existing validation info
      continue;
    }

    // Check if this is a multivalue-relationship attribute
    const isMultivalueRelationship = multivalueRelationshipAttrs.some((attr) => attr.rel_display_attribute === key);

    if (isMultivalueRelationship) {
      // Convert both existing and incoming values to arrays for processing
      let existingArray: string[] = [];
      let incomingArray: string[] = [];

      // Handle existing value
      if (Array.isArray(merged[key])) {
        existingArray = merged[key];
      } else if (typeof merged[key] === "string" && merged[key] !== "") {
        existingArray = stringToArray(merged[key]);
      }

      // Handle incoming value
      if (Array.isArray(value)) {
        incomingArray = value;
      } else if (typeof value === "string" && value !== "") {
        incomingArray = stringToArray(value);
      }

      // Merge arrays and remove duplicates
      if (incomingArray.length > 0) {
        const combinedArray = [...existingArray, ...incomingArray];
        const uniqueArray = [...new Set(combinedArray)];
        // Store as semicolon-delimited string to match expected format
        merged[key] = arrayToString(uniqueArray);
      } else if (existingArray.length > 0) {
        // Keep existing value as semicolon-delimited string
        merged[key] = arrayToString(existingArray);
      }
    } else if (value !== undefined && value !== null && value !== "") {
      // For non-multivalue fields, incoming value overwrites existing
      merged[key] = value;
    }
  }

  return merged;
}

// Helper function to create a unique key for an entity
function createEntityKey(schemaName: string, entityRecord: Record<string, any>): string {
  const schemaShortName = schemaName === "application" ? "app" : schemaName;

  // Try to find the key attribute (name or id)
  let keyValue = entityRecord[schemaShortName + "_name"] || entityRecord[schemaShortName + "_id"];

  if (!keyValue) {
    // If no key attribute found, use all non-metadata attributes to create a unique key
    const nonMetadataKeys = Object.keys(entityRecord)
      .filter((key) => !key.startsWith("__"))
      .sort();
    keyValue = nonMetadataKeys.map((key) => `${key}:${entityRecord[key]}`).join("|");
  }

  return `${schemaName}:${keyValue}`;
}

export function readXLSXFile(reader: FileReader, file: Blob) {
  return new Promise((resolve, reject) => {
    reader.onerror = () => {
      reader.abort();
      reject(new DOMException("Problem parsing input file."));
    };

    reader.onload = () => {
      resolve(reader.result);
    };
    reader.readAsArrayBuffer(file);
  });
}

export async function convertDataFileToJSON(reader: FileReader, selectedFile: Blob, selectedSheet?: string) {
  const data = await readXLSXFile(reader, selectedFile);
  const workbook = XLSX.read(data, { raw: true });

  let sheet: any;
  if (selectedSheet) {
    if (workbook.Sheets[selectedSheet]) {
      sheet = workbook.Sheets[selectedSheet];
    } else {
      sheet = workbook.Sheets[workbook.SheetNames[0]];
    }
  } else {
    sheet = workbook.Sheets[workbook.SheetNames[0]];
  }
  //Convert all numbers to text.
  Object.keys(sheet).forEach(function (s) {
    if (sheet[s].t === "n") {
      delete sheet[s].w;
      sheet[s].z = "0";
      sheet[s].t = "s";
      sheet[s].w = sheet[s].v.toString();
      sheet[s].v = sheet[s].v.toString();
    }
  });

  return XLSX.utils.sheet_to_json(sheet);
}

export function performValueValidation(attribute: ImportAttribute, value: string) {
  //Exit if attribute is not defined or null.
  if (!attribute.attribute && value !== "")
    return {
      type: "warning",
      message:
        attribute.lookup_attribute_name +
        " attribute name not found in any user schema and your data file has provided values.",
    };
  else if (!attribute.attribute && value === "") return null;

  let errorMsg = null;

  switch (attribute.attribute.type) {
    case "list":
      errorMsg = validateList(attribute, value);
      break;
    case "multivalue-string":
      errorMsg = validateMultiString(attribute, value);
      break;
    case "relationship":
      errorMsg = validateValue(value, attribute.attribute);
      break;
    case "json":
      errorMsg = validateJson(value);
      break;
    case "tag":
      const errorMsgList = validateTags(attribute.attribute, parseTagsString(value));
      if (errorMsgList) {
        errorMsg = errorMsgList.join(", ");
      }
      break;
    default:
      errorMsg = validateValue(value, attribute.attribute);
  }

  if (errorMsg != null) return { type: "error", message: errorMsg };
  else return null;
}

function validateList(attribute: ImportAttribute, value: string) {
  let errorMsg = null;
  const list = value.split(";");
  for (const item in list) {
    const currError = validateValue(list[item], attribute.attribute);
    errorMsg = currError ? currError : errorMsg;
  }
  return errorMsg;
}

function validateJson(value: string) {
  let errorMsg = null;
  if (value) {
    try {
      JSON.parse(value);
    } catch (objError: any) {
      if (objError instanceof SyntaxError) {
        console.error(objError.name);
        errorMsg = "Invalid JSON: " + objError.message;
      } else {
        console.error(objError.message);
      }
    }
  }
  return errorMsg;
}

function validateMultiString(attribute: ImportAttribute, value: string) {
  let errorMsg = null;
  const mvlist = value.split(";");
  for (const item in mvlist) {
    const currError = validateValue(mvlist[item], attribute.attribute);
    errorMsg = currError ? currError : errorMsg;
  }
  return errorMsg;
}

function getSchemaAttribute(attributeName: string, schema: EntitySchema) {
  let attr = null;

  for (const attribute of schema.attributes) {
    if (attribute.name === attributeName) {
      attr = attribute;
      break;
    }
  }

  return attr;
}

function getSchemaRelationshipAttributes(attributeName: string | undefined, schema: EntitySchema) {
  const attributes = [];

  for (const attribute of schema.attributes) {
    if (attribute.type === "relationship" || attribute.type === "multivalue-relationship") {
      if (attribute.rel_display_attribute === attributeName) {
        //We've got a live one!!
        attributes.push(attribute);
        break;
      }
    }
  }

  return attributes.length > 0 ? attributes : null;
}

function getFindAttributeWithSchemaName(
  attributeName: string,
  schemas: Record<string, EntitySchema>,
  schema_name: string
) {
  let attr = null;
  const attrList: (
    | { attribute: null; schema_name: null; lookup_attribute_name: string; lookup_schema_name: string }
    | { attribute: Attribute; schema_name: string; lookup_attribute_name: string; lookup_schema_name: string }
  )[] = [];
  if (!schemas[schema_name]) {
    attrList.push({
      attribute: attr,
      schema_name: null,
      lookup_attribute_name: attributeName,
      lookup_schema_name: schema_name,
    }); //Schema_name not valid.
  } else {
    if (schemas[schema_name].schema_type === "user") {
      attr = getSchemaAttribute(attributeName, schemas[schema_name]);
      if (attr) {
        attrList.push({
          attribute: attr,
          schema_name: schema_name,
          lookup_attribute_name: attributeName,
          lookup_schema_name: schema_name,
        });
      } else
        attrList.push({
          attribute: attr,
          schema_name: null,
          lookup_attribute_name: attributeName,
          lookup_schema_name: schema_name,
        });
    } else {
      attrList.push({
        attribute: attr,
        schema_name: null,
        lookup_attribute_name: attributeName,
        lookup_schema_name: schema_name,
      });
    }
  }
  return attrList;
}

function getFindAttributeWithNoSchemaName(attributeName: string, schemas: Record<string, EntitySchema>) {
  const attrList: {
    attribute: Attribute;
    schema_name: string;
    lookup_attribute_name: string;
    lookup_schema_name: string;
  }[] = [];
  for (const schema_name in schemas) {
    if (schemas[schema_name].schema_type === "user") {
      let lAttr = null;
      lAttr = getSchemaAttribute(attributeName, schemas[schema_name]);
      if (lAttr) {
        attrList.push({
          attribute: lAttr,
          schema_name: schema_name,
          lookup_attribute_name: attributeName,
          lookup_schema_name: schema_name,
        });
      }

      let lRelatedAttrs = null;
      lRelatedAttrs = getSchemaRelationshipAttributes(attributeName, schemas[schema_name]);
      if (lRelatedAttrs) {
        for (const lRelatedAttr of lRelatedAttrs) {
          attrList.push({
            attribute: lRelatedAttr,
            schema_name: schema_name,
            lookup_attribute_name: attributeName,
            lookup_schema_name: schema_name,
          });
        }
      }
    }
  }
  return attrList;
}

function getFindAttribute(attributeName: string, schemas: Record<string, EntitySchema>, schema_name?: string): any[] {
  let attrList: any[] = [];
  if (schemas) {
    if (schema_name) {
      attrList = getFindAttributeWithSchemaName(attributeName, schemas, schema_name);
    } else {
      attrList = getFindAttributeWithNoSchemaName(attributeName, schemas);
    }
  }

  //Not found set default response.
  if (attrList.length === 0) {
    attrList.push({
      attribute: null,
      schema_name: null,
      lookup_attribute_name: attributeName,
      lookup_schema_name: schema_name,
    });
  }

  return attrList;
}

export function performDataValidation(schemas: Record<string, EntitySchema>, csvData: Record<string, any>[]) {
  const attributeMappings: any[] = [];
  const schemaNames: string[] = [];

  for (const [itemIdx, item] of csvData.entries()) {
    const itemErrors: any[] = [];
    const itemWarnings: any[] = [];
    const itemInformational: any[] = [];
    for (const key in item) {
      performDataValidationForItem(
        [key, item],
        schemaNames,
        schemas,
        itemErrors,
        itemWarnings,
        itemInformational,
        attributeMappings
      );
    }

    item["__import_row"] = itemIdx;
    item["__validation"] = {};
    item["__validation"]["errors"] = itemErrors;
    item["__validation"]["warnings"] = itemWarnings;
    item["__validation"]["informational"] = itemInformational;
  }

  return { data: csvData, attributeMappings: attributeMappings, schema_names: schemaNames };
}

function performDataValidationForItem(
  keyItemTuple: [string, any],
  schemaNames: string[],
  schemas: Record<string, EntitySchema>,
  itemErrors: any[],
  itemWarnings: any[],
  itemInformational: any[],
  attributeMappings: any[]
) {
  const [key, item] = keyItemTuple;
  let attr: any[] = [];
  let schema_name = null;
  if (key.startsWith("[")) {
    //Schema name provided in key.
    const keySplit = key.split("]");
    if (keySplit.length > 1) {
      if (keySplit[0] !== "" && keySplit[1] !== "") {
        schema_name = keySplit[0].substring(1);
        attr = getFindAttribute(keySplit[1], schemas, schema_name);
      } else {
        //check with full key as not in correct format.
        //Key does not provide schema hint.
        attr = getFindAttribute(key, schemas);
      }
    } else {
      //check with full key as not in correct format.
      //Key does not provide schema hint.
      attr = getFindAttribute(key, schemas);
    }
  } else {
    //Key does not provide schema hint.
    attr = getFindAttribute(key, schemas);
  }

  if (attr.length > 1) {
    itemInformational.push({
      attribute: key,
      error:
        "Ambiguous attribute name provided. It is found in multiple schemas [" +
        attr
          .map((item) => {
            return item.schema_name;
          })
          .join(", ") +
        "]. Import will map data to schemas as required based on record types.",
    });
  }

  performValidationForAttr(attr, key, item, schemaNames, attributeMappings, itemErrors, itemWarnings);
}

function performValidationForAttr(
  attr: any,
  key: string,
  item: any,
  schemaNames: string[],
  attributeMappings: any[],
  itemErrors: any[],
  itemWarnings: any[]
) {
  for (const foundAttr of attr) {
    foundAttr["import_raw_header"] = key;

    const filterMappings = attributeMappings.filter((item) =>
      item["import_raw_header"] === key ? item["schema_name"] === foundAttr.schema_name : false
    );

    if (filterMappings.length === 0) {
      attributeMappings.push(foundAttr);
    }

    //Add schema names to list for quick lookup later.
    if (foundAttr.attribute && !schemaNames.includes(foundAttr.schema_name)) {
      schemaNames.push(normalizeEntityName(foundAttr.schema_name));
    }

    const msgError = performValueValidation(foundAttr, item[key]);
    if (msgError) {
      if (msgError.type === "error") {
        itemErrors.push({ attribute: key, error: msgError.message });
      } else if (msgError.type === "warning") {
        itemWarnings.push({ attribute: key, error: msgError.message });
      }
    }
  }
}

export function normalizeEntityName(entityName: string): string {
  return entityName === "app" ? "application" : entityName;
}

function updateSummaryForRecordKeyValue(
  dataJson: any,
  schemaAttributes: any[],
  keyAttribute: any,
  importedRecordKeyValue: any,
  { schemaName, schemas }: { schemaName: string; schemas: Record<string, EntitySchema> },
  dataAll: Record<string, any>,
  result: {
    attributeMappings: any[];
    entities: Record<string, any>;
    hasUpdates: boolean;
  }
) {
  const itemOrMismatch = isMismatchedItem(
    dataJson.data,
    schemaAttributes,
    keyAttribute.import_raw_header,
    importedRecordKeyValue.toLowerCase()
  );
  if (itemOrMismatch !== null) {
    const importRow = dataJson.data.find((importItem: { [x: string]: string }) =>
      isValidKeyValue(importItem, keyAttribute, importedRecordKeyValue, schemaName)
    );

    const importRecord: Record<string, any> = {};
    importRecord[keyAttribute.attribute.name] = importedRecordKeyValue;

    for (const attr of schemaAttributes) {
      addImportRowValuesToImportSummaryRecord(schemaName, attr, importRow, importRecord, dataAll);
    }

    const entityName = normalizeEntityName(schemaName);
    if (
      dataAll[entityName].data.some(
        (dataItem: { [x: string]: string }) =>
          dataItem[keyAttribute.attribute.name].toLowerCase() === importedRecordKeyValue.toLowerCase()
      )
    ) {
      addImportedRecordExistingToSummary(
        {
          schema: schemas[schemaName],
          schemaName: schemaName,
        },
        keyAttribute,
        importedRecordKeyValue,
        importRecord,
        result,
        importRow,
        dataAll
      );
    } else {
      addImportedRecordCreateToSummary(
        schemas[schemaName],
        schemaName,
        keyAttribute,
        importedRecordKeyValue,
        importRecord,
        result,
        importRow
      );
    }
  } else {
    //Not an issue as validation errors would have been recorded.
  }
}

function updateSummaryForSchema(
  distinct: Record<string, any>,
  { schemaName, schemas }: { schemaName: string; schemas: Record<string, EntitySchema> },
  dataJson: any,
  schemaAttributes: any[],
  keyAttribute: any,
  dataAll: Record<string, any>,
  result: {
    attributeMappings: any[];
    entities: Record<string, any>;
    hasUpdates: boolean;
  }
) {
  for (const importedRecordKeyValue of distinct[schemaName]) {
    if (importedRecordKeyValue === undefined) {
      continue;
    }

    if (importedRecordKeyValue.toLowerCase() !== "") {
      //Verify that the key has a value, if not ignore.
      updateSummaryForRecordKeyValue(
        dataJson,
        schemaAttributes,
        keyAttribute,
        importedRecordKeyValue,
        { schemaName, schemas },
        dataAll,
        result
      );
    }
  }
}

export function getSummary(
  schemas: Record<string, EntitySchema>,
  dataJson: any,
  dataAll: Record<string, any>
): {
  attributeMappings: any[];
  entities: Record<string, any>;
  hasUpdates: boolean;
} {
  const distinct: Record<string, any> = {};

  const result: { attributeMappings: any[]; entities: Record<string, any>; hasUpdates: boolean } = {
    entities: {} as Record<string, any>,
    hasUpdates: false,
    attributeMappings: [],
  };

  for (const schemaName in schemas) {
    if (schemas[schemaName].schema_type === "user") {
      result["entities"][schemaName] = {
        Create: [],
        Update: [],
        NoChange: [],
      };

      distinct[schemaName] = extractImportedRecordKeysForSchema(dataJson.data, schemaName);

      if (distinct[schemaName].length === 0) {
        //If nothing returned then continue to next schema.
        continue;
      }

      let schemaAttributes = [];

      schemaAttributes = dataJson.attributeMappings.filter((attr: { schema_name: string }) => {
        return normalizeEntityName(attr.schema_name) === normalizeEntityName(schemaName);
      });

      const keyAttribute = schemaAttributes.find((attr: { attribute: { name: string } }) => {
        //Get schema key attribute.
        const schemaShortname = schemaName === "application" ? "app" : schemaName;
        if (attr.attribute.name === schemaShortname + "_name" || attr.attribute.name === schemaShortname + "_id") {
          //check if _name key present in attributes
          return attr;
        }
      });
      updateSummaryForSchema(
        distinct,
        { schemaName, schemas },
        dataJson,
        schemaAttributes,
        keyAttribute,
        dataAll,
        result
      );
    }
  }

  //Pass attribute mappings back as needed to build table columns and config.
  result.attributeMappings = dataJson.attributeMappings;

  return result;
}

function findMismatchInArray(arrayItems: any[], checkAttributes: any[]) {
  let misMatchFound = false;
  const finalItem = arrayItems[0]; //set to first element as if not mismatched we with return this record.

  // Group array items by schema to validate consistency within each schema
  const itemsBySchema: Record<string, any[]> = {};
  for (const item of arrayItems) {
    const schema = item.__schema || "default";
    if (!itemsBySchema[schema]) {
      itemsBySchema[schema] = [];
    }
    itemsBySchema[schema].push(item);
  }

  // Group attributes by schema for more efficient processing
  const attributesBySchema: Record<string, any[]> = {};
  for (const attr of checkAttributes) {
    const schemaName = attr.schema_name || "default";
    if (!attributesBySchema[schemaName]) {
      attributesBySchema[schemaName] = [];
    }
    attributesBySchema[schemaName].push(attr);
  }

  // Validate consistency within each schema
  for (const [schemaName, schemaItems] of Object.entries(itemsBySchema)) {
    const schemaAttributes = attributesBySchema[schemaName] || [];

    for (const attr of schemaAttributes) {
      //For each attribute in this import for the same schema check that it is consistent.
      const distinctValue = [
        ...new Set(
          schemaItems.map((x) => {
            if (attr.attribute.type === "relationship" || attr.attribute.type === "multivalue-relationship") {
              return x[attr.attribute.rel_display_attribute];
            } else {
              return x[attr.attribute.name];
            }
          })
        ),
      ];

      if (distinctValue.length > 1) {
        //Problem found, update validation for all items with this item value within this schema.
        for (const item of schemaItems) {
          if (!item.__validation) {
            item.__validation = { errors: [], warnings: [], informational: [] };
          }
          item.__validation.errors.push({
            attribute: attr.attribute.name,
            error: attr.attribute.description + " cannot be different for the same " + attr.schema_name + ".",
          });
          misMatchFound = true;
        }
      }
    }
  }

  return { finalItem, misMatchFound };
}

export function isMismatchedItem(dataArray: any[], checkAttributes: any[], key: any, value: any) {
  let misMatchFound = false;
  let finalItem = null;

  const arrayItems = dataArray.filter((item) => {
    if (item[key]) {
      if (item[key].toLowerCase() === value.toLowerCase()) {
        return true;
      }
    } else {
      return false;
    }
  });

  if (arrayItems.length > 1) {
    //Multiple entries for same item, need to check that attribute values are the same for all.
    const __ret = findMismatchInArray(arrayItems, checkAttributes);
    finalItem = __ret.finalItem;
    misMatchFound = __ret.misMatchFound;
  } else {
    //Only a single entry with this item no need to check.
    finalItem = arrayItems[0];
  }

  if (misMatchFound) {
    return null;
  } else {
    return finalItem;
  }
}

function extractImportedRecordKeysForSchema(importData: any[], schemaName: string) {
  const schemaShortName = schemaName === "application" ? "app" : schemaName;
  //Populate distinct records from data import for each schema, referenced by _name or _id attribute.
  const tempDistinct = [
    ...new Set(
      importData.map((x) => {
        if ("__schema" in x && schemaName !== x.__schema) {
          return;
        } else if (schemaShortName + "_id" in x) {
          return x[schemaShortName + "_id"];
        } else if ("[" + schemaName + "]" + schemaShortName + "_id" in x) {
          return x["[" + schemaName + "]" + schemaShortName + "_id"];
        } else if (schemaShortName + "_name" in x) {
          return x[schemaShortName + "_name"];
        } else if ("[" + schemaName + "]" + schemaShortName + "_name" in x) {
          return x["[" + schemaName + "]" + schemaShortName + "_name"];
        }
      })
    ),
  ];

  let cleanRecords = tempDistinct.filter((item) => {
    return item !== undefined && item !== "";
  });

  if (cleanRecords === undefined) {
    //If nothing returned then continue to next schema.
    cleanRecords = [];
  }

  return cleanRecords;
}

function isValidKeyValue(
  importItem: { [x: string]: string },
  keyAttribute: any,
  importedRecordKeyValue: any,
  schemaName: string
) {
  if ("__schema" in importItem && importItem.__schema !== schemaName) {
    return false;
  } else if (importItem[keyAttribute.import_raw_header]) {
    if (importItem[keyAttribute.import_raw_header].toLowerCase() === importedRecordKeyValue.toLowerCase()) {
      return true;
    }
  } else {
    return false;
  }
}

export function addImportRowValuesToImportSummaryRecord(
  schemaName: string,
  attribute: { import_raw_header: string; attribute: { type: string; listMultiSelect: any; name: string } },
  importRow: { [x: string]: any; hasOwnProperty: (arg0: any) => any },
  importRecord: { [x: string]: any },
  dataAll: Record<string, any>
) {
  if (
    importRow?.hasOwnProperty(attribute.import_raw_header) &&
    attribute.attribute.type !== "relationship" &&
    attribute.attribute.type !== "multivalue-relationship"
  ) {
    switch (attribute.attribute.type) {
      case "list": {
        if (attribute.attribute.listMultiSelect) {
          //Build array for multiselect attribute.
          let formattedText = importRow[attribute.import_raw_header];
          formattedText = formattedText.split(";");

          importRecord[attribute.attribute.name] = formattedText;
        } else {
          importRecord[attribute.attribute.name] = importRow[attribute.import_raw_header];
        }
        break;
      }
      case "multivalue-string": {
        let formattedText = importRow[attribute.import_raw_header];
        formattedText = formattedText.split(";");

        importRecord[attribute.attribute.name] = formattedText;
        break;
      }
      case "tag": {
        const formattedTags = importRow[attribute.import_raw_header];

        importRecord[attribute.attribute.name] = parseTagsString(formattedTags);
        break;
      }
      case "checkbox": {
        const formattedText = importRow[attribute.import_raw_header];
        const regex = /^\s*(true|1|on)\s*$/i;
        importRecord[attribute.attribute.name] = regex.test(formattedText);
        break;
      }
      default: {
        importRecord[attribute.attribute.name] = importRow[attribute.import_raw_header];
      }
    }
  } else if (attribute.attribute.type === "relationship" || attribute.attribute.type === "multivalue-relationship") {
    addRelationshipValueToImportSummaryRecord(attribute, schemaName, importRow, importRecord, dataAll);
  }
}

function parseTagsString(tagsDelimitedString: string) {
  if (tagsDelimitedString.endsWith(";")) {
    // Remove any trailing semicolon as may have been added by user.
    tagsDelimitedString = tagsDelimitedString.substring(0, tagsDelimitedString.length - 1);
    // If tagsDelimitedString string is now empty no tags defined, return empty array.
    if (tagsDelimitedString === "") {
      return [];
    }
  }

  const formattedTags = tagsDelimitedString.split(";");
  return formattedTags.map((tag: string) => {
    const key_value = tag.split("=");
    return { key: key_value[0], value: key_value[1] };
  });
}

function addImportedRecordExistingToSummaryChangedItems(
  { item, item_id, item_name }: { item: any; item_id: EntityId; item_name: any },
  changesItem: Record<string, any>,
  { schema, schemaName, tempSchemaName }: { schema: EntitySchema; schemaName: string; tempSchemaName: string },
  changesItemWithCalc: Record<string, any>,
  summaryResults: Record<string, any>,
  importDataRow: {
    [p: string]: { [p: string]: { attribute: string; error: string }[] };
  }
) {
  //Create a temporary item that has all updates and validate.
  const newItem = Object.assign({}, item);

  //Update temp object with changes.
  const keys = Object.keys(changesItem);
  for (const key of keys) {
    newItem[key] = changesItem[key];
  }
  const check = checkValidItemCreate(newItem, schema);

  //Add appid to item.
  if (check === null) {
    changesItemWithCalc[tempSchemaName + "_id"] = item_id;
    if (!changesItemWithCalc?.hasOwnProperty(tempSchemaName + "_name")) {
      changesItemWithCalc[tempSchemaName + "_name"] = item_name;
    }
    summaryResults.entities[schemaName].Update.push(changesItemWithCalc);
    summaryResults.hasUpdates = true;
  } else {
    //Errors found on requirements check, log errors against data row.

    for (const error of check) {
      importDataRow["__validation"]["errors"].push({
        attribute: error.name,
        error: "Missing required " + schemaName + " attribute: " + error.name,
      });
    }
  }
}

function addImportedRecordExistingToSummary(
  schemaRec: { schema: EntitySchema; schemaName: string },
  keyAttribute: { attribute: { name: string } },
  keyAttributeValue: string,
  importedRecord: {},
  summaryResults: Record<string, any>,
  importDataRow: { [x: string]: { [x: string]: { attribute: string; error: string }[] } },
  dataAll: Record<string, any>
) {
  const { schema, schemaName } = schemaRec;
  const tempSchemaName = schemaName === "application" ? "app" : schemaName;

  let item_id = "";
  let item_name = null;
  const entityName = normalizeEntityName(schemaName);
  const item = dataAll[entityName].data.find((dataItem: { [x: string]: string }) => {
    if (dataItem[keyAttribute.attribute.name]) {
      if (dataItem[keyAttribute.attribute.name].toLowerCase() === keyAttributeValue.toLowerCase()) {
        return true;
      }
    }
  });

  if (item) {
    item_id = item[tempSchemaName + "_id"];
    item_name = item[tempSchemaName + "_name"];
  }

  const changesItemWithCalc = getChanges(importedRecord, dataAll[entityName].data, keyAttribute.attribute.name, true)!;
  const changesItem = getChanges(importedRecord, dataAll[entityName].data, keyAttribute.attribute.name, false);

  if (changesItem) {
    addImportedRecordExistingToSummaryChangedItems(
      { item, item_id, item_name },
      changesItem,
      { schema, schemaName, tempSchemaName },
      changesItemWithCalc,
      summaryResults,
      importDataRow
    );
  } else {
    const noChangeItem: Record<string, any> = {};
    noChangeItem[tempSchemaName + "_name"] = item_name;
    summaryResults.entities[schemaName].NoChange.push(noChangeItem);
  }
}

function getInvalidAttrsPerAttr(attr: Attribute | (Attribute & { conditions: unknown }), item: any) {
  const invalidAttributes: any[] = [];
  if (attr.required) {
    //Attribute is required.
    if (attr.name in item) {
      if (!(item[attr.name] !== "" && item[attr.name] !== undefined && item[attr.name] !== null)) {
        invalidAttributes.push(attr);
      }
    } else {
      //key not in item, missing required attribute.
      invalidAttributes.push(attr);
    }
  } else if ("conditions" in attr) {
    if (checkAttributeRequiredConditions(item, attr.conditions).required) {
      if (!(item[attr.name] !== "" && item[attr.name] !== undefined && item[attr.name] !== null)) {
        invalidAttributes.push(attr);
      }
    }
  }
  return invalidAttributes;
}

//Function checks the item passed has valid data as per the schema requirements.
function checkValidItemCreate(item: any, schema: EntitySchema) {
  const requiredAttributes = getRequiredAttributes(schema, true);

  const invalidAttributes: any[] = [];

  for (const attr of requiredAttributes) {
    invalidAttributes.push(...getInvalidAttrsPerAttr(attr, item));
  }

  if (invalidAttributes.length > 0) {
    return invalidAttributes;
  } else {
    return null;
  }
}

function extractRelatedItem(
  dataAll: Record<string, any>,
  importedAttribute: {
    import_raw_header: string;
    attribute: any;
  },
  importRow: { [p: string]: any; hasOwnProperty?: (arg0: any) => any }
) {
  const entityName = normalizeEntityName(importedAttribute.attribute.rel_entity);
  return dataAll[entityName].data.find((item: { [x: string]: string }) => {
    if (item[importedAttribute.attribute.rel_display_attribute] && importRow[importedAttribute.import_raw_header]) {
      if (
        item[importedAttribute.attribute.rel_display_attribute].toLowerCase() ===
        importRow[importedAttribute.import_raw_header].toLowerCase()
      ) {
        return true;
      }
    }
  });
}

function addRelationshipValueToImportSummaryRecordTypeName(
  importedAttribute: { import_raw_header: string; attribute: any },
  importRow: {
    [p: string]: any;
    hasOwnProperty?: (arg0: any) => any;
  },
  importSummaryRecord: { [p: string]: any },
  dataAll: Record<string, any>
) {
  if (importedAttribute.attribute.listMultiSelect && importRow[importedAttribute.import_raw_header]) {
    extractRelationshipList(
      importRow[importedAttribute.import_raw_header],
      importedAttribute,
      importSummaryRecord,
      dataAll
    );
  } else if (importedAttribute.attribute.listMultiSelect && importRow[importedAttribute.attribute.name]) {
    extractRelationshipList(
      importRow[importedAttribute.attribute.name],
      importedAttribute,
      importSummaryRecord,
      dataAll
    );
  } else {
    //Not a multiselect relational value.
    const relatedItem = extractRelatedItem(dataAll, importedAttribute, importRow);
    if (relatedItem) {
      importSummaryRecord[importedAttribute.attribute.name] = relatedItem[importedAttribute.attribute.rel_key];
    } else {
      if (
        importRow[importedAttribute.import_raw_header] !== "" &&
        importRow[importedAttribute.import_raw_header] !== undefined
      ) {
        //Item name does not exist, so will be created if provided. Setting ID to 'tbc', once the related
        // record is created then this will be updated in the commit with the new records' ID.
        importSummaryRecord[importedAttribute.attribute.name] = "tbc";
        importSummaryRecord["__" + importedAttribute.attribute.name] = importRow[importedAttribute.import_raw_header];
      }
    }
  }
}

function addRelationshipValueToImportSummaryRecordTypeId(
  importRow: { [p: string]: any; hasOwnProperty?: (arg0: any) => any },
  importedAttribute: {
    import_raw_header: string;
    attribute: any;
  },
  importSummaryRecord: { [p: string]: any }
) {
  if (
    importRow[importedAttribute.import_raw_header] !== "" &&
    importRow[importedAttribute.import_raw_header] !== undefined
  ) {
    //ID is being provided instead of display value.
    if (importedAttribute.attribute.listMultiSelect) {
      importSummaryRecord[importedAttribute.attribute.name] = importRow[importedAttribute.import_raw_header].split(";");
    } else {
      importSummaryRecord[importedAttribute.attribute.name] = importRow[importedAttribute.import_raw_header];
    }
  }
}

export function addRelationshipValueToImportSummaryRecord(
  importedAttribute: { import_raw_header: string; attribute: any },
  schemaName: string,
  importRow: { [x: string]: any; hasOwnProperty?: (arg0: any) => any },
  importSummaryRecord: { [x: string]: any },
  dataAll: Record<string, any>
) {
  const relationshipValueType = getRelationshipValueType(importedAttribute, schemaName);

  if (relationshipValueType === "name") {
    //relationship value is a name not ID, perform search to see if this item exists.
    addRelationshipValueToImportSummaryRecordTypeName(importedAttribute, importRow, importSummaryRecord, dataAll);
  } else if (relationshipValueType === "id") {
    //related attribute display value not present in import, ID has been provided.
    addRelationshipValueToImportSummaryRecordTypeId(importRow, importedAttribute, importSummaryRecord);
  } else {
    console.error("UNHANDLED: relationship type not found.");
  }
}

export function getRelationshipValueType(
  importedAttribute: {
    import_raw_header: string;
    attribute: { rel_display_attribute: string; name: string; listMultiSelect: any };
  },
  schemaName: string
) {
  if (
    importedAttribute.import_raw_header ===
    ("[" + schemaName + "]" + importedAttribute.attribute.rel_display_attribute).toLowerCase()
  ) {
    return "name";
  } else if (
    importedAttribute.import_raw_header.toLowerCase() ===
    importedAttribute.attribute.rel_display_attribute.toLowerCase()
  ) {
    return "name";
  } else if (
    importedAttribute.import_raw_header.toLowerCase() === importedAttribute.attribute.name.toLowerCase() &&
    importedAttribute.attribute.listMultiSelect
  ) {
    return "name";
  } else if (
    importedAttribute.import_raw_header.toLowerCase() ===
      ("[" + schemaName + "]" + importedAttribute.attribute.name).toLowerCase() &&
    importedAttribute.attribute.listMultiSelect
  ) {
    return "name";
  } else if (importedAttribute.import_raw_header.toLowerCase() === importedAttribute.attribute.name.toLowerCase()) {
    return "id";
  } else if (
    importedAttribute.import_raw_header.toLowerCase() ===
    ("[" + schemaName + "]" + importedAttribute.attribute.name).toLowerCase()
  ) {
    return "id";
  }
}

function extractValueIdAndDisplay(
  dataAll: Record<string, any>,
  importedAttribute: {
    attribute: {
      rel_entity: string;
      rel_display_attribute: string;
      rel_key: string;
      name: string;
    };
  },
  itemValue: string,
  valuesID: any[],
  valuesDisplay: any[],
  importValueDelimitedStringList: string
) {
  const entityName = normalizeEntityName(importedAttribute.attribute.rel_entity);
  const relatedItem = dataAll[entityName].data.find((item: { [x: string]: string }) => {
    if (item[importedAttribute.attribute.rel_display_attribute] && itemValue) {
      if (item[importedAttribute.attribute.rel_display_attribute].toLowerCase() === itemValue.toLowerCase()) {
        return true;
      }
    }
  });
  if (relatedItem) {
    valuesID.push(relatedItem[importedAttribute.attribute.rel_key]);
    valuesDisplay.push(relatedItem[importedAttribute.attribute.rel_display_attribute]);
  } else {
    if (importValueDelimitedStringList !== "" && importValueDelimitedStringList !== undefined) {
      //Item name does not exist so will be created if provided.
      valuesID.push("tbc");
      valuesDisplay.push(itemValue);
    }
  }
}

function extractRelationshipList(
  importValueDelimitedStringList: string | undefined,
  importedAttribute: {
    attribute: {
      rel_entity: string;
      rel_display_attribute: string;
      rel_key: string;
      name: string;
    };
  },
  importSummaryRecord: { [x: string]: any[] },
  dataAll: Record<string, any>
) {
  //Multiselect attribute.
  // Nothing to process if importValueDelimitedStringList is empty string so return.
  if (!importValueDelimitedStringList) {
    return;
  }
  const valuesRaw = importValueDelimitedStringList.split(";");
  const valuesID: any[] = [];
  const valuesDisplay: any[] = [];

  if (valuesRaw.length > 0) {
    for (const itemValue of valuesRaw) {
      extractValueIdAndDisplay(
        dataAll,
        importedAttribute,
        itemValue,
        valuesID,
        valuesDisplay,
        importValueDelimitedStringList
      );
    }

    importSummaryRecord[importedAttribute.attribute.name] = valuesID;
    importSummaryRecord["__" + importedAttribute.attribute.name] = valuesDisplay;
  } else {
    //No values provided.
    importSummaryRecord[importedAttribute.attribute.name] = [];
  }
}

function addImportedRecordCreateToSummary(
  schema: EntitySchema,
  schemaName: string,
  keyAttribute: { attribute: { name: string } },
  keyAttributeValue: any,
  importedRecord: { [x: string]: string | null },
  summaryResults: { entities: any; hasUpdates: any },
  importDataRow: { [x: string]: { [x: string]: { attribute: string; error: string }[] } }
) {
  //1. Get required schema attributes for this entity type.
  //2. check returned required attributes against the list of attributes supplied in attributeMappings.
  //3. if there are missing required attributes add an error to the record/row.
  //4. recheck that values have been provided for all required attributes. Add errors to record/row if they do not have values.
  //5. Do not add to Create array.
  // Note: this check might need to be done with updates to once the ability to clear values is implemented.

  //Check the entity is valid, i.e. it has the user key defined, if not, do not add as this is not something the user is looking to create.

  if (keyAttribute.attribute.name in importedRecord && importedRecord[keyAttribute.attribute.name] !== "") {
    const check = checkValidItemCreate(importedRecord, schema);

    if (check === null) {
      //No errors on item add to create array.
      summaryResults.entities[schemaName].Create.push(importedRecord);
      summaryResults.hasUpdates = true;
    } else {
      //Errors found on requirements check, log errors against data row.
      for (const error of check) {
        importDataRow["__validation"]["errors"].push({
          attribute: error.name,
          error: "Missing required " + schemaName + " attribute: " + error.name,
        });
      }
    }
  } else {
    //Name not provided.
    console.log("_name not provided.");
  }
}

function filterOutHiddenAttributes(schemas: Record<string, EntitySchema>, schema_name: string) {
  return schemas[schema_name].attributes.filter((attr: Attribute) => {
    if (!attr.hidden) {
      attr.schema = schemas[schema_name].schema_name === "app" ? "application" : schemas[schema_name].schema_name;
      return attr;
    }
  });
}

export function getAllAttributes(schemas: Record<string, EntitySchema>) {
  const all_attributes: Attribute[] = [];
  if (schemas) {
    for (const schema_name in schemas) {
      if (schemas[schema_name].schema_type === "user") {
        const nonHiddenAttributes = filterOutHiddenAttributes(schemas, schema_name);
        all_attributes.push(...nonHiddenAttributes);
      }
    }
  }
  return all_attributes;
}

export function getRequiredAttributesAllSchemas(schemas: Record<string, EntitySchema>): Attribute[] {
  if (!schemas) return [];

  return Object.values(schemas).flatMap((schema) => {
    return schema.schema_type === "user" ? getRequiredAttributes(schema) : [];
  });
}

export function exportAllTemplate(schemas: Record<string, EntitySchema>) {
  const ws_data: Record<string, any> = {};

  const attributes = getAllAttributes(schemas); // get all required attributes from all schemas

  const headers: Record<string, any> = {};
  for (const attr_idx in attributes) {
    if (attributes[attr_idx].type === "relationship") {
      headers["[" + attributes[attr_idx].schema + "]" + attributes[attr_idx].rel_display_attribute] = attributes[
        attr_idx
      ].sample_data_intake
        ? attributes[attr_idx].sample_data_intake
        : "";
    } else {
      headers["[" + attributes[attr_idx].schema + "]" + attributes[attr_idx].name] = attributes[attr_idx]
        .sample_data_intake
        ? attributes[attr_idx].sample_data_intake
        : "";
    }
  }

  const json_output = [headers]; // Create single item array with empty values to populate headers fdr intake form.

  const range = { s: { c: 0, r: 0 }, e: { c: attributes.length, r: 1 } }; // set worksheet cell range
  ws_data["!ref"] = XLSX.utils.encode_range(range);

  const wb = XLSX.utils.book_new(); // create new workbook
  wb.SheetNames.push("mf_intake"); // create new worksheet
  wb.Sheets["mf_intake"] = XLSX.utils.json_to_sheet(json_output); // load headers array into worksheet

  XLSX.writeFile(wb, "cmf-intake-form-all.xlsx"); // export to user

  console.log("CMF intake template exported.");
}

export function removeCalculatedKeyValues(item: { [x: string]: any }) {
  for (const key in item) {
    if (key.startsWith("__")) {
      delete item[key];
    }
  }
}

export function removeTbcValues(item: { [x: string]: any }) {
  for (const key in item) {
    if (item.hasOwnProperty(key)) {
      const value = item[key];

      // Handle string values
      if (typeof value === "string" && value === "tbc") {
        delete item[key];
      }
      // Handle array values
      else if (Array.isArray(value)) {
        // Filter out "tbc" values from arrays
        const filteredArray = value.filter((v) => v !== "tbc");
        if (filteredArray.length === 0) {
          // If array becomes empty after filtering, remove the property
          delete item[key];
        } else if (filteredArray.length !== value.length) {
          // If we removed some "tbc" values, update the array
          item[key] = filteredArray;
        }
      } else if (typeof value === "object" && value !== null && !Array.isArray(value)) {
        removeTbcValues(value); // Recursively process nested objects
      }
    }
  }
}

function updateRelatedMultiListAttr(item: any, attr: Attribute, newItem: Record<string, any>) {
  if (item["__" + attr.name] && (!item[attr.name] || item[attr.name].includes("tbc"))) {
    const relatedNamesIDs = item[attr.name];
    const relatedNames = item["__" + attr.name];
    let hasUpdates = false;

    //For each related name update the tbc values with new items ID.
    for (let relNameIdx = 0; relNameIdx < relatedNamesIDs.length; relNameIdx++) {
      const relatedName = relatedNames[relNameIdx];
      const newItemName = newItem[attr.rel_display_attribute!];

      if (relatedName && newItemName && relatedName.toLowerCase() === newItemName.toLowerCase()) {
        relatedNamesIDs[relNameIdx] = newItem[attr.rel_key!];
        hasUpdates = true;
      }
    }

    if (hasUpdates) {
      item[attr.name] = relatedNamesIDs;

      // Check if all items in the list have been resolved (no more "tbc" values)
      const hasUnresolvedItems = relatedNamesIDs.some((id: string) => id === "tbc");

      if (!hasUnresolvedItems) {
        // All items resolved, remove the __ attribute
        delete item["__" + attr.name];
      }
    }
  }
}

function updateRelatedSelectAttr(item: any, attr: Attribute, newItem: Record<string, any>) {
  if ((!item[attr.name] || item[attr.name] === "tbc") && item["__" + attr.name]) {
    if (item["__" + attr.name].toLowerCase() === newItem[attr.rel_display_attribute!].toLowerCase()) {
      item[attr.rel_key!] = newItem[attr.rel_key!];
      delete item["__" + attr.name];
    }
  }
}

export function updateRelatedItemAttributes(
  schemas: Record<string, EntitySchema>,
  newItem: Record<string, any> | null,
  new_item_schema_name: string,
  related_items: any[],
  related_schema_name: string,
  keyAttributeName?: string
) {
  const new_item_schema_name_shortname = new_item_schema_name === "application" ? "app" : new_item_schema_name;

  if (!schemas[new_item_schema_name]) {
    console.debug("Invalid new_item_schema_name: " + new_item_schema_name);
    return;
  }

  if (!schemas[related_schema_name]) {
    console.debug("Invalid related_schema_name: " + related_schema_name);
    return;
  }

  if (!related_items || related_items.length === 0) {
    console.debug("No related_items to update in items: " + related_schema_name);
    return;
  }

  if (!newItem) {
    console.debug("No new item to reference.");
    return;
  }

  // Log the key attribute being used for debugging
  if (keyAttributeName) {
    console.debug(`Using key attribute: ${keyAttributeName} for ${new_item_schema_name} item`);
  }

  //get all relationship attributes for related items' schema.
  const rel_attributes = schemas[related_schema_name].attributes.filter((attr) => {
    return (
      (attr.type === "relationship" || attr.type === "multivalue-relationship") &&
      attr.rel_entity === new_item_schema_name_shortname
    );
  });

  console.debug(
    `Found ${rel_attributes.length} relationship attributes in ${related_schema_name} that reference ${new_item_schema_name}`
  );

  //Update items with new items ids for created item.
  for (const item of related_items) {
    for (const attr of rel_attributes) {
      if (attr.listMultiSelect) {
        //Deal with multiple related items. This only currently supports names not IDs.
        updateRelatedMultiListAttr(item, attr, newItem);
      } else {
        //Update single select items.
        updateRelatedSelectAttr(item, attr, newItem);
      }
    }
  }
}

export function buildCommitExceptionNotification(
  exception: { response: { data?: { cause?: string; errors?: any } } },
  schema: any,
  schema_shortname: string,
  currentItem: { [x: string]: string }
) {
  const currentItemElement = currentItem[schema_shortname + "_name"];
  const exceptionData = exception.response?.data;
  if (exceptionData) {
    const cause = exceptionData.cause ?? JSON.stringify(exceptionData.errors ?? exceptionData);
    return {
      itemType: schema,
      error: currentItemElement ? `${currentItemElement} - ${cause}` : cause,
      item: currentItem,
    };
  } else {
    return {
      itemType: schema,
      error: currentItemElement ? currentItemElement + " - Unknown error occurred" : "Unknown error occurred",
      item: currentItem,
    };
  }
}

export function captureItemsBeforeUpdate(items: any[], schemaName: string): Map<string, any> {
  const itemMap = new Map<string, any>();
  const schemaShortname = schemaName === "application" ? "app" : schemaName;

  for (const item of items) {
    // Create a unique key for the item (using ID or name)
    const itemId = item[schemaShortname + "_id"];
    const itemName = item[schemaShortname + "_name"];
    const key = itemId || itemName;

    if (key) {
      // Deep clone the item to capture its state before updates
      itemMap.set(key, JSON.parse(JSON.stringify(item)));
    }
  }

  return itemMap;
}

export function detectChangesInItems(
  beforeItems: Map<string, any>,
  afterItems: any[],
  schemaName: string
): Array<{ item: any; schema: string }> {
  const changedItems: Array<{ item: any; schema: string }> = [];
  const schemaShortname = schemaName === "application" ? "app" : schemaName;

  for (const afterItem of afterItems) {
    const itemId = afterItem[schemaShortname + "_id"];
    const itemName = afterItem[schemaShortname + "_name"];
    const key = itemId || itemName;

    if (key && beforeItems.has(key)) {
      const beforeItem = beforeItems.get(key);
      const itemChanges: Record<string, any> = {};
      let hasChanges = false;

      // Compare before and after to detect actual changes
      for (const prop in afterItem) {
        if (prop.startsWith("__")) continue; // Skip metadata

        if (beforeItem[prop] !== afterItem[prop]) {
          itemChanges[prop] = afterItem[prop];
          hasChanges = true;
        }
      }

      if (hasChanges && itemId) {
        changedItems.push({
          item: { ...itemChanges, [schemaShortname + "_id"]: itemId },
          schema: schemaShortname,
        });
      }
    }
  }

  return changedItems;
}

export async function saveChangedItemsBulk(
  changedItems: Array<{ item: any; schema: string }>,
  apiUser: UserApiClient,
  notification: CompletionNotification,
  loutputCommit: any[]
) {
  // Group changes by schema for more efficient processing
  const changesBySchema = new Map<string, Array<{ item: any; schema: string }>>();

  for (const changedItem of changedItems) {
    const { schema } = changedItem;
    if (!changesBySchema.has(schema)) {
      changesBySchema.set(schema, []);
    }
    changesBySchema.get(schema)!.push(changedItem);
  }

  // Process each schema's changes in parallel
  const updatePromises = Array.from(changesBySchema.entries()).map(async ([schema, items]) => {
    console.debug(`Bulk updating ${items.length} ${schema} items with related changes`);

    // Process items in batches to avoid overwhelming the server
    const batchSize = 10; // Adjust batch size as needed
    const batches = [];
    for (let i = 0; i < items.length; i += batchSize) {
      batches.push(items.slice(i, i + batchSize));
    }

    for (const batch of batches) {
      const batchPromises = batch.map(async ({ item, schema }) => {
        try {
          const itemId = item[schema + "_id"];
          const updateData = { ...item };
          delete updateData[schema + "_id"]; // Remove ID from update payload

          await apiUser.putItem(itemId, updateData, schema);
          console.debug(`Successfully updated ${schema} item ${itemId}`);
        } catch (e: any) {
          console.error(`Failed to update ${schema} item:`, e);
          loutputCommit.push(buildCommitExceptionNotification(e, schema, schema, item));
        }
      });

      // Wait for current batch to complete before starting next batch
      await Promise.all(batchPromises);
    }
  });

  // Wait for all schema updates to complete
  await Promise.all(updatePromises);
}

export async function updateAllRelationships(
  allNewItems: any[],
  dataImport: { [p: string]: { Create: any[]; Update: any[] } },
  schemas: Record<string, EntitySchema>,
  notification: CompletionNotification,
  updateUploadStatus: (notification: CompletionNotification, message: string, numberRecords?: number) => void,
  outputCommitErrors: any[],
  commitErrors: any[]
) {
  console.debug("Starting final relationship update pass for all items");

  updateUploadStatus(notification, "Updating all relationships...", 0);

  // Capture the state of all items before any relationship updates
  const beforeUpdateState = new Map<string, Map<string, any>>();
  for (const schemaName in dataImport) {
    beforeUpdateState.set(schemaName + "_Create", captureItemsBeforeUpdate(dataImport[schemaName].Create, schemaName));
    beforeUpdateState.set(schemaName + "_Update", captureItemsBeforeUpdate(dataImport[schemaName].Update, schemaName));
  }

  // Update relationships for all newly created items
  console.debug("Processing", allNewItems.length, "newly created items for relationship updates");

  for (const newItem of allNewItems) {
    // Use the schemaName that was added during creation
    const newItemSchema = newItem.__schemaName;

    if (newItemSchema) {
      const schemaShortname = newItemSchema === "application" ? "app" : newItemSchema;
      const keyAttributeName = schemaShortname + "_id";
      const itemName = newItem[schemaShortname + "_name"];
      const itemId = newItem[schemaShortname + "_id"];
      console.debug(
        `Processing ${newItemSchema}: "${itemName}" (ID: ${itemId}) with key attribute: ${keyAttributeName}`
      );

      // Update relationships in all other schemas that might reference this new item
      for (const updateSchema in dataImport) {
        console.debug(`  Checking ${updateSchema} items for references to ${newItemSchema}:${itemName}`);
        updateRelatedItemAttributes(
          schemas,
          newItem,
          newItemSchema,
          dataImport[updateSchema].Create,
          updateSchema,
          keyAttributeName
        );
        updateRelatedItemAttributes(
          schemas,
          newItem,
          newItemSchema,
          dataImport[updateSchema].Update,
          updateSchema,
          keyAttributeName
        );
      }
    } else {
      console.warn("Could not determine schema for new item:", newItem);
    }
  }

  // Collect all changes that were made
  const allChangedItems: Array<{ item: any; schema: string }> = [];
  for (const schemaName in dataImport) {
    const beforeCreate = beforeUpdateState.get(schemaName + "_Create")!;
    const beforeUpdate = beforeUpdateState.get(schemaName + "_Update")!;

    allChangedItems.push(...detectChangesInItems(beforeCreate, dataImport[schemaName].Create, schemaName));
    allChangedItems.push(...detectChangesInItems(beforeUpdate, dataImport[schemaName].Update, schemaName));
  }

  // Send all updates in one bulk operation
  if (allChangedItems.length > 0) {
    console.debug(`Sending ${allChangedItems.length} relationship updates in bulk`);
    const apiUser = new UserApiClient();
    const loutputCommit: any[] = [];
    await saveChangedItemsBulk(allChangedItems, apiUser, notification, loutputCommit);

    if (loutputCommit.length > 0) {
      commitErrors.push(...loutputCommit);
      commitErrors.push(...outputCommitErrors);
    }
  }

  updateUploadStatus(notification, "Relationship updates completed", 0);
}

/**
 * Fetches all items for each schema type and returns them organized by entity type.
 */
export const getAllItemsBySchemaType = async (
  entityTypes: string[],
  apiUser: UserApiClient
): Promise<Map<string, Record<string, unknown>[]>> => {
  const itemsBySchema = new Map<string, Record<string, unknown>[]>();

  for (const entityType of entityTypes) {
    const apiEntityType = entityType === "application" ? "app" : entityType;
    try {
      const allItems = await apiUser.getItems(apiEntityType);
      itemsBySchema.set(apiEntityType, allItems);
    } catch (error) {
      console.log(`Error fetching items for ${entityType}:`, error);
      itemsBySchema.set(apiEntityType, []);
    }
  }

  return itemsBySchema;
};
