#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import cmf_boto
import functools
import re
import query_conditions
from query_comparator_operations import query_comparator_operations_dictionary
from boto3.dynamodb.conditions import Key

application = os.environ['application']
environment = os.environ['environment']

ATTRIBUTE_MESSAGE_PREFIX = "Attribute "

SCHEMA_TO_TABLE_NAME_OVERRIDE_MAP = {
        'application': 'app',
        'script': 'ssm-script'
    }

STATUS_TXT_IN_PROGRESS = 'In Progress'
STATUS_TXT_COMPLETE = 'Complete'
STATUS_TXT_NOT_STARTED = 'Not Started'
STATUS_TXT_SKIPPED = 'Skip'
STATUS_TXT_RETRY = 'Retry'
STATUS_TXT_FAILED = 'Failed'
STATUS_TXT_PENDING_APPROVAL = 'Pending Approval'
STATUS_OK_TO_RETRY = [STATUS_TXT_COMPLETE, STATUS_TXT_SKIPPED, STATUS_TXT_FAILED]
TASK_PREDECESSOR_ALLOWED_UPDATE_STATUS = [STATUS_TXT_COMPLETE, STATUS_TXT_SKIPPED]

DEFAULT_TAG_REGEX = '^[a-zA-Z0-9+-=._:/@ ]+$'

SCHEMA_NO_DDB_TABLE_LOOKUP = ['secret']  # schema names provided here will bypass relationship data validations during record create and update operations.

class UnSupportedOperationTypeException(Exception):
    pass


def get_function_for_operation(operation):
    try:
        return query_comparator_operations_dictionary[operation]
    except KeyError as key_error:
        print(key_error)
        raise UnSupportedOperationTypeException(f"The operation {operation} is not supported")


def get_required_attributes(schema, include_conditional=False):
    required_attributes = []

    if not schema:
        return required_attributes

    schema_system_key = schema['schema_name'] + '_id'
    if schema['schema_name'] == 'application':
        schema_system_key = 'app_id'

    for attribute in schema['attributes']:
        # Check if mandatory required flag set and not the system key attribute.
        if ('required' in attribute and attribute['required'] == True) \
            and not ('hidden' in attribute and attribute['hidden'] == True) \
            and attribute['name'] != schema_system_key \
            and attribute.get('type') != 'relationship':
            required_attributes.append(attribute)
        # if not mandatory required then is there a conditional required.
        elif 'conditions' in attribute and include_conditional:
            required_attributes = append_conditional_attributes(attribute, required_attributes)

    return required_attributes


def append_conditional_attributes(attribute, required_attributes):
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
        operation = get_function_for_operation(query['comparator'])
        if operation:
            query_result = operation(item, query, query_result)
            if query_result == False:
                break

    if query_result:
        if 'true' in conditions['outcomes']:
            conditions = conditions['outcomes']['true']
    elif 'false' in conditions['outcomes']:
        conditions = conditions['outcomes']['false']

    return_required, return_hidden = query_conditions.parse_outcomes(conditions)
    return {'required': return_required, 'hidden': return_hidden}


def check_valid_item_create(item, schema, related_items=None):
    required_attributes = get_required_attributes(schema, True)
    invalid_attributes = check_required_attributes(item, required_attributes)
    if len(invalid_attributes) > 0:
        return invalid_attributes

    # check that values are correct.
    validation_errors = []
    validation_errors.extend(validate_item_keys_and_values(item, schema['attributes'], related_items))
    validation_errors.extend(invalid_attributes)

    # Add schema-specification validation
    if schema['schema_name'] == 'pipeline':
        validation_errors.extend(check_valid_pipeline_create(item))
    elif schema['schema_name'] == 'task_execution':
        validation_errors.extend(check_valid_task_execution_update(item))

    if len(validation_errors) > 0:
        return validation_errors
    else:
        return None


def check_required_attributes(item, required_attributes):
    invalid_attributes = []
    for attribute in required_attributes:
        invalid_attribute_message = f"{ATTRIBUTE_MESSAGE_PREFIX}{attribute['name']} is required and not provided."
        is_valid = True
        if 'required' in attribute and attribute['required']:
            # Attribute is required.
            is_valid = is_required_attribute_valid(item, attribute)
        elif 'conditions' in attribute:
            is_valid = is_conditional_attribute_valid(item, attribute)

        if not is_valid:
            invalid_attributes.append(invalid_attribute_message)
    return invalid_attributes


def is_required_attribute_valid(item, attribute):
    attr_value = functools.reduce(lambda obj, path: obj.get(path, ''), attribute['name'].split("."), item)
    return bool(attr_value)


def is_conditional_attribute_valid(item, attribute):
    conditions_check_result = check_attribute_required_conditions(item, attribute['conditions'])
    if conditions_check_result['required'] and  \
        not (attribute['name'] in item and item[attribute['name']] != '' and item[
            attribute['name']] is not None):
            return False

    return True


def validate_value(attribute, value, regex_string):
    std_error = "Error in validation, please check entered value."
    error = None
    pattern = re.compile(regex_string)
    if not pattern.match(value):
        # Validation error.
        if 'validation_regex_msg' in attribute and attribute['validation_regex_msg'] != '':
            error = f"{ATTRIBUTE_MESSAGE_PREFIX}{attribute['name']}, {attribute['validation_regex_msg']}"
        else:
            error = f"{ATTRIBUTE_MESSAGE_PREFIX}{attribute['name']}, {std_error}"

    return error


def get_related_items(related_schema_names):
    related_items = {}

    for related_schema_name in related_schema_names:
        # Check that item is set.
        if not related_schema_name:
            continue

        if related_schema_name in SCHEMA_NO_DDB_TABLE_LOOKUP:
            continue  # entity not saved in DDB so no check is possible also options list is provided by external source.

        table_name_suffix = map_schema_to_table_name_suffix(related_schema_name)

        related_table_name = '{}-{}-{}'.format(application, environment, table_name_suffix)

        related_table = cmf_boto.resource('dynamodb').Table(related_table_name)
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
    if attribute.get('rel_entity') in SCHEMA_NO_DDB_TABLE_LOOKUP:
        return None # entity not saved in DDB so no check is possible also options list is provided by external source.

    if 'rel_entity' not in attribute or 'rel_key' not in attribute:
        # invalid relationship attribute.
        return [attribute['name'] + ': Invalid relationship attribute schema or key missing.']
    else:
        if preloaded_related_items:
            # Preloaded items provided.
            related_items = preloaded_related_items
        else:
            # No preloaded item provided, load from DDB table.
            related_items = load_items_from_ddb(attribute)

        if 'listMultiSelect' in attribute and attribute['listMultiSelect']:
            message = validate_list_multi_select(attribute, related_items, value)
        else:
            message = validate_non_list_multi_select(attribute, related_items, value)

        return message


def load_items_from_ddb(attribute):
    # No preloaded item provided, load from DDB table.

    table_name_suffix = map_schema_to_table_name_suffix(attribute['rel_entity'])

    related_table_name = '{}-{}-{}'.format(application, environment, table_name_suffix)

    related_table = cmf_boto.resource('dynamodb').Table(related_table_name)
    related_items = scan_dynamodb_data_table(related_table)  # get all items from related table.

    return related_items


def validate_list_multi_select(attribute, related_items, value):
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


def validate_non_list_multi_select(attribute, related_items, value):
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


def validate_tag_value(attribute, tag, errors):
    if 'validation_regex' in attribute and attribute['validation_regex'] != '':
        value_validation_result = validate_value(attribute, tag['value'], attribute['validation_regex'])
        if value_validation_result != None:
            errors.append(value_validation_result)
    else:
        # use default regex for tag value validation
        value_validation_result = validate_value(attribute, tag['value'], DEFAULT_TAG_REGEX)
        if value_validation_result != None:
            errors.append(value_validation_result)


def validate_tag_type_attribute(item, attribute, key, errors):

    for tag in item[key]:
        validate_tag_value(attribute, tag, errors)

    return errors


def validate_list_type_attribute(item, attribute, key, errors):
    listvalue = attribute['listvalue'].lower().split(',')
    if 'listMultiSelect' in attribute and attribute['listMultiSelect'] == True:
        for item in item[key]:
            if str(item).lower() not in listvalue:
                message = ATTRIBUTE_MESSAGE_PREFIX + key + "'s value does not match any of the allowed values '" + \
                            attribute['listvalue'] + "' defined in the schema"
                errors.append(message)
    else:
        if item[key] != '' and str(item[key]).lower() not in listvalue:
                message = ATTRIBUTE_MESSAGE_PREFIX + key + "'s value does not match any of the allowed values '" + \
                            attribute[
                                'listvalue'] + "' defined in the schema"
                errors.append(message)

    return errors


def validate_relationship_type_attribute(related_items, item, attribute, key, errors):
    if related_items and attribute['rel_entity'] in related_items.keys():
        related_record_validation = validate_item_related_record(
            attribute, item[key],
            related_items[attribute['rel_entity']])
    else:
        # relationship items not preloaded, validate will have to fetch them.
        related_record_validation = validate_item_related_record(attribute, item[key])

    if related_record_validation != None:
        errors.append(related_record_validation)

    return errors


def validate_other_type_attribute(item, attribute, key, errors):
    if 'validation_regex' in attribute and attribute['validation_regex'] != '' \
        and item[key] != '' and item[key] is not None:
        if attribute['type'] == 'multivalue-string':
            errors = validate_multivalue_string_type_attribute(item, attribute, key, errors)
        else:
            value_validation_result = validate_value(attribute, item[key], attribute['validation_regex'])
            if value_validation_result != None:
                errors.append(value_validation_result)

    return errors


def validate_multivalue_string_type_attribute(item, attribute, key, errors):
    valid_regex = True
    for value in item[key]:
        value_validation_result = validate_value(attribute, value, attribute['validation_regex'])
        if value_validation_result != None:
            valid_regex = False
    if not valid_regex:
        errors.append(value_validation_result)

    return errors


def append_error_message(check, key, errors):
    if check == False:
        message = f"{ATTRIBUTE_MESSAGE_PREFIX}{key} is not defined in the schema."
        errors.append(message)

    return errors


def validate_attribute(attribute, item, key, errors, related_items):
    if attribute['type'] == 'list' and 'listvalue' in attribute:
        errors = validate_list_type_attribute(item, attribute, key, errors)
    elif attribute['type'] == 'relationship':
        errors = validate_relationship_type_attribute(related_items, item, attribute, key, errors)
    elif attribute['type'] == 'tag':
        errors = validate_tag_type_attribute(item, attribute, key, errors)
    else:
        errors = validate_other_type_attribute(item, attribute, key, errors)

    return errors


def validate_item_keys_and_values(item, attributes, related_items=None):
    errors = []

    for key in item.keys():
        check = False
        if key.startswith('_'):
            #  Ignore system keys.
            continue
        for attribute in attributes:
            if key == attribute['name']:
                check = True
                errors = validate_attribute(attribute, item, key, errors, related_items)
                break  # Exit loop as key matched to attribute no need to check other attributes.

        errors = append_error_message(check, key, errors)

    return errors


def scan_dynamodb_data_table(data_table):
    response = data_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluate key is   " + str(response['LastEvaluatedKey']))
        response = data_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response['Items'])
    return scan_data


def query_dynamodb_index(data_table, index_name, key_condition):
    response = data_table.query(
        IndexName=index_name,
        KeyConditionExpression=key_condition
    )
    query_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluated key is " + str(response['LastEvaluatedKey']))
        response = data_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        query_data.extend(response['Items'])
    return query_data


def does_item_exist(new_item_key, new_item_value, current_items):
    # Search current_items for key and value that match.
    for item in current_items:
        if new_item_key in item and str(item[new_item_key]).lower() == str(new_item_value).lower():
            return True

    # Item not found in current_items.
    return False


def get_task(task_id, task_version=0):
    validation_errors = []
    task_table_name = '{}-{}-ssm-scripts'.format(application, environment)
    task_table = cmf_boto.resource('dynamodb').Table(task_table_name)

    task = task_table.get_item(Key={'package_uuid': task_id, 'version' : int(task_version)})

    if 'Item' not in task:
        msg = f'Task ID "{task_id}" was not found'
        print(msg)
        validation_errors.append(msg)

    return task, validation_errors


def check_valid_pipeline_create(item):
    validation_errors = []
    pipeline_template_task_table_name = '{}-{}-pipeline_template_tasks'.format(application, environment)
    pipeline_template_task_table = cmf_boto.resource('dynamodb').Table(pipeline_template_task_table_name)

    pipeline_template_id = item['pipeline_template_id']
    pipeline_template_tasks = query_dynamodb_index(
        pipeline_template_task_table,
        'pipeline_template_id-index',
        Key('pipeline_template_id').eq(pipeline_template_id)
    )
    pipeline_task_arguments = item.get('task_arguments', [])

    for pipeline_template_task in pipeline_template_tasks:
        task_id = pipeline_template_task['task_id']
        task_version = pipeline_template_task['task_version']

        task, task_errors = get_task(task_id, task_version)
        if task_errors:
            validation_errors.extend(task_errors)
            continue

        if 'task_arguments' not in task['Item']:
            # No arguments to validate
            continue

        task_template_arguments = task['Item']['task_arguments']
        task_template_argument_names = [arg['name'] for arg in task_template_arguments]

        required_attributes = [arg for arg in task_template_arguments if arg.get('required', False)]
        task_args = {i:pipeline_task_arguments[i] for i in pipeline_task_arguments if i in task_template_argument_names}

        errors = check_required_attributes(task_args, required_attributes)
        validation_errors.extend(errors)

        errors = validate_item_keys_and_values(task_args, task_template_arguments)
        validation_errors.extend(errors)

    return validation_errors


def check_valid_task_execution_update(item):

    task, task_errors = get_task(item['task_id'], item['task_version'])
    if task_errors:
        return task_errors

    pipeline_id = item['pipeline_id']
    task_execution_table_name = '{}-{}-task_executions'.format(application, environment)
    task_execution_table = cmf_boto.resource('dynamodb').Table(task_execution_table_name)
    task_executions = query_dynamodb_index(
        task_execution_table,
        'pipeline_id-index',
        Key('pipeline_id').eq(pipeline_id)
    )

    validation_errors = validate_task_predecessors_status(item, task_executions)

    current_task_execution = next(t for t in task_executions if t['task_execution_id'] == item['task_execution_id'])

    if task['Item']['type'] == 'Automated' and current_task_execution['task_execution_status'] not in STATUS_OK_TO_RETRY:
        msg = f'Can not update execution status for an automated task with status: {item["task_execution_status"]}'
        print(msg)
        validation_errors.append(msg)

    return validation_errors

def map_schema_to_table_name_suffix(schema_name):
    table_name_suffix = schema_name

    # if schema is found in the map then use the table name suffix assigned instead of schema name.
    if SCHEMA_TO_TABLE_NAME_OVERRIDE_MAP.get(schema_name, None):
        table_name_suffix = SCHEMA_TO_TABLE_NAME_OVERRIDE_MAP.get(schema_name)

    # pluralize table name suffix.
    table_name_suffix = f"{table_name_suffix}s"

    return table_name_suffix

def get_task_execution_predecessors(task_id, tasks):
    predecessors = []
    for task in tasks:
        if task_id in task['task_successors']:
            predecessors.append(task)

    return predecessors


def validate_task_predecessors_status(item, task_executions):
    errors = []

    # validate that all predecessor tasks are in a valid state to allow task updates.
    predecessors = get_task_execution_predecessors(item['task_execution_id'], task_executions)

    for predecessor in predecessors:
        if predecessor['task_execution_status'] not in TASK_PREDECESSOR_ALLOWED_UPDATE_STATUS:
            msg = f"Can not update execution status for task as predecessor '{predecessor['task_execution_name']}' as it is not in a valid state ({predecessor['task_execution_status']})"
            errors.append(msg)

    return errors


def is_valid_id(schema, item_id):
    if schema.get('key_type', 'number') == 'number':
        pattern = re.compile("^\d+$")
        if not pattern.match(item_id):
            return False
    elif schema.get('key_type', 'number') == 'uuid':
        pattern = re.compile("^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z")
        if not pattern.match(item_id):
            return False

    return True
