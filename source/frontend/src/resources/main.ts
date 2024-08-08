/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Functions declared in this module are for generic factory functionality.
 */

import { Attribute, EntitySchema } from "../models/EntitySchema";
import { UserAccess } from "../models/UserAccess";
import { ButtonDropdownProps } from "@awsui/components-react";

/**
 * Compares the provided newItem object to the object based in the dataArray of the matching key, returning the difference.
 * @param newItem
 * @param dataArray
 * @param key
 * @param keepCalculated - all keys which start with __ will be ignored by default, if set to true they will not be evaluated but returned to the output.
 * @returns {{}|null}
 */
export function getChanges(newItem: any, dataArray: any[], key: string, keepCalculated = false) {
  let update: Record<string, any> = {};

  let currentItem = dataArray.find((item) => {
    if (item[key].toLowerCase() === newItem[key].toLowerCase()) {
      return true;
    }
  });

  // Compare the selected server to the original server list and extract key values that are different
  const keys = Object.keys(newItem);
  for (const i in keys) {
    const curkey = keys[i];
    //Ignore any system calculated values as these are never stored in database.
    if (!curkey.startsWith("_")) {
      if (!deepEqual(currentItem[curkey], newItem[curkey])) {
        update[curkey] = newItem[curkey];
      }
    } else if (curkey.startsWith("__") && keepCalculated) {
      //Just add calculated items, as maybe required for other functions.
      update[curkey] = newItem[curkey];
    }
  }
  if (Object.keys(update).length === 0) {
    return null;
  } else {
    return update;
  }
}

type ComparableObject = object | null | undefined;

/**
 * Performs a deep comparison of 2 objects based on keys and values, returning true if they are identical and false if not.
 * @param object1
 * @param object2
 * @returns {boolean}
 */
export function deepEqual(object1: ComparableObject, object2: ComparableObject) {
  // this is just to get the complexity of this function below 15
  const simpleEquality = simpleCompare(object1, object2);
  if (simpleEquality !== EqualityType.NotKnown) return simpleEquality === EqualityType.Equal;

  const keys1 = Object.keys(<object>object1);
  const keys2 = Object.keys(<object>object2);

  if (keys1.length !== keys2.length) {
    return false;
  }

  for (const key of keys1) {
    const val1 = (<any>object1)[key];
    const val2 = (<any>object2)[key];
    const areObjects = isObject(val1) && isObject(val2);
    if ((areObjects && !deepEqual(val1, val2)) || (!areObjects && val1 !== val2)) {
      return false;
    }
  }

  return true;
}

enum EqualityType {
  Equal = "EQUAL",
  NotEqual = "NOT_EQUAL",
  NotKnown = "NOT_KNOWN",
}

function simpleCompare(object1: ComparableObject, object2: ComparableObject): EqualityType {
  if ((!object1 && object2) || (object1 && !object2)) {
    //if either undefined  return false.
    return EqualityType.NotEqual;
  }

  if ((object1 == null && object2 != null) || (object1 != null && object2 == null)) {
    //if either undefined  return false.
    return EqualityType.NotEqual;
  } else if (object1 == null && object2 == null) {
    // both are null.
    return EqualityType.Equal;
  }
  return EqualityType.NotKnown;
}

/**
 * Checks if variable passed is of type object.
 * @param object
 * @returns {boolean}
 */
function isObject(object: any) {
  return object != null && typeof object === "object";
}

function resolveRelationshipValuesForRelationsAndPolicies(
  attributesWithRelations: Attribute[],
  lMainData: readonly any[],
  relatedData: any
) {
  for (const attributesWithRelationsItem of attributesWithRelations) {
    for (const lMainDataItem of lMainData) {
      if (propExists(lMainDataItem, attributesWithRelationsItem.name)) {
        let lRel_Value = getRelationshipValue(
          relatedData,
          attributesWithRelationsItem,
          getNestedValuePath(lMainDataItem, attributesWithRelationsItem.name)
        );

        //Update last element in key name with __ to reflect names that are path based.
        let arrName = attributesWithRelationsItem.name.split(".");
        arrName[arrName.length - 1] = "__" + arrName[arrName.length - 1];
        let newName = arrName.join(".");

        if (lRel_Value.status === "loaded") {
          setNestedValuePath(lMainDataItem, newName, lRel_Value.value);
        } else if (lRel_Value.status === "not found") {
          setNestedValuePath(
            lMainDataItem,
            newName,
            ` [ERROR: ${attributesWithRelationsItem.rel_key} (${lRel_Value.value}) not found in ${attributesWithRelationsItem.rel_entity} table]`
          );
        } else {
          setNestedValuePath(lMainDataItem, newName, lRel_Value.value + " [resolving...]");
        }
      }
    }
  }
}

function resolveRelationshipValuesForTags(attributesWithTags: Attribute[], lMainData: readonly any[]) {
  for (const attributesWithTagsItem of attributesWithTags) {
    for (const lMainDataItem of lMainData) {
      if (propExists(lMainDataItem, attributesWithTagsItem.name)) {
        //Update last element in key name with __ to reflect names that are path based.
        let arrName = attributesWithTagsItem.name.split(".");
        arrName[arrName.length - 1] = "__" + arrName[arrName.length - 1];
        let newName = arrName.join(".");

        let value = getNestedValuePath(lMainDataItem, attributesWithTagsItem.name);

        let lRel_Value = value
          .map((tag: { key: string; value: string }) => {
            return tag.key + "=" + tag.value;
          })
          .join(";");
        setNestedValuePath(lMainDataItem, newName, lRel_Value.value);
      }
    }
  }
}

/**
 * Resolves all relation key/values in the mainData records with related display values from relatedData.
 * @param relatedData
 * @param mainData
 * @param mainDataSchema
 * @returns {*}
 */
export function resolveRelationshipValues(relatedData: any, mainData: readonly any[], mainDataSchema: EntitySchema) {
  let lMainData = mainData;

  let attributesWithRelations = mainDataSchema.attributes.filter(function (entry) {
    return entry.type === "relationship" || entry.type === "policies";
  });
  resolveRelationshipValuesForRelationsAndPolicies(attributesWithRelations, lMainData, relatedData);

  let attributesWithTags = mainDataSchema.attributes.filter(function (entry) {
    return entry.type === "tag";
  });
  resolveRelationshipValuesForTags(attributesWithTags, lMainData);

  return lMainData;
}

function getMatchingPolicyRecord(relatedData: any, attribute: Attribute, value: any) {
  return relatedData[attribute.rel_entity!].data.filter((item: any) => {
    for (const listItem of value) {
      if (item[attribute.rel_key!] === listItem["policy_id"]) {
        return true;
      }
    }
  });
}

function getMatchingListItemRecord(relatedData: any, attribute: Attribute, value: any) {
  return relatedData[attribute.rel_entity!].data.filter((item: any) => {
    for (const listItem of value) {
      if (item[attribute.rel_key!] === listItem) {
        return true;
      }
    }
  });
}

function getDefaultMatchingRecord(relatedData: any, attribute: Attribute, value: any) {
  return relatedData[attribute.rel_entity!].data.find((item: any) => {
    if (item[attribute.rel_key!].toLowerCase() === value.toLowerCase()) {
      return true;
    }
  });
}

function getRelationshipValueFromMatchingRecord(record: any, attribute: Attribute, value: any) {
  if (attribute.type !== "policies") {
    return record[attribute.rel_display_attribute!]
      ? {
          status: "loaded",
          value: record[attribute.rel_display_attribute!],
        }
      : { status: "loaded", value: null };
  } else if (attribute.type === "policies" || (attribute.type === "relationship" && attribute.listMultiSelect)) {
    let returnArray = [];
    for (const item of record) {
      if (item[attribute.rel_display_attribute!]) {
        returnArray.push(item[attribute.rel_display_attribute!]);
      }
    }
    return returnArray.length > 0 ? { status: "loaded", value: returnArray } : { status: "loaded", value: null };
  } else {
    return { status: "not found", value: value };
  }
}

/**
 * Resolves a relationship key value to the display value.
 * @param relatedData
 * @param attribute
 * @param value
 * @returns {{value, status: string}|{value: *, status: string}|{value: null, status: string}|{value: string, status: string}|{value: *[], status: string}|{value: null, status: string}}
 */
function getRelationshipValue(relatedData: any, attribute: Attribute, value: any) {
  if (!relatedData[attribute.rel_entity!]) {
    return {
      status: "error",
      value: "[" + value + "] " + attribute.rel_entity + " entity was not provided in related data.",
    };
  }

  if (relatedData[attribute.rel_entity!].isLoading) return { status: "loading", value: value };
  else {
    let record = undefined;
    //For policies this is an array of objects that needs special processing.
    if (attribute.type === "policies") {
      record = getMatchingPolicyRecord(relatedData, attribute, value);
    } else if (Array.isArray(value)) {
      // Multiselect relationship value.
      record = getMatchingListItemRecord(relatedData, attribute, value);
    } else {
      record = getDefaultMatchingRecord(relatedData, attribute, value);
    }
    if (record) return getRelationshipValueFromMatchingRecord(record, attribute, value);
    else return { status: "not found", value: value };
  }
}

function validateValueList(
  attribute: {
    type: any;
    validation_regex?: any;
    validation_regex_msg?: any;
    listvalue?: any;
  },
  value: string,
  errorMsg: string | null
) {
  if (attribute.listvalue) {
    let attrListValues = attribute.listvalue.split(",");
    let foundAll = null;

    for (const attrListValue of attrListValues) {
      if (attrListValue.toLowerCase() === value.toLowerCase()) {
        foundAll = true;
      }
    }

    if (!foundAll) {
      errorMsg = "Value entered is invalid, " + "possible values are: " + attribute.listvalue + ".";
    }
  }
  return errorMsg;
}

function validateRegEx(
  value: string,
  attribute: {
    type: any;
    validation_regex?: any;
    validation_regex_msg?: any;
    listvalue?: any;
  },
  errorMsg: string | null,
  stdError: string
) {
  if (!value.match(attribute.validation_regex)) {
    //Validation error
    if (attribute.validation_regex_msg) {
      errorMsg = attribute.validation_regex_msg;
    } else {
      errorMsg = stdError;
    }
  }
  return errorMsg;
}

/**
 * Validates the value passed against the attributes' value validation, these could be listvalues, regex, required.
 * @param value
 * @param attribute
 * @returns {null}
 */
export function validateValue(
  value: string,
  attribute: {
    type: any;
    validation_regex?: any;
    validation_regex_msg?: any;
    listvalue?: any;
  }
) {
  const stdError = "Error in validation, please check entered value.";
  let errorMsg = null;

  //Validate valuelist.
  if (attribute.type === "list" && value !== "" && value !== undefined && value !== null) {
    //Check value is matching list item.
    errorMsg = validateValueList(attribute, value, errorMsg);
  }

  //Validate regex.
  if (
    attribute.validation_regex &&
    attribute.validation_regex !== "" &&
    value !== "" &&
    value !== undefined &&
    value !== null
  ) {
    errorMsg = validateRegEx(value, attribute, errorMsg, stdError);
  }

  return errorMsg;
}

/**
 * Gets a key value from the obj, based on the optional arguments being passed providing the keys to traverse, each arg is a key level.
 * @param obj
 * @param args
 * @returns {*}
 */
export function getNestedValue(obj: any, ...args: string[]) {
  return args.reduce((obj, level) => obj && obj[level], obj);
}

/**
 * Gets a key value from the obj based on passing a period delimited path to the key/value required.
 * @param obj
 * @param path
 * @returns {undefined|*}
 */
export function getNestedValuePath(obj: any, path: string) {
  if (path) {
    return path.split(".").reduce((obj, pathElement) => obj && obj[pathElement], obj);
  } else {
    return undefined;
  }
}

function setNestedValuePathToUndefined(o_arr: any[], parts: string[], o: any) {
  if (Array.isArray(o_arr[parts.length - 2])) {
    o_arr[parts.length - 2].splice(parts[parts.length - 1], 1);
    if (o_arr[parts.length - 2].length === 0) {
      //Array now empty, remove key.
      delete o[parts[parts.length - 2]];
    }
  } else {
    delete o[parts[parts.length - 1]];
  }
}

/**
 * Sets a key value from the obj based on passing a period delimited path to the key/value required.
 * @param obj
 * @param path
 * @param value
 */
export function setNestedValuePath(obj: any, path: string, value: any) {
  let parts = path.split(".");
  let o = obj;
  let o_arr = [];
  if (parts.length > 1) {
    for (let i = 0; i < parts.length - 1; i++) {
      if (!o[parts[i]])
        if (parts[parts.length - 1] === "+1" && i === parts.length - 2) {
          o[parts[i]] = [];
        } else {
          o[parts[i]] = {};
        }

      o = o[parts[i]];
      o_arr.push(o);
    }
  }
  if (value === undefined) {
    setNestedValuePathToUndefined(o_arr, parts, o);
  } else if (parts[parts.length - 1] === "+1") {
    o_arr[parts.length - 2].push(value);
  } else {
    o[parts[parts.length - 1]] = value;
  }
}

/**
 * Checks if a key exists based on passing a period delimited path to the key/value required.
 * @param obj
 * @param path
 * @returns {boolean}
 */
export const propExists = (obj: any, path: string) => {
  return !!path.split(".").reduce((obj, prop) => {
    return obj && obj[prop] ? obj[prop] : undefined;
  }, obj);
};

function stringCompare(a: string, b: string) {
  if (a === b) {
    return 0;
  }
  return a.localeCompare(b);
}

function numberCompare(a: number, b: number) {
  if (a === b) {
    return 0;
  }
  return a > b ? 1 : -1;
}

function booleanCompare(a: boolean, b: boolean) {
  if (a === b) {
    return 0;
  }
  return a === true ? 1 : -1;
}

function compareDate(a: Date, b: Date) {
  if (a.getTime() === b.getTime()) {
    return 0;
  }
  return a.getTime() > b.getTime() ? 1 : -1;
}

/**
 * Sort comparator function used for all item table configurations.
 * @param a
 * @param b
 * @returns {number|number}
 */
export function sortAscendingComparator(a: any, b: any) {
  if (typeof a === "string" && typeof b === "string") {
    return stringCompare(a, b);
  }
  if (typeof a === "number" && typeof b === "number") {
    return numberCompare(a, b);
  }
  if (typeof a === "boolean" && typeof b === "boolean") {
    return booleanCompare(a, b);
  }
  if (a instanceof Date && b instanceof Date) {
    return compareDate(a, b);
  }
  const aUndefined = a === undefined;
  const bUndefined = b === undefined;
  if (aUndefined && bUndefined) {
    return 0;
  }
  if (aUndefined) {
    return 1;
  }
  if (bUndefined) {
    return -1;
  }
  return 0;
}

/**
 * Returns a localized date/time string.
 * @param stringDateTime
 * @param returnObject
 * @returns {Date|string|undefined}
 */
export function returnLocaleDateTime(stringDateTime: string, returnObject = false) {
  if (stringDateTime === null || stringDateTime === undefined) {
    return undefined;
  }

  let originalDate = new Date(stringDateTime);
  let newDate = new Date(originalDate.getTime() - originalDate.getTimezoneOffset() * 60 * 1000);

  if (returnObject) {
    return newDate;
  } else {
    return newDate.toLocaleString();
  }
}

/**
 * returns a file encoded as base64.
 * @param file
 * @returns {Promise<unknown>}
 */
export const toBase64 = (file: File) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });

/**
 * Capitalizes the first letter of the s parameter.
 * @constructor
 * @param {string} s - The string to capitalize.
 * @returns {string} Returns the capitalized version of param s.
 */
export const capitalize = (s: string) => (s && s[0].toUpperCase() + s.slice(1)) || "";

function extracted(
  existingItems: any[],
  schemas: Record<string, EntitySchema>,
  schema_name: string,
  userEntityAccess: UserAccess
) {
  const items: any[] = [];
  if (schemas[schema_name].group) {
    //Has groups
    let group = existingItems.filter(function (item) {
      return item.id === schemas[schema_name].group && item.items;
    });

    if (group.length === 0) {
      items.push({
        id: schemas[schema_name].group,
        text: schemas[schema_name].group,
        items: [
          {
            id: schemas[schema_name].schema_name,
            text: schemas[schema_name].friendly_name,
            description: schemas[schema_name].description,
            disabled: userEntityAccess[schema_name] ? !userEntityAccess[schema_name].create : true,
          },
        ],
      });
    } else {
      group[0].items!.push({
        id: schemas[schema_name].schema_name,
        text: schemas[schema_name].friendly_name,
        description: schemas[schema_name].description,
        disabled: userEntityAccess[schema_name] ? !userEntityAccess[schema_name].create : true,
      });
    }
  } else {
    items.push({
      id: schemas[schema_name].schema_name,
      text: schemas[schema_name].friendly_name,
      description: schemas[schema_name].description,
      disabled: userEntityAccess[schema_name] ? !userEntityAccess[schema_name].create : true,
    });
  }
  return items;
}

/**
 * Provides the options list for actions drop-down menus.
 * @param schemas - provide all schemas, these will be filtered by the function.
 * @param userEntityAccess
 * @returns {*[]}
 */
export function userAutomationActionsMenuItems(schemas: Record<string, EntitySchema>, userEntityAccess: UserAccess) {
  const items: ButtonDropdownProps.ItemOrGroup[] = [];
  for (const schema_name in schemas) {
    if (schemas[schema_name].schema_type === "automation") {
      //Only add automations that have at least one action, defined. This allows for other automation schemas to be stored.
      if (schemas[schema_name].actions!.length > 0) {
        items.push(...extracted(items, schemas, schema_name, userEntityAccess));
      }
    }
  }
  return items;
}
