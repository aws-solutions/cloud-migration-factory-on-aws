// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Functions declared in this module are for generic factory functionality.
 */

/**
 * Compares the provided newItem object to the object based in the dataArray of the matching key, returning the difference.
 * @param newItem
 * @param dataArray
 * @param key
 * @param keepCalculated - all keys which start with __ will be ignored by default, if set to true they will not be evaluated but returned to the output.
 * @returns {{}|null}
 */
export function getChanges(newItem, dataArray, key, keepCalculated = false) {

  let update: Record<string, any> = {};

  let currentItem = dataArray.find(item => {
    if (item[key].toLowerCase() === newItem[key].toLowerCase()) {
        return true;
      }
    }
  )

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

/**
 * Performs a deep comparison of 2 objects based on keys and values, returning true if they are identical and false if not.
 * @param object1
 * @param object2
 * @returns {boolean}
 */
export function deepEqual(object1, object2) {

  if ((!object1 && object2) || (object1 && !object2)) {
    //if either undefined  return false.
    return false;
  }

  if ((object1 == null && object2 != null) || (object1 != null && object2 == null)) {
    //if either undefined  return false.
    return false;
  } else if (object1 == null && object2 == null) {
    // both are null.
    return true;
  }

  const keys1 = Object.keys(object1);
  const keys2 = Object.keys(object2);

  if (keys1.length !== keys2.length) {
    return false;
  }

  for (const key of keys1) {
    const val1 = object1[key];
    const val2 = object2[key];
    const areObjects = isObject(val1) && isObject(val2);
    if ((areObjects && !deepEqual(val1, val2)) || (!areObjects && val1 !== val2)) {
      return false;
    }
  }

  return true;
}

/**
 * Checks if variable passed is of type object.
 * @param object
 * @returns {boolean}
 */
function isObject(object) {
  return object != null && typeof object === 'object';
}

/**
 * Resolves all relation key/values in the mainData records with related display values from relatedData.
 * @param relatedData
 * @param mainData
 * @param mainDataSchema
 * @returns {*}
 */
export function resolveRelationshipValues(relatedData, mainData, mainDataSchema) {
  let lMainData = mainData;

  let attributesWithRelations = mainDataSchema.attributes.filter(function (entry) {
    return entry.type === 'relationship' || entry.type === 'policies';
  })

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
        arrName[arrName.length - 1] = '__' + arrName[arrName.length - 1];
        let newName = arrName.join(".");

        if (lRel_Value.status === 'loaded') {
          setNestedValuePath(lMainDataItem, newName, lRel_Value.value);
        } else if (lRel_Value.status === 'not found') {
          setNestedValuePath(lMainDataItem,
            newName,
            ` [ERROR: ${attributesWithRelationsItem.rel_key} (${lRel_Value.value}) not found in ${attributesWithRelationsItem.rel_entity} table]`);
        } else {
          setNestedValuePath(lMainDataItem, newName, lRel_Value.value + ' [resolving...]');
        }

      }
    }
  }

  let attributesWithTags = mainDataSchema.attributes.filter(function (entry) {
    return entry.type === 'tag';
  })

  for (const attributesWithTagsItem of attributesWithTags) {
    for (const lMainDataItem of lMainData) {
      if (propExists(lMainDataItem, attributesWithTagsItem.name)) {
        //Update last element in key name with __ to reflect names that are path based.
        let arrName = attributesWithTagsItem.name.split(".");
        arrName[arrName.length - 1] = '__' + arrName[arrName.length - 1];
        let newName = arrName.join(".");

        let value = getNestedValuePath(lMainDataItem, attributesWithTagsItem.name);

        let lRel_Value = value.map((tag) => {
          return tag.key + '=' + tag.value
        }).join(';');
        setNestedValuePath(lMainDataItem, newName, lRel_Value.value);
      }
    }
  }

  return lMainData;
}

/**
 * Resolves a relationship key value to the display value.
 * @param relatedData
 * @param attribute
 * @param value
 * @returns {{value, status: string}|{value: *, status: string}|{value: null, status: string}|{value: string, status: string}|{value: *[], status: string}|{value: null, status: string}}
 */
function getRelationshipValue(relatedData, attribute, value) {
  if (!relatedData[attribute.rel_entity]) {
    return {status: 'error', value: '[' + value + '] ' + attribute.rel_entity + ' entity was not provided in related data.'}

  }

  if (relatedData[attribute.rel_entity].isLoading)
    return {status: 'loading', value: value};
  else {
    let record = undefined;
    //For policies this is an array of objects that needs special processing.
    if (attribute.type === 'policies') {
      record = relatedData[attribute.rel_entity].data.filter(item => {
        for (const listItem of value) {
            if (item[attribute.rel_key] === listItem['policy_id']) {
              return true;
            }
          }
        }
      )
    } else if (Array.isArray(value)) {
      // Multiselect relationship value.
      record = relatedData[attribute.rel_entity].data.filter(item => {
        for (const listItem of value) {
            if (item[attribute.rel_key] === listItem) {
              return true;
            }
          }
        }
      )
    } else {
      record = relatedData[attribute.rel_entity].data.find(item => {
          if (item[attribute.rel_key].toLowerCase() === value.toLowerCase()) {
            return true;
          }
        }
      )
    }

    if (record && attribute.type !== 'policies') {
      return record[attribute.rel_display_attribute] ? {
        status: 'loaded',
        value: record[attribute.rel_display_attribute]
      } : {status: 'loaded', value: null};
    } else if (record && (attribute.type === 'policies' || (attribute.type === 'relationship' && attribute.listMultiSelect))) {
      let returnArray = [];
      for (const item of record) {
        if (item[attribute.rel_display_attribute]) {
          returnArray.push(item[attribute.rel_display_attribute])
        }
      }

      return returnArray.length > 0 ? {status: 'loaded', value: returnArray} : {status: 'loaded', value: null};
    } else {
      return {status: 'not found', value: value};
    }
  }

}

/**
 * Validates the value passed against the attributes' value validation, these could be listvalues, regex, required.
 * @param value
 * @param attribute
 * @returns {null}
 */
export function validateValue(value, attribute) {

  const stdError = "Error in validation, please check entered value.";
  let errorMsg = null;

  //Validate valuelist.
  if (attribute.type === 'list' && (value !== '' && value !== undefined && value !== null)) {
    //Check value is matching list item.
    if (attribute.listvalue) {
      let attrListValues = attribute.listvalue.split(',');
      let foundAll = null;

      for (let itemIdx = 0; itemIdx < attrListValues.length; itemIdx++) {
        if (attrListValues[itemIdx].toLowerCase() === value.toLowerCase()) {
          foundAll = true;
        }
      }

      if (!foundAll) {
        errorMsg = 'Value entered is invalid, ' + 'possible values are: ' + attribute.listvalue + '.';
      }
    }
  }

  //Validate regex.
  if (attribute.validation_regex && attribute.validation_regex !== '' && (value !== '' && value !== undefined && value !== null)) {
    if (!value.match(attribute.validation_regex)) {
      //Validation error
      if (attribute.validation_regex_msg) {
        errorMsg = attribute.validation_regex_msg;
      } else {
        errorMsg = stdError
      }
    }
  }

  return errorMsg;

}

/**
 * Gets a key value from the obj, based on the optional arguments being passed providing the keys to traverse, each arg is a key level.
 * @param obj
 * @param args
 * @returns {*}
 */
export function getNestedValue(obj, ...args) {
  return args.reduce((obj, level) => obj && obj[level], obj)
}

/**
 * Gets a key value from the obj based on passing a period delimited path to the key/value required.
 * @param obj
 * @param path
 * @returns {undefined|*}
 */
export function getNestedValuePath(obj, path) {
  if (path) {
    return path.split(".").reduce((obj, pathElement) => obj && obj[pathElement], obj)
  } else {
    return undefined;
  }

}

/**
 * Sets a key value from the obj based on passing a period delimited path to the key/value required.
 * @param obj
 * @param path
 * @param value
 */
export function setNestedValuePath(obj, path, value) {
  let parts = path.split('.');
  let o = obj;
  let o_arr = [];
  if (parts.length > 1) {
    for (let i = 0; i < parts.length - 1; i++) {
      if (!o[parts[i]])
        if (parts[parts.length - 1] === '+1' && i === parts.length - 2) {
          o[parts[i]] = [];
        } else {
          o[parts[i]] = {};
        }

      o = o[parts[i]];
      o_arr.push(o);
    }
  }
  if (value === undefined) {
    if (Array.isArray(o_arr[parts.length - 2])) {
      o_arr[parts.length - 2].splice(parts[parts.length - 1], 1);
      if (o_arr[parts.length - 2].length === 0) {
        //Array now empty, remove key.
        delete o[parts[parts.length - 2]]
      }
    } else {
      delete o[parts[parts.length - 1]]
    }
  } else if (parts[parts.length - 1] === '+1') {
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
export const propExists = (obj, path) => {
  return !!path.split('.').reduce((obj, prop) => {
    return obj && obj[prop] ? obj[prop] : undefined;
  }, obj)
}

/**
 * Sort comparator function used for all item table configurations.
 * @param a
 * @param b
 * @returns {number|number}
 */
export function sortAscendingComparator(a, b) {

  if (typeof a === "string" && typeof b === "string") {
    if (a === b) {
      return 0;
    }
    return a.localeCompare(b);
  }
  if (typeof a === "number" && typeof b === "number") {
    if (a === b) {
      return 0;
    }
    return a > b ? 1 : -1;
  }
  if (typeof a === "boolean" && typeof b === "boolean") {
    if (a === b) {
      return 0;
    }
    return a === true ? 1 : -1;
  }
  if (a instanceof Date && b instanceof Date) {
    if (a.getTime() === b.getTime()) {
      return 0;
    }
    return a.getTime() > b.getTime() ? 1 : -1;
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
export function returnLocaleDateTime(stringDateTime, returnObject = false) {

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
export const toBase64 = file => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onload = () => resolve(reader.result);
  reader.onerror = error => reject(error);
});

/**
 * Capitalizes the first letter of the s parameter.
 * @constructor
 * @param {string} s - The string to capitalize.
 * @returns {string} Returns the capitalized version of param s.
 */
export const capitalize = s => (s && s[0].toUpperCase() + s.slice(1)) || ""

/**
 * Provides the options list for actions drop-down menus.
 * @param schema - provide all schemas, these will be filtered by the function.
 * @param userEntityAccess
 * @returns {*[]}
 */
export function userAutomationActionsMenuItems(schema, userEntityAccess) {

  let items = [];

  for (const schema_name in schema) {

    if (schema[schema_name].schema_type === 'automation') {
      //Only add automations that have at least one action, defined. This allows for other automation schemas to be stored.
      if (schema[schema_name].actions.length > 0) {

        if (schema[schema_name].group) {
          //Has groups
          let group = items.filter(function (item) {
            return item.id === schema[schema_name].group && item.items;
          });

          if (group.length === 0) {
            items.push({
              id: schema[schema_name].group,
              text: schema[schema_name].group,
              items: [{
                id: schema[schema_name].schema_name,
                text: schema[schema_name].friendly_name,
                description: schema[schema_name].description,
                disabled: userEntityAccess[schema_name] ? !userEntityAccess[schema_name].create : true
              }]
            });
          } else {
            group[0].items.push({
              id: schema[schema_name].schema_name,
              text: schema[schema_name].friendly_name,
              description: schema[schema_name].description,
              disabled: userEntityAccess[schema_name] ? !userEntityAccess[schema_name].create : true
            })
          }
        } else {
          items.push({
            id: schema[schema_name].schema_name,
            text: schema[schema_name].friendly_name,
            description: schema[schema_name].description,
            disabled: userEntityAccess[schema_name] ? !userEntityAccess[schema_name].create : true
          });
        }
      }
    }
  }


  return items;
}
