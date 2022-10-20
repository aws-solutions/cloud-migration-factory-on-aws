import os
import boto3
import re

application = os.environ['application']
environment = os.environ['environment']


def get_required_attributes(schema, include_conditional=False):
    required_attributes = []
    schema_system_key = schema['schema_name'] + '_id'

    if schema['schema_name'] == 'application':
        schema_system_key = 'app_id'

    if schema:
        for attribute in schema['attributes']:

            if ('required' in attribute and attribute['required'] == True) \
                and not ('hidden' in attribute and attribute['hidden'] == True) \
                and attribute[
                'name'] != schema_system_key:  # Check if mandatory required flag set and not the system key attribute.
                required_attributes.append(attribute)
            elif 'conditions' in attribute and include_conditional:
                # if not mandatory required then is there a conditional required.
                if 'outcomes' in attribute['conditions'] and 'true' in attribute['conditions']['outcomes']:
                    for outcome in attribute['conditions']['outcomes']['true']:
                        if outcome == 'required':
                            required_attributes.append(attribute)
                if 'outcomes' in attribute['conditions'] and 'false' in attribute['conditions']['outcomes']:
                    for outcome in attribute['conditions']['outcomes']['false']:
                        if outcome == 'required':
                            required_attributes.append(attribute)
    return required_attributes


def check_attribute_required_conditions(item, conditions):
    return_required = False
    return_hidden = False
    query_result = None

    if not conditions:
        # No conditions passed.
        return {'required': return_required, 'hidden': return_hidden}

    for query in conditions['queries']:
        if query['comparator'] == '=':
            if query['attribute'] in item and query['value']:
                if item[query['attribute']] == query['value']:
                    if query_result != False:
                        query_result = True
                else:
                    query_result = False
                    break
        elif query['comparator'] == '!=':
            if query['attribute'] in item and query['value']:
                if item[query['attribute']] != query['value']:
                    if query_result != False:
                        query_result = True
                else:
                    query_result = False
                    break
        elif query['comparator'] == '!empty':
            if query['attribute'] in item:
                if isinstance(item[query['attribute']], list):
                    if len(item[query['attribute']]) != 0:
                        if query_result != False:
                            query_result = True
                    else:
                        query_result = False
                        break
                else:
                    if item[query['attribute']] != '':
                        if query_result != False:
                            query_result = True
                    else:
                        query_result = False
                        break
        elif query['comparator'] == 'empty':
            if query['attribute'] in item:
                if isinstance(item[query['attribute']], list):
                    if len(item[query['attribute']]) > 0:
                        if query_result != False:
                            query_result = True
                    else:
                        query_result = False
                        break
                else:
                    if item[query['attribute']] == '':
                        if query_result != False:
                            query_result = True
                    else:
                        query_result = False
                        break
            elif query['attribute'] not in item and 'comparator' in query:
                if query_result != False:
                    query_result = True

    if query_result:
        if 'true' in conditions['outcomes']:
            for outcome in conditions['outcomes']['true']:
                if outcome == 'required':
                    return_required = True
                    continue
                elif outcome == 'not_required':
                    return_required = False
                    continue
                elif outcome == 'hidden':
                    return_hidden = True
                    continue
                elif outcome == 'not_hidden':
                    return_hidden = False
                    continue
    else:
        if 'false' in conditions['outcomes']:
            for outcome in conditions['outcomes']['false']:
                if outcome == 'required':
                    return_required = True
                    continue
                elif outcome == 'not_required':
                    return_required = False
                    continue
                elif outcome == 'hidden':
                    return_hidden = True
                    continue
                elif outcome == 'not_hidden':
                    return_hidden = False
                    continue

    return {'required': return_required, 'hidden': return_hidden}


def check_valid_item_create(item, schema, related_items=None):
    invalid_attributes = []

    required_attributes = get_required_attributes(schema, True)

    for attribute in required_attributes:
        if 'required' in attribute and attribute['required']:
            # Attribute is required.
            if attribute['name'] in item:
                if not (item[attribute['name']] != '' and item[attribute['name']] is not None):
                    invalid_attributes.append("Attribute: " + attribute['name'] + " is required and not provided.")
            else:
                # key not in item, missing required attribute.
                invalid_attributes.append("Attribute: " + attribute['name'] + " is required and not provided.")
        elif 'conditions' in attribute:
            conditions_check_result = check_attribute_required_conditions(item, attribute['conditions'])
            if conditions_check_result['required']:
                if not (attribute['name'] in item and item[attribute['name']] != '' and item[
                    attribute['name']] is not None):
                    invalid_attributes.append("Attribute: " + attribute['name'] + " is required and not provided.")

    if len(invalid_attributes) > 0:
        return invalid_attributes

    # check that values are correct.
    validation_errors = validate_item_keys_and_values(item, schema['attributes'], related_items)

    validation_errors.extend(invalid_attributes)

    if len(validation_errors) > 0:
        return validation_errors
    else:
        return None


def validate_value(attribute, value):
    std_error = "Error in validation, please check entered value.";
    error = None
    pattern = re.compile(attribute['validation_regex'])
    if not pattern.match(value):
        # Validation error.
        if 'validation_regex_msg' in attribute:
            error = "Attribute: " + attribute['name'] + ", " + attribute['validation_regex_msg']
        else:
            error = "Attribute: " + attribute['name'] + ", " + std_error

    return error


def get_related_items(related_schema_names):
    related_items = {}

    for related_schema_name in related_schema_names:
        # Check that item is set.
        if not related_schema_name:
            continue

        if related_schema_name == 'application':
            table_name = 'app'
        else:
            table_name = related_schema_name

        related_table_name = '{}-{}-{}s'.format(application, environment, table_name)

        related_table = boto3.resource('dynamodb').Table(related_table_name)
        related_table_items = scan_dynamodb_data_table(related_table)  # get all items from related table.
        related_items[related_schema_name] = related_table_items

    return related_items


def get_item_attribute_names(items):
    attribute_names = []
    for item in items:
        for key in item.keys():
            if key.startswith('_'):
                #  Ignore system keys.
                continue
            if key not in attribute_names:
                attribute_names.append(key)

    return attribute_names


# Filters the provided attributes for all with a type of relationship.
def get_relationship_attributes(attribute_names, attributes):
    relationship_attributes = []
    for attribute in attributes:
        if attribute['name'] in attribute_names:
            if attribute['type'] == 'relationship':
                relationship_attributes.append(attribute)

    return relationship_attributes


# Searches relationship_attributes parameter and provides related table names.
def get_relationship_schema_names(relationship_attributes):
    relationship_schema_names = []
    for relationship_attribute in relationship_attributes:
        if 'rel_entity' not in relationship_attribute:
            continue

        relationship_schema_names.append(relationship_attribute['rel_entity'])

    return relationship_schema_names


# Based on the items provided it returns any related data items to be used to validate relationships.
def get_relationship_data(items, schema):
    # Get duplicated list of attributes being uploaded.
    attribute_names = get_item_attribute_names(items)

    # Filter attributes for relationship attributes.
    relationship_attributes = get_relationship_attributes(attribute_names, schema['attributes'])

    # extract schema names from related attributes.
    relationship_schema_names = get_relationship_schema_names(relationship_attributes)

    # Get all data for the schema list provided.
    related_data = get_related_items(relationship_schema_names)

    return related_data


def validate_item_related_record(attribute, value, preloaded_related_items=None):
    if attribute['type'] != 'relationship':
        return None  # Not a relationship attribute, return success.

    if 'rel_entity' not in attribute or 'rel_key' not in attribute:
        # invalid relationship attribute.
        return [attribute['name'] + ': Invalid relationship attribute schema or key missing.']
    else:
        if preloaded_related_items:
            # Preloaded items provided.
            related_items = preloaded_related_items
        else:
            # No preloaded item provided, load from DDB table.
            table_name = attribute['rel_entity']
            if table_name == 'application':
                table_name = 'app'

            related_table_name = '{}-{}-{}s'.format(application, environment, table_name)

            related_table = boto3.resource('dynamodb').Table(related_table_name)
            related_items = scan_dynamodb_data_table(related_table)  # get all items from related table.

        if 'listMultiSelect' in attribute and attribute['listMultiSelect']:
            related_records_found = []
            related_records_not_found = []
            for related_item in related_items:
                if related_item[attribute['rel_key']] in value:
                    related_records_found.append(related_item[attribute['rel_key']])

            for record_id in value:
                if record_id not in related_records_found:
                    related_records_not_found.append(record_id)

            if len(related_records_not_found) > 0:
                message = attribute['name'] + ': The following related record ids do not exist using key ' + \
                          attribute['rel_key'] + ' - ' + ", ".join(related_records_not_found)
                return [message]
            else:
                #  All related IDs found.
                return None
        else:
            related_record_found = False
            for related_item in related_items:
                if related_item[attribute['rel_key']] == str(value):
                    related_record_found = True

            if not related_record_found:
                message = attribute['name'] + ':' + value + ' related record does not exist using key ' + \
                          attribute['rel_key']
                return [message]
            else:
                return None

    # return [attribute['name'] + ': Unsupported relationship schema ' + attribute['rel_entity']]  # invalid relationship attribute.


def validate_item_keys_and_values(item, attributes, related_items=None):
    errors = []
    std_error = "Error in validation, please check entered value."
    for key in item.keys():
        check = False
        if key.startswith('_'):
            #  Ignore system keys.
            continue
        for attribute in attributes:
            if key == attribute['name']:
                check = True
                if attribute['type'] == 'list' and 'listvalue' in attribute:
                    listvalue = attribute['listvalue'].lower().split(',')
                    if 'listMultiSelect' in attribute and attribute['listMultiSelect'] == True:
                        for item in item[key]:
                            if item.lower() not in listvalue:
                                message = "Attribute " + key + "'s value does not match any of the allowed values '" + \
                                          attribute['listvalue'] + "' defined in the schema"
                                errors.append(message)
                    else:
                        if item[key] != '':
                            if item[key].lower() not in listvalue:
                                message = "Attribute " + key + "'s value does not match any of the allowed values '" + \
                                          attribute[
                                              'listvalue'] + "' defined in the schema"
                                errors.append(message)
                elif attribute['type'] == 'relationship':
                    if related_items and attribute['rel_entity'] in related_items.keys():
                        related_record_validation = validate_item_related_record(attribute, item[key],
                                                                                 related_items[attribute['rel_entity']])
                    else:
                        # relationship items not preloaded, validate will have to fetch them.
                        related_record_validation = validate_item_related_record(attribute, item[key])

                    if related_record_validation != None:
                        errors.append(related_record_validation)
                else:
                    if 'validation_regex' in attribute and attribute['validation_regex'] != '' and item[key] != '' and \
                        item[
                            key] is not None:
                        if attribute['type'] == 'multivalue-string':
                            valid_regex = True
                            for value in item[key]:
                                value_validation_result = validate_value(attribute, value)
                                if value_validation_result != None:
                                    valid_regex = False
                            if not valid_regex:
                                errors.append(value_validation_result)
                        else:
                            value_validation_result = validate_value(attribute, item[key])
                            if value_validation_result != None:
                                errors.append(value_validation_result)
                break  # Exit loop as key matched to attribute no need to check other attributes.

        if check == False:
            message = "Attribute: " + key + " is not defined in the schema."
            errors.append(message)

    return errors


def scan_dynamodb_data_table(data_table):
    response = data_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluate key is   " + str(response['LastEvaluatedKey']))
        response = data_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response['Items'])
    return scan_data


def does_item_exist(new_item_key, new_item_value, current_items):
    # Search current_items for key and value that match.
    for item in current_items:
        if new_item_key in item and item[new_item_key] == new_item_value:
            return True

    # Item not found in current_items.
    return False
