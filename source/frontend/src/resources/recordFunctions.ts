// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {getNestedValuePath} from "./main";


function isEqualsQueryTrue(query, item){
  if (item[query.attribute] && query.value){ //Check this condition has ability to provide outcome.
    //Attribute exists.
    return item[query.attribute] === query.value;
  }
}

function isNotEqualsQueryTrue(query, item){
  if (item[query.attribute] && query.value) { //Check this condition has ability to provide outcome.
    //Attribute exists.
    return item[query.attribute] !== query.value;
  }
}

function isNotEmptyQueryTrue(query, item){
  if (query.attribute in item) { //Check this condition has ability to provide outcome.
    //Attribute exists.
    if (Array.isArray(item[query.attribute])) {
      return item[query.attribute].length !== 0
    } else {
      //Not an array check value
      return item[query.attribute] !== '' && item[query.attribute] !== false;
    }
  } else {
    return false;
  }
}

function isEmptyQueryTrue(query, item){
  if (query.attribute in item) { //Check this condition has ability to provide outcome.
    //Attribute exists.

    if (Array.isArray(item[query.attribute])) {
      return item[query.attribute].length > 0;
    } else {
      //Not an array check value
      return item[query.attribute] === '' || item[query.attribute] === false;
    }
  } else {
      return true;
  }
}


function evaluateQueryCondition(query, item){
  let queryResult = null;

  switch (query.comparator){
    case '=':
      queryResult = isEqualsQueryTrue(query, item);
      break;
    case '!=':
      queryResult = isNotEqualsQueryTrue(query, item);
      break;
    case '!empty':
      queryResult = isNotEmptyQueryTrue(query, item);
      break;
    case 'empty':
      queryResult = isEmptyQueryTrue(query, item);
      break;
    default:
      break;
  }

  return queryResult;
}

function isRequiredOutcome(outcomes, type){
  if (type in outcomes) {
    for (const outcome of outcomes[type]) {
      switch (outcome) {
        case 'required':
          return true;
        case 'not_required':
          return false;
        default:
          break;
      }
    }
  }

  return null;
}

function isHiddenOutcome(outcomes, type){
  if (type in outcomes) {
    for (const outcome of outcomes[type]) {
      switch (outcome) {
        case 'hidden':
          return true;
        case 'not_hidden':
          return false;
        default:
          break;
      }
    }
  }

  return null;
}

export function checkAttributeRequiredConditions(item, conditions){
  let returnRequired = null;
  let returnHidden = null;

  if (!conditions){
    //No conditions passed.
    return {'required': returnRequired, 'hidden': returnHidden};
  }

  let queryResult = null;

  for (const query of conditions.queries){
    queryResult = evaluateQueryCondition(query,item);
  }

  //Evaluate true outcomes.
  if (queryResult) {
    returnHidden = isHiddenOutcome(conditions.outcomes,'true');
    returnRequired = isRequiredOutcome(conditions.outcomes,'true')
  } else if (queryResult !== null) {
    returnHidden = isHiddenOutcome(conditions.outcomes,'false');
    returnRequired = isRequiredOutcome(conditions.outcomes,'false')
  }

  return {'required': returnRequired, 'hidden': returnHidden};

}

function isAttributeRequired(attribute, schema, includeConditional){
  let schemaKeyAttributeName = schema.schema_name === 'application' ? 'app_id' : schema.schema_name +'_id';

  if (attribute.required && !attribute.hidden && attribute.name !== schemaKeyAttributeName) {
    attribute.schema = schema.schema_name === 'app' ? 'application' : schema.schema_name;
    return attribute;
  } else if (attribute.conditions && includeConditional) { //does attribute have conditions defined, if yes then check if required is a possible outcome.
    if (attribute.conditions.outcomes['true'])
      return isRequiredOutcome(attribute.conditions.outcomes, 'true')
    if (attribute.conditions.outcomes['false'])
      return isRequiredOutcome(attribute.conditions.outcomes, 'false')
  }
}

export function getRequiredAttributes(schema, includeConditional = false){
  let required_attributes = [];

  if (schema) {
    required_attributes = schema.attributes.filter(attribute => isAttributeRequired(attribute, schema, includeConditional));
  }

  return required_attributes;

}

export function getRelationshipRecord (relatedData, attribute, value) {

  // Check if related data for the entity required is present in relatedData object.
  if ((relatedData?.[attribute.rel_entity]) && !(relatedData[attribute.rel_entity].isLoading || !value)){
      if (attribute.listMultiSelect) {
        // Multiselect relationship values.
        return relatedData[attribute.rel_entity].data.filter(item =>
          isItemRelationshipMatch(attribute.rel_key, item, value)
        );
      } else {
        let record = relatedData[attribute.rel_entity].data.find(item =>
          isItemRelationshipMatch(attribute.rel_key, item, [value])
        );

        if (record) {
          return record;
        } else {
          return null;
        }
      }
  } else {
    // Related data does not contain data for the required entity.
    return null;
  }
}

function isItemRelationshipMatch(relatedRecordKey, record, relationshipKeyValues){
  for (const listItem of relationshipKeyValues) {
    if (getNestedValuePath(record, relatedRecordKey).toLowerCase() === listItem.toLowerCase()) {
      return true;
    }
  }
  return false;
}

function getUnresolvedRelationships(relatedRecordKey, resolvedRelationshipRecords, relationshipKeyValues){
  let invalidRelationshipKeys = [];
  if (resolvedRelationshipRecords.length !== relationshipKeyValues.length){
    for (const relationshipKeyValue of relationshipKeyValues) {
      let foundRecord = false;
      for (const resolvedRelationshipRecord of resolvedRelationshipRecords) {
        if (getNestedValuePath(resolvedRelationshipRecord, relatedRecordKey).toLowerCase() === relationshipKeyValue.toLowerCase()) {
          foundRecord = true;
        }
      }
      if (!foundRecord) {
        invalidRelationshipKeys.push(relationshipKeyValue)
      }
    }
  }

  return invalidRelationshipKeys;
}

function getRelationshipMultiSelectDisplayValues(attribute, relatedData, relationshipKeyValues){
  // Multiselect relationships value.
  let foundRelationshipRecords = relatedData[attribute.rel_entity].data.filter(
    item => isItemRelationshipMatch(attribute.rel_key, item, relationshipKeyValues)
  )

  let resolvedDisplayValues = foundRelationshipRecords.map(item => {
    return (getNestedValuePath(item,attribute.rel_display_attribute))
  });

  let unresolvedRelationShips = getUnresolvedRelationships(attribute.rel_key, foundRelationshipRecords, relationshipKeyValues);

  return {status: 'loaded', value: resolvedDisplayValues, invalid: unresolvedRelationShips};
}

function getRelationshipSingleDisplayValue(attribute, relatedData, currentValue){
  let record = relatedData[attribute.rel_entity].data.find(item =>
    isItemRelationshipMatch(attribute.rel_key, item, [currentValue])
  );

  if (record) {
    let returnValue = null;
    if (attribute.type === 'embedded_entity')
      returnValue = getNestedValuePath(record, attribute.rel_attribute)
    else {
      returnValue = getNestedValuePath(record, attribute.rel_display_attribute)
    }

    return returnValue ? {status: 'loaded', value: returnValue} : {status: 'loaded', value: null};
  } else {
    return currentValue ? {status: 'not found', value: currentValue} : {status: 'loaded', value: null};
  }
}

export function getRelationshipValue (relatedData, attribute, value) {

  if (relatedData?.[attribute.rel_entity]) {
    //relatedData contains the related entity data to perform lookup.
    if (relatedData[attribute.rel_entity].isLoading || !value) {
      //Loading relatedData still or value empty.
      return value ? {status: 'loading', value: value} : {status: 'loaded', value: null};
    } else {
      if (attribute.listMultiSelect) {
        return getRelationshipMultiSelectDisplayValues(attribute, relatedData, value);
      } else {
        return getRelationshipSingleDisplayValue(attribute, relatedData, value);
      }
    }
  }

  // By default, return null or the original value provided. default return will only be used when other lookups
  // failed to return data.
  return value ? {status: 'not found', value: value} : {status: 'loaded', value: null};
}

function appendValidationErrors(errorList, validationErrors){
  if (validationErrors?.length > 0){
    for (const error of validationErrors){
      for (const error_detail in error){
        errorList.push(error_detail + ' : ' + error[error_detail].join());
      }
    }
  }
}

function appendExistingNameErrors(errorList, existingNameErrors){
  if (existingNameErrors?.length > 0){
    for (const error of existingNameErrors){
      errorList.push(error +  " already exists.");
    }
  }
}

export function parsePUTResponseErrors(errors){
  let errorList = [];
  //Check for validation errors.
  appendValidationErrors(errorList, errors?.validation_errors);

  //Check for duplication errors.
  appendExistingNameErrors(errorList, errors?.existing_name);

  //Check for unprocessed put errors.
  appendValidationErrors(errorList, errors?.unprocessed_items);

  // This is an array of errors.
  if (Array.isArray(errors)){
    for (const error of errors){
      if(error.cause){
        //If cause key exists populate with string.
        errorList.push(error.cause);
      } else {
        errorList.push(error);
      }

    }

  }

  return errorList;

}