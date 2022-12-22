/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {getNestedValuePath} from "./main";

export function checkAttributeRequiredConditions(item, conditions){
  let returnRequired = null;
  let returnHidden = null;

  if (!conditions){
    //No conditions passed.
    return {'required': returnRequired, 'hidden': returnHidden};
  }

  let queryResult = null;

  for (const query of conditions.queries){
    if (query.comparator === '='){
      if (item[query.attribute] && query.value){ //Check this condition has ability to provide outcome.
        //Attribute exists.
        if (item[query.attribute] === query.value){
          if (queryResult !== false) //AND the results.
            queryResult = true;
        } else {
          queryResult = false;
          break; //At least one query is false, no need to continue.
        }
      }
    } else if (query.comparator === '!=') {
      if (item[query.attribute] && query.value) { //Check this condition has ability to provide outcome.
        //Attribute exists.
        if (item[query.attribute] !== query.value) {
          if (queryResult !== false) //AND the results.
            queryResult = true;
        } else {
          queryResult = false;
          break; //At least one query is false, no need to continue.
        }
      }
    }else if (query.comparator === '!empty') {
      if (query.attribute in item) { //Check this condition has ability to provide outcome.
        //Attribute exists.
        if (Array.isArray(item[query.attribute])) {
          if (item[query.attribute].length !== 0) {
            if (queryResult !== false) //AND the results.
              queryResult = true;
          } else {
            queryResult = false;
            break; //At least one query is false, no need to continue.
          }
        } else {
          //Not an array check value
          if (item[query.attribute] !== '' && item[query.attribute] !== false) {
            if (queryResult !== false) //AND the results.
              queryResult = true;
          } else {
            queryResult = false;
            break; //At least one query is false, no need to continue.
          }
        }
      } else {
        queryResult = false;
        break; //attribute is not set.
      }
    }else if (query.comparator === 'empty') {
      if (query.attribute in item) { //Check this condition has ability to provide outcome.
        //Attribute exists.

        if (Array.isArray(item[query.attribute])) {
          if (item[query.attribute].length > 0) {
            queryResult = false;
            break; //At least one query is false, no need to continue.
          } else {
            //Empty Array.
            if (queryResult !== false) //AND the results.
              queryResult = true;
          }
        } else {
          //Not an array check value
          if (item[query.attribute] === '' || item[query.attribute] === false) {
            if (queryResult !== false) //AND the results.
              queryResult = true;
          } else {
            queryResult = false;
            break; //At least one query is false, no need to continue.
          }

        }
      } else {
        if (queryResult !== false) //AND the results.
          queryResult = true;
      }
    }
  }

  //Evaluate true outcomes.
  if (queryResult) {
    if ('true' in conditions.outcomes)
      for (const outcome of conditions.outcomes['true']) {
        switch (outcome) {
          case 'required':
            returnRequired = true;
            break;
          case 'not_required':
            returnRequired = false;
            break;
          case 'hidden':
            returnHidden = true;
            break;
          case 'not_hidden':
            returnHidden = false;
            break;
        }
      }
  } else {
    if ('false' in conditions.outcomes)
      for (const outcome of conditions.outcomes['false']) {
        switch (outcome) {
          case 'required':
            returnRequired = true;
            break;
          case 'not_required':
            returnRequired = false;
            break;
          case 'hidden':
            returnHidden = true;
            break;
          case 'not_hidden':
            returnHidden = false;
            break;
        }
      }
  }

  return {'required': returnRequired, 'hidden': returnHidden};

}

export function getRequiredAttributes(schema, includeConditional = false){
  let required_attributes = [];
  let schemaName = schema.schema_name === 'application' ? 'app_id' : schema.schema_name +'_id';

  if (schema) {
    required_attributes = schema.attributes.filter(attribute => {
      if (attribute.required && !attribute.hidden && attribute.name !== schemaName) {
        attribute.schema = schema.schema_name === 'app' ? 'application' : schema.schema_name;
        return attribute;
      } else if (attribute.conditions && includeConditional) { //does attribute have conditions defined, if yes then check if required is a possible outcome.
        if (attribute.conditions.outcomes['true'])
          for (const outcome of attribute.conditions.outcomes['true']) {
            if (outcome === 'required'){
              return attribute;
            }
          }
        if (attribute.conditions.outcomes['false'])
          for (const outcome of attribute.conditions.outcomes['false']) {
            if (outcome === 'required'){
              return attribute;
            }
          }
      }
    });
  }

  return required_attributes;

}

export function getRelationshipRecord (relatedData, attribute, value) {

  if (!relatedData) {
    return null;
  }

  // Check if related data for the entity required is present in relatedData object.
  if (relatedData[attribute.rel_entity]){
    if (relatedData[attribute.rel_entity].isLoading || !value){
      //Loading relatedData still or value empty.
      return null;
    } else {
      if (attribute.listMultiSelect) {
        // Multiselect relationship value.
        let records = relatedData[attribute.rel_entity].data.filter(item => {
            for (const listItem of value) {
              if (getNestedValuePath(item,attribute.rel_key).toLowerCase() === listItem.toLowerCase()) {
                return true;
              }
            }
          }
        )

        if (records) {
          return records;
        } else {
          return null;
        }
      } else {
        let record = relatedData[attribute.rel_entity].data.find(item => {
            if (getNestedValuePath(item,attribute.rel_key).toLowerCase() === value.toLowerCase()) {
              return true;
            }
          }
        )

        if (record) {
          return record;
        } else {
          return null;
        }
      }
    }
  } else {
    // Related data does not contain data for the required entity.
    return null;
  }
}

export function getRelationshipValue (relatedData, attribute, value) {

  if (!relatedData) {
    //No related data to lookup was provided.
    return value ? {status: 'not found', value: value} : {status: 'loaded', value: null};
  }

  if (relatedData[attribute.rel_entity]) {
    //relatedData contains the related entity data to perform lookup.
    if (relatedData[attribute.rel_entity].isLoading || !value) {
      //Loading relatedData still or value empty.
      return value ? {status: 'loading', value: value} : {status: 'loaded', value: null};
    } else {
      if (attribute.listMultiSelect) {
        // Multiselect relationship value.
        let records = relatedData[attribute.rel_entity].data.filter(item => {
            for (const listItem of value) {
              if (getNestedValuePath(item, attribute.rel_key).toLowerCase() === listItem.toLowerCase()) {
                return true;
              }
            }
          }
        )

        let returnItems = records.map(item => {
          return (getNestedValuePath(item,attribute.rel_display_attribute))
        });

        if (returnItems) {
          // Items have been returned from map function.
          return {status: 'loaded', value: returnItems};
        }
      } else {
        let record = relatedData[attribute.rel_entity].data.find(item => {
            if (getNestedValuePath(item,attribute.rel_key).toLowerCase() === value.toLowerCase()) {
              return true;
            }
          }
        )

        if (record) {
          let returnValue = null;
          if (attribute.type === 'embedded_entity')
            returnValue = getNestedValuePath(record, attribute.rel_attribute)
          else {
            returnValue = getNestedValuePath(record, attribute.rel_display_attribute)
          }

          return returnValue ? {status: 'loaded', value: returnValue} : {status: 'loaded', value: null};
        }
      }
    }
  }

  // By default, return null or the original value provided. default return will only be used when other lookups
  // failed to return data.
  return value ? {status: 'not found', value: value} : {status: 'loaded', value: null};
}

export function parsePUTResponseErrors(errors){
  let returnMessage = [];
  //Check for validation errors.
  if (errors.validation_errors && errors.validation_errors.length > 0){
    for (var error of errors.validation_errors){
      for (var error_detail in error){
        returnMessage.push(error_detail + ' : ' + error[error_detail].join());
      }
    }
  }
  //Check for duplication errors.
  if (errors.existing_name && errors.existing_name.length > 0){
    for (var error of errors.existing_name){
        returnMessage.push(error +  " already exists.");
    }
  }

  //Check for unprocessed put errors.
  if (errors.unprocessed_items && errors.unprocessed_items.length > 0){
    for (var error of errors.unprocessed_items){
      for (var error_detail in error){
        returnMessage.push(error_detail + ' : ' + error[error_detail].join());
      }
    }
  }

  // This is an array of errors,
  if (Array.isArray(errors)){
    for (let error of errors){
      if(error.cause){
        //If cause key exists populate with string.
        returnMessage.push(error.cause);
      } else {
        returnMessage.push(error);
      }

    }

  }
  return returnMessage;

}