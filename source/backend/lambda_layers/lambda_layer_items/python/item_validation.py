#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import cmf_boto
import functools
import re
import query_conditions
from query_comparator_operations import query_comparator_operations_dictionary
from boto3.dynamodb.conditions import Key, Attr

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
STATUS_TXT_ABANDONED = 'Abandoned'
STATUS_OK_TO_RETRY = [STATUS_TXT_COMPLETE, STATUS_TXT_SKIPPED, STATUS_TXT_FAILED, STATUS_TXT_ABANDONED]
TASK_PREDECESSOR_ALLOWED_UPDATE_STATUS = [STATUS_TXT_COMPLETE, STATUS_TXT_SKIPPED, STATUS_TXT_ABANDONED]

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


def check_valid_item_create(item, schema):
    required_attributes = get_required_attributes(schema, True)
    invalid_attributes = check_required_attributes(item, required_attributes)
    if len(invalid_attributes) > 0:
        return invalid_attributes

    # check that values are correct.
    validation_errors = []
    validation_errors.extend(validate_item_keys_and_values(item, schema['attributes']))
    validation_errors.extend(invalid_attributes)

    # Add schema-specification validation
    if schema['schema_name'] == 'pipeline':
        validation_errors.extend(check_valid_pipeline_create(item))
    elif schema['schema_name'] == 'task_execution':
        validation_errors.extend(check_valid_task_execution_update(item))
    elif schema['schema_name'] == 'rule':
        validation_errors.extend(check_valid_rule_create(item))

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


def validate_required_relationship(item, attribute, key, errors):
    if not item[key] and 'required' in attribute and attribute['required']:
        errors.append(f"{ATTRIBUTE_MESSAGE_PREFIX}{attribute['name']} is required and not provided.")
        return True
    return False


def validate_relationship_schema(attribute, errors):
    if not "rel_entity" in attribute and not "rel_key" in attribute:
        errors.append(attribute['name'] + ': Invalid relationship attribute schema or key missing.')
        return False
    return True


def validate_multi_select_relationship(item, attribute, key, errors):
    relationship_values = item[key] if isinstance(item[key], list) else [item[key]]
    unique_values = list(dict.fromkeys(relationship_values))  # Remove duplicates while preserving order
    not_found_values = []
    
    table_name_suffix = map_schema_to_table_name_suffix(attribute["rel_entity"])
    related_table_name = '{}-{}-{}'.format(application, environment, table_name_suffix)
    client = cmf_boto.client('dynamodb')

    keys = [{attribute["rel_key"]: {'S': str(value)}} for value in unique_values]
    try:
        response = client.batch_get_item(
            RequestItems={
                related_table_name: {'Keys': keys}
            }
        )
        
        response_items = response.get('Responses', {}).get(related_table_name, [])
        found_values = {item[attribute["rel_key"]]['S'] for item in response_items}
        not_found_values = [str(value) for value in relationship_values if str(value) not in found_values]
        
    except Exception as e:
        errors.append(f"{key}: Failed to validate relationship - {str(e)}")
        return
    
    if not_found_values:
        errors.append(key + ': The following related record ids do not exist using key ' + \
                    attribute["rel_key"] + ' - ' + ", ".join(not_found_values))


def validate_single_relationship(item, attribute, key, errors):
    table_name_suffix = map_schema_to_table_name_suffix(attribute["rel_entity"])
    related_table_name = '{}-{}-{}'.format(application, environment, table_name_suffix)
    related_table = cmf_boto.resource('dynamodb').Table(related_table_name)
    
    # Use query instead of get_item as there are tables with SK
    try:
        response = related_table.query(
            KeyConditionExpression=Key(attribute["rel_key"]).eq(str(item[key]))
        )
        if not response.get('Items'):
            errors.append(key + ':' + str(item[key]) + ' related record does not exist using key ' + attribute["rel_key"])
    except Exception as e:
        errors.append(f"{key}: Failed to validate relationship - {str(e)}")


def validate_relationship_type_attribute(item, attribute, key, errors):
    if validate_required_relationship(item, attribute, key, errors) or not item[key]:
        return errors
        
    if not validate_relationship_schema(attribute, errors):
        return errors
        
    if attribute["rel_entity"] in SCHEMA_NO_DDB_TABLE_LOOKUP:
        return errors
    
    if 'listMultiSelect' in attribute and attribute['listMultiSelect']:
        validate_multi_select_relationship(item, attribute, key, errors)
    else:
        validate_single_relationship(item, attribute, key, errors)
       
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


def validate_attribute(attribute, item, key, errors):
    if attribute['type'] == 'list' and 'listvalue' in attribute:
        errors = validate_list_type_attribute(item, attribute, key, errors)
    elif attribute['type'] == 'relationship':
        errors = validate_relationship_type_attribute(item, attribute, key, errors)
    elif attribute['type'] == 'tag':
        errors = validate_tag_type_attribute(item, attribute, key, errors)
    else:
        errors = validate_other_type_attribute(item, attribute, key, errors)

    return errors


def validate_item_keys_and_values(item, schema):
    errors = []

    for key in item.keys():
        check = False
        if key.startswith('_'):
            #  Ignore system keys.
            continue
        for attribute in schema:
            if key == attribute['name']:
                check = True
                errors = validate_attribute(attribute, item, key, errors)
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


def does_item_with_name_exist(new_item_key, new_item_value, data_table):
    try:
        # Query the NameIndex GSI
        response = data_table.query(
            IndexName='NameIndex', # NameIndex should be set on all tables. If not, it will scan
            KeyConditionExpression=Key(new_item_key).eq(new_item_value),
            Limit=1
        )
        return len(response.get('Items', [])) > 0
    except Exception as e:
        print(f"Error querying NameIndex: {str(e)}")
        # Fall back to scan if GSI doesn't exist
        response = data_table.scan(
            FilterExpression=Attr(new_item_key).eq(new_item_value),
            Limit=1
        )
        return len(response.get('Items', [])) > 0


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


def check_valid_rule_create(item):
    validation_errors = []

    rule_type = item.get('rule_type')
    sub_type = item.get('sub_type')

    if rule_type == 'PRIORITIZING':
        # Conditional required fields based on sub_type
        if sub_type == 'SCORING':
            if not item.get('scoring_criteria'):
                validation_errors.append('scoring_criteria is required when sub_type is SCORING')
            elif isinstance(item['scoring_criteria'], list):
                for i, criteria in enumerate(item['scoring_criteria']):
                    complexity_score = criteria.get('complexity_score')
                    try:
                        complexity_score = float(complexity_score)
                        if not (0 <= complexity_score <= 100):
                            validation_errors.append(
                                f'scoring_criteria[{i}].complexity_score must be a number between 0 and 100'
                            )
                    except (ValueError, TypeError):
                        validation_errors.append(
                            f'scoring_criteria[{i}].complexity_score must be a number between 0 and 100'
                        )

        elif sub_type == 'SORTING':
            if not item.get('sort_order'):
                validation_errors.append('sort_order is required when sub_type is SORTING')
            sort_level = item.get('sort_level')
            if sort_level is None:
                validation_errors.append('sort_level is required when sub_type is SORTING')

    # Validate GROUPING rules
    elif rule_type in ['GROUPING_INCLUSIVE', 'GROUPING_EXCLUSIVE']:
        relationships = item.get('relationships')
        if not relationships:
            validation_errors.append('relationships is required for GROUPING rules')
        elif not isinstance(relationships, list):
            validation_errors.append('relationships must be a list')
        else:
            for i, relationship in enumerate(relationships):
                if not isinstance(relationship, dict):
                    validation_errors.append(f'relationships[{i}] must be an object')
                    continue

                if not relationship.get('asset_type'):
                    validation_errors.append(f'relationships[{i}].asset_type is required')
                if not relationship.get('asset_key'):
                    validation_errors.append(f'relationships[{i}].asset_key is required')

                # TODO: Validate asset_key values exist in the schema
                valid_asset_types = ['app', 'database', 'server']  # Add more if needed
                if relationship.get('asset_type') and relationship['asset_type'] not in valid_asset_types:
                    validation_errors.append(
                        f"relationships[{i}].asset_type must be one of: {', '.join(valid_asset_types)}"
                    )
        if not item.get('status') or item['status'] not in ['ENABLED', 'DISABLED']:
            validation_errors.append("status must be one of: ENABLED, DISABLED")

        if 'rule_description' in item and not isinstance(item['rule_description'], str):
            validation_errors.append('rule_description must be a string')
            
    else:
        validation_errors.append('rule_type must be one of: PRIORITIZING, GROUPING_INCLUSIVE, GROUPING_EXCLUSIVE')

    return validation_errors


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


# Input validation utilities

# Validation constants
MAX_STRING_LENGTH = 255
MAX_LIST_COUNT = 200
ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def validate_id_string(value: str, field_name: str) -> str:
    """Validate an ID string field. Returns error message or None if valid."""
    if not isinstance(value, str):
        return f"{field_name} must be a string"
    if not value.strip():
        return f"{field_name} cannot be empty"
    if len(value) > MAX_STRING_LENGTH:
        return f"{field_name} exceeds maximum length of {MAX_STRING_LENGTH}"
    if not ID_PATTERN.match(value):
        return f"{field_name} must contain only alphanumeric characters, dashes, and underscores"
    return None


def validate_id_list(values: list, field_name: str, max_count: int = MAX_LIST_COUNT) -> str:
    """Validate a list of ID strings. Returns error message or None if valid."""
    if not isinstance(values, list):
        return f"{field_name} must be a list"
    if not values:
        return f"{field_name} cannot be empty"
    if len(values) > max_count:
        return f"Too many {field_name}. Maximum allowed is {max_count}"
    
    for value in values:
        error = validate_id_string(value, f"Item in {field_name}")
        if error:
            return error
    
    if len(set(values)) != len(values):
        return f"Duplicate {field_name} not allowed"
    
    return None