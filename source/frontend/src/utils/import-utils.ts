/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import * as XLSX from "xlsx";
import { getChanges, validateTags, validateValue } from "../resources/main";
import { Attribute, EntitySchema } from "../models/EntitySchema";
import { checkAttributeRequiredConditions, getRequiredAttributes } from "../resources/recordFunctions";

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
    for (let key in dataItem) {
      if (dataItem[key] === null || dataItem[key] === "") {
        delete dataItem[key];
      }
    }
  }
  return dataJson;
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
  let data = await readXLSXFile(reader, selectedFile);
  let workbook = XLSX.read(data);
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
  let list = value.split(";");
  for (let item in list) {
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
  let mvlist = value.split(";");
  for (let item in mvlist) {
    const currError = validateValue(mvlist[item], attribute.attribute);
    errorMsg = currError ? currError : errorMsg;
  }
  return errorMsg;
}

function getSchemaAttribute(attributeName: string, schema: EntitySchema) {
  let attr = null;

  for (let attribute of schema.attributes) {
    if (attribute.name === attributeName) {
      attr = attribute;
      break;
    }
  }

  return attr;
}

function getSchemaRelationshipAttributes(attributeName: string | undefined, schema: EntitySchema) {
  let attributes = [];

  for (let attribute of schema.attributes) {
    if (attribute.type === "relationship") {
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
  let attributeMappings: any[] = [];
  let schemaNames: string[] = [];

  for (let [itemIdx, item] of csvData.entries()) {
    let itemErrors: any[] = [];
    let itemWarnings: any[] = [];
    let itemInformational: any[] = [];
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
    let keySplit = key.split("]");
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

    let filterMappings = attributeMappings.filter((item) =>
      item["import_raw_header"] === key ? item["schema_name"] === foundAttr.schema_name : false
    );

    if (filterMappings.length === 0) {
      attributeMappings.push(foundAttr);
    }

    //Add schema names to list for quick lookup later.
    if (foundAttr.attribute && !schemaNames.includes(foundAttr.schema_name)) {
      schemaNames.push(foundAttr.schema_name);
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
  let itemOrMismatch = isMismatchedItem(
    dataJson.data,
    schemaAttributes,
    keyAttribute.import_raw_header,
    importedRecordKeyValue.toLowerCase()
  );
  if (itemOrMismatch !== null) {
    let importRow = dataJson.data.find((importItem: { [x: string]: string }) =>
      isValidKeyValue(importItem, keyAttribute, importedRecordKeyValue)
    );

    let importRecord: Record<string, any> = {};
    importRecord[keyAttribute.attribute.name] = importedRecordKeyValue;

    for (const attr of schemaAttributes) {
      addImportRowValuesToImportSummaryRecord(schemaName, attr, importRow, importRecord, dataAll);
    }

    if (
      dataAll[schemaName].data.some(
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
  let distinct: Record<string, any> = {};

  let result: { attributeMappings: any[]; entities: Record<string, any>; hasUpdates: boolean } = {
    entities: {} as Record<string, any>,
    hasUpdates: false,
    attributeMappings: [],
  };

  for (const schemaName in schemas) {
    if (schemas[schemaName].schema_type === "user") {
      let temp_schema_name = schemaName === "application" ? "app" : schemaName;
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
        return attr.schema_name === schemaName;
      });

      let keyAttribute = schemaAttributes.find((attr: { attribute: { name: string } }) => {
        //Get schema key attribute.
        if (attr.attribute.name === temp_schema_name + "_name" || attr.attribute.name === temp_schema_name + "_id") {
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
  let finalItem = arrayItems[0]; //set to first element as if not mismatched we with return this record.
  for (const attr of checkAttributes) {
    //For each attribute in this import for the same schema check that it is consistent.
    let distinctValue = [
      ...new Set(
        arrayItems.map((x) => {
          if (attr.attribute.type === "relationship") {
            return x[attr.attribute.rel_display_attribute];
          } else {
            return x[attr.attribute.name];
          }
        })
      ),
    ];

    if (distinctValue.length > 1) {
      //Problem found, update validation for all items with this item value.
      for (let itemValue in arrayItems) {
        arrayItems[itemValue].__validation.errors.push({
          attribute: attr.attribute.name,
          error: attr.attribute.description + " cannot be different for the same " + attr.schema_name + ".",
        });
        misMatchFound = true;
      }
    }
  }
  return { finalItem, misMatchFound };
}

export function isMismatchedItem(dataArray: any[], checkAttributes: any[], key: any, value: any) {
  let misMatchFound = false;
  let finalItem = null;

  let arrayItems = dataArray.filter((item) => {
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
  let tempSchemaName = schemaName === "application" ? "app" : schemaName;
  //Populate distinct records from data import for each schema, referenced by _name or _id attribute.
  const tempDistinct = [
    ...new Set(
      importData.map((x) => {
        if (tempSchemaName + "_id" in x) {
          return x[tempSchemaName + "_id"];
        } else if ("[" + schemaName + "]" + tempSchemaName + "_id" in x) {
          return x["[" + schemaName + "]" + tempSchemaName + "_id"];
        } else if (tempSchemaName + "_name" in x) {
          return x[tempSchemaName + "_name"];
        } else if ("[" + schemaName + "]" + tempSchemaName + "_name" in x) {
          return x["[" + schemaName + "]" + tempSchemaName + "_name"];
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

function isValidKeyValue(importItem: { [x: string]: string }, keyAttribute: any, importedRecordKeyValue: any) {
  if (importItem[keyAttribute.import_raw_header]) {
    if (importItem[keyAttribute.import_raw_header].toLowerCase() === importedRecordKeyValue.toLowerCase()) {
      return true;
    }
  } else {
    return false;
  }
}

export function addImportRowValuesToImportSummaryRecord(
  schemaName: string,
  attribute: { import_raw_header: string; attribute: { type: string; listMultiSelect: any; name: string | number } },
  importRow: { [x: string]: any; hasOwnProperty: (arg0: any) => any },
  importRecord: { [x: string]: any },
  dataAll: Record<string, any>
) {
  if (importRow?.hasOwnProperty(attribute.import_raw_header) && attribute.attribute.type !== "relationship") {
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
        let formattedTags = importRow[attribute.import_raw_header];

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
  } else if (attribute.attribute.type === "relationship") {
    addRelationshipValueToImportSummaryRecord(attribute, schemaName, importRow, importRecord, dataAll);
  }
}

function parseTagsString(tagsDelimitedString: string) {

  if (tagsDelimitedString.endsWith(';')) {
    // Remove any trailing semicolon as may have been added by user.
    tagsDelimitedString = tagsDelimitedString.substring(0,tagsDelimitedString.length-1);
    // If tagsDelimitedString string is now empty no tags defined, return empty array.
    if (tagsDelimitedString === ''){
      return []
    }
  }

  let formattedTags = tagsDelimitedString.split(";");
  return formattedTags.map((tag: string) => {
    let key_value = tag.split("=");
    return { key: key_value[0], value: key_value[1] };
  });
}

function addImportedRecordExistingToSummaryChangedItems(
  { item, item_id, item_name }: { item: any; item_id: number; item_name: any },
  changesItem: Record<string, any>,
  { schema, schemaName, tempSchemaName }: { schema: EntitySchema; schemaName: string; tempSchemaName: string },
  changesItemWithCalc: Record<string, any>,
  summaryResults: Record<string, any>,
  importDataRow: {
    [p: string]: { [p: string]: { attribute: string; error: string }[] };
  }
) {
  //Create a temporary item that has all updates and validate.
  let newItem = Object.assign({}, item);

  //Update temp object with changes.
  const keys = Object.keys(changesItem);
  for (let key of keys) {
    newItem[key] = changesItem[key];
  }
  let check = checkValidItemCreate(newItem, schema);

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

  let item_id = -1;
  let item_name = null;
  let item = dataAll[schemaName].data.find((dataItem: { [x: string]: string }) => {
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

  let changesItemWithCalc = getChanges(importedRecord, dataAll[schemaName].data, keyAttribute.attribute.name, true)!;
  let changesItem = getChanges(importedRecord, dataAll[schemaName].data, keyAttribute.attribute.name, false);

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
    let noChangeItem: Record<string, any> = {};
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
  return dataAll[importedAttribute.attribute.rel_entity].data.find((item: { [x: string]: string }) => {
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
      rel_entity: string | number;
      rel_display_attribute: string | number;
      rel_key: string | number;
      name: string;
    };
  },
  itemValue: string,
  valuesID: any[],
  valuesDisplay: any[],
  importValueDelimitedStringList: string
) {
  let relatedItem = dataAll[importedAttribute.attribute.rel_entity].data.find((item: { [x: string]: string }) => {
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
      rel_entity: string | number;
      rel_display_attribute: string | number;
      rel_key: string | number;
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
    let check = checkValidItemCreate(importedRecord, schema);

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
        let nonHiddenAttributes = filterOutHiddenAttributes(schemas, schema_name);
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
  let ws_data: Record<string, any> = {};

  let attributes = getAllAttributes(schemas); // get all required attributes from all schemas

  let headers: Record<string, any> = {};
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

  let range = { s: { c: 0, r: 0 }, e: { c: attributes.length, r: 1 } }; // set worksheet cell range
  ws_data["!ref"] = XLSX.utils.encode_range(range);

  let wb = XLSX.utils.book_new(); // create new workbook
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

function updateRelatedMultiListAttr(item: any, attr: Attribute, newItem: Record<string, any>) {
  if (item["__" + attr.name] && (!item[attr.name] || item[attr.name].includes("tbc"))) {
    let relatedNamesIDs = item[attr.name];
    let relatedNames = item["__" + attr.name];

    //For each related name update the tbc values with new items ID.
    for (let relNameIdx = 0; relNameIdx < relatedNamesIDs.length; relNameIdx++) {
      if (relatedNamesIDs[relNameIdx] === "tbc") {
        //check if this is a record to update.
        if (relatedNames[relNameIdx].toLowerCase() === newItem[attr.rel_display_attribute!].toLowerCase()) {
          relatedNamesIDs[relNameIdx] = newItem[attr.rel_key!];
        }
      }
    }
    item[attr.name] = relatedNamesIDs;
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
  related_schema_name: string
) {
  if (!schemas[new_item_schema_name]) {
    console.debug("Invalid new_item_schema_name" + new_item_schema_name);
    return;
  }

  if (!schemas[related_schema_name]) {
    console.debug("Invalid related_schema_name" + related_schema_name);
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

  //get all relationship attributes for related items' schema.
  const rel_attributes = schemas[related_schema_name].attributes.filter((attr) => {
    return attr.type === "relationship" && attr.rel_entity === new_item_schema_name;
  });

  //Update items with new items ids for created item.
  for (let item of related_items) {
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
