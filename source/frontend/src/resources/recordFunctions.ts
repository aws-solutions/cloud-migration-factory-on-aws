/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {getNestedValuePath} from "./main";
import {Attribute, BaseData, EntitySchema} from "../models/EntitySchema";
import {CmfAddNotification} from "../models/AppChildProps";


type QueryType = {
  comparator: any;
  attribute: string;
  value: any;
};

function isEqualsQueryTrue(
  query: QueryType,
  item: Record<string, any>
) {
  if (item[query.attribute] && query.value) { //Check this condition has ability to provide outcome.
    //Attribute exists.
    return item[query.attribute] === query.value;
  }
}

function isNotEqualsQueryTrue(
  query: QueryType,
  item: Record<string, any>
) {
  if (item[query.attribute] && query.value) { //Check this condition has ability to provide outcome.
    //Attribute exists.
    return item[query.attribute] !== query.value;
  }
}

function isNotEmptyQueryTrue(
  query: QueryType,
  item: Record<string, any>
) {
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

function isEmptyQueryTrue(
  query: QueryType,
  item: Record<string, any>
) {
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


function evaluateQueryCondition(
  query: QueryType,
  item: Record<string, any>
) {
  let queryResult = null;

  switch (query.comparator) {
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

function isRequiredOutcome(
  outcomes: Record<string, any>,
  type: string
) {
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

function isHiddenOutcome(
  outcomes: Record<string, any>,
  type: string
) {
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

export function checkAttributeRequiredConditions(
  item: Record<string, any>,
  conditions: {
    queries: any;
    outcomes: Record<string, any>;
  }
) {
  let returnRequired = null;
  let returnHidden = null;
  const comparisonTypeDefault = 'AND'

  if (!conditions) {
    //No conditions passed.
    return {'required': returnRequired, 'hidden': returnHidden};
  }

  let queryResult = null;

  for (const query of conditions.queries) {
    let singleQueryResult = evaluateQueryCondition(query, item);
    if (comparisonTypeDefault == 'AND')
    {
      if (singleQueryResult !== false) //AND the results.
      {
        queryResult = singleQueryResult;
      } else {
        queryResult = singleQueryResult;
        break; //At least one query is false, no need to continue.
      }
    }
    else
    {
      if (singleQueryResult == true) //OR the results.
      {
        queryResult = singleQueryResult;
        break; //At least one query is true, no need to continue.
      } else {
        queryResult = singleQueryResult;
      }
    }
  }

  //Evaluate true outcomes.
  if (queryResult) {
    returnHidden = isHiddenOutcome(conditions.outcomes, 'true');
    returnRequired = isRequiredOutcome(conditions.outcomes, 'true')
  } else if (queryResult !== null) {
    returnHidden = isHiddenOutcome(conditions.outcomes, 'false');
    returnRequired = isRequiredOutcome(conditions.outcomes, 'false')
  }

  return {'required': returnRequired, 'hidden': returnHidden};

}

function isAttributeRequired(
  attribute: Attribute,
  schema: EntitySchema,
  includeConditional: boolean) {
  let schemaKeyAttributeName = schema.schema_name === 'application' ? 'app_id' : schema.schema_name + '_id';

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

export function getRequiredAttributes(schema: EntitySchema, includeConditional = false) {
  let required_attributes: Attribute[] = [];

  if (schema) {
    required_attributes = schema.attributes.filter(attribute => isAttributeRequired(attribute, schema, includeConditional));
  }

  return required_attributes;

}

export function getRelationshipRecord(
  attribute: Attribute,
  relatedData: BaseData,
  value: string
) {

  // Check if related data for the entity required is present in relatedData object.
  const relEntity = attribute.rel_entity!;
  if (relatedData?.[relEntity] && !(relatedData[relEntity]?.isLoading || !value)) {
    if (attribute.listMultiSelect) {
      // Multiselect relationship values.
      return relatedData[relEntity]?.data.filter((item: any) =>
        isItemRelationshipMatch(attribute.rel_key, item, value)
      );
    } else {
      let record = relatedData[relEntity]?.data.find((item: any) =>
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

function isItemRelationshipMatch(
  relatedRecordKey: string | undefined,
  record: any,
  relationshipKeyValues: string | any[]
) {
  for (const listItem of relationshipKeyValues) {
    if (getNestedValuePath(record, relatedRecordKey).toLowerCase() === listItem.toLowerCase()) {
      return true;
    }
  }
  return false;
}

function getUnresolvedRelationships(
  relatedRecordKey: any,
  resolvedRelationshipRecords: any[],
  relationshipKeyValues: any[]
) {
  let invalidRelationshipKeys = [];
  if (resolvedRelationshipRecords.length !== relationshipKeyValues.length) {
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

function getRelationshipMultiSelectDisplayValues(
  attribute: Attribute,
  relatedData: BaseData,
  relationshipKeyValues: any[]
): {
  invalid?: any[];
  value: any;
  status: "loaded"
} {
  // Multiselect relationships value.
  const relEntity = attribute.rel_entity!;
  let foundRelationshipRecords = relatedData[relEntity]?.data.filter(
    (item: any) => isItemRelationshipMatch(attribute.rel_key, item, relationshipKeyValues)
  ) ?? [];

  let resolvedDisplayValues = foundRelationshipRecords.map((item: any) => {
    return (getNestedValuePath(item, attribute.rel_display_attribute))
  });

  let unresolvedRelationShips = getUnresolvedRelationships(attribute.rel_key, foundRelationshipRecords, relationshipKeyValues);

  return {status: 'loaded', value: resolvedDisplayValues, invalid: unresolvedRelationShips};
}

function getRelationshipSingleDisplayValue(
  attribute: Attribute,
  relatedData: BaseData,
  currentValue: any | string
): {
  value: any;
  status: "not found" | "loaded"
} {
  const relEntity = attribute.rel_entity!;
  let record = relatedData[relEntity]?.data.find((item: any) =>
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

export function getRelationshipValue(
  attribute: Attribute,
  relatedData: BaseData,
  value: any[] | null
): {
  value: any | null;
  status: "loaded" | "loading" | "not found";
  invalid?: any[];
} {

  const relEntity = attribute.rel_entity!;
  if (relatedData?.[relEntity]) {
    //relatedData contains the related entity data to perform lookup.
    if (relatedData[relEntity]?.isLoading || !value) {
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

function appendValidationErrors(
  errorList: any[],
  validationErrors: any[]
) {
  if (validationErrors?.length > 0) {
    for (const error of validationErrors) {
      for (const error_detail in error) {
        errorList.push(error_detail + ' : ' + error[error_detail].join());
      }
    }
  }
}

function appendExistingNameErrors(
  errorList: any[],
  existingNameErrors: any[]
) {
  if (existingNameErrors?.length > 0) {
    for (const error of existingNameErrors) {
      errorList.push(error + " already exists.");
    }
  }
}

// TODO cleanly define the expected error datastructure returned from the API
export function parsePUTResponseErrors(errors: any): any[] {
  let errorList: any[] = [];
  //Check for validation errors.
  appendValidationErrors(errorList, errors?.validation_errors);

  //Check for duplication errors.
  appendExistingNameErrors(errorList, errors?.existing_name);

  //Check for unprocessed put errors.
  appendValidationErrors(errorList, errors?.unprocessed_items);

  // This is an array of errors.
  if (Array.isArray(errors)) {
    for (const error of errors) {
      if (error.cause) {
        //If cause key exists populate with string.
        errorList.push(error.cause);
      } else {
        errorList.push(error);
      }

    }

  }

  return errorList;
}

export function apiActionErrorHandler(
  action: string,
  schemaName: string,
  error: any,
  addNotification: (notificationAddRequest: CmfAddNotification) => string
) {
  console.error(error);
  let response: string;
  //Check if errors key exists from Lambda errors.
  if (error.response?.data?.errors) {
    response = error.response.data.errors;
    response = parsePUTResponseErrors(response).join(',');
  } else if (error.response?.data?.cause) {
    response = error.response.data.cause;
  } else {
    response = 'Unknown error occurred.';
  }

  addNotification({
    type: 'error',
    dismissible: true,
    header: action + " " + schemaName,
    content: (response)
  })
}