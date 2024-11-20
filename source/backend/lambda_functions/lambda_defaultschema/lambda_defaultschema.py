#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import traceback
from datetime import datetime, timezone
import json
import os

import requests

import cmf_boto
from cmf_logger import logger


application = os.environ['application']
environment = os.environ['environment']
ROLE_TABLE = os.getenv('RoleDynamoDBTable')
SCHEMA_TABLE = os.getenv('SchemaDynamoDBTable')
POLICY_TABLE = os.getenv('PolicyDynamoDBTable')
PIPELINE_TEMPLATE_TABLE = os.getenv('PipelineTemplateDynamoDBTable')
SCRIPTS_TABLE = os.getenv('ScriptsDynamoDBTable')
PIPELINE_TEMPLATE_TASK_TABLE = os.getenv('PipelineTemplateTaskDynamoDBTable')

SCHEMAS_TO_OVERWRITE_DURING_UPDATE = ['ssm_job', 'job', 'mgn', 'policy', 'group', 'user', 'role', 'secret']

# Load default schema from json.
with open('default_schema.json') as json_schema_file:
    default_schema = json.load(json_schema_file)

# Load default policies from json.
with open('default_policies.json') as json_policies_file:
    default_policies = json.load(json_policies_file)

# Load default roles from json.
with open('default_roles.json') as json_roles_file:
    default_roles = json.load(json_roles_file)

# Load default tasks from json.
with open('default_tasks.json') as json_tasks_file:
    default_tasks = json.load(json_tasks_file)

# Load default pipeline templates and associated tasks from json.
with open('default_pipeline_templates_import.json') as json_pipeline_templates_file:
    default_pipeline_templates = json.load(json_pipeline_templates_file)


lambda_client = cmf_boto.client('lambda')


def load_default_pipeline_templates_and_tasks():
    import_event = {
        'httpMethod': 'POST',
        'body': json.dumps(default_pipeline_templates),
        'requestContext': {'authorizer':
            {'claims':
                {
                    'cognito:groups': ['admin'],
                    'cognito:username' : '[system]',
                    'email': '[system]'
                }
            }
        }
    }

    import_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-import_export_pipeline',
                                        InvocationType='RequestResponse',
                                        Payload=json.dumps(import_event))

    logger.info(import_response)


def add_last_modified_attributes(item):
    timestamp = {
        "S": datetime.now(timezone.utc).isoformat()
    }
    identity = {
        "M": {
            # The identity is currently coupled with an email string.
            # Setting a default value for now to be displayed on the console.
            "email": {
                "S": "[system]"
            }
        }
    }
    item['_history'] = {
        "M": {
            "lastModifiedBy": identity,
            "lastModifiedTimestamp": timestamp,
            "createdBy": identity,
            "createdByTimestamp": timestamp
        }
    }
    return item


def load_cmf_system_defaults():
    client = cmf_boto.client('dynamodb')

    logger.info("Loading default schemas")
    for item in default_schema:
        client.put_item(
            TableName=SCHEMA_TABLE,
            Item=item
        )

    logger.info("Loading default roles")
    for item in default_roles:
        client.put_item(
            TableName=ROLE_TABLE,
            Item=item
        )

    logger.info("Loading default policies")
    for item in default_policies:
        client.put_item(
            TableName=POLICY_TABLE,
            Item=item
        )

    logger.info("Loading default scripts")
    for item in default_tasks:
        client.put_item(
            TableName=SCRIPTS_TABLE,
            Item=add_last_modified_attributes(item)
        )

    logger.info("Loading default pipeline templates")
    load_default_pipeline_templates_and_tasks()


def update_schema(ddb_client, existing_schemas, updated_schema):

    existing_schema = next((existing_schema for existing_schema in existing_schemas if existing_schema["schema_name"]["S"] == updated_schema["schema_name"]["S"]), None)

    if existing_schema:
        if existing_schema["schema_name"]["S"] in SCHEMAS_TO_OVERWRITE_DURING_UPDATE:
            logger.info(f'Overwriting existing schema : {existing_schema["schema_name"]["S"]}')
        else:
            logger.info(f'Updating existing schema : {existing_schema["schema_name"]["S"]}')
            # Search existing schema and append any custom attributes to the new schema.
            for existing_attribute in existing_schema["attributes"]["L"]:
                updated_attribute = next(
                    (updated_schema_attribute for updated_schema_attribute in updated_schema["attributes"]["L"] if updated_schema_attribute["M"]["name"]["S"] == existing_attribute["M"]["name"]["S"]), None)

                if updated_attribute and updated_attribute["M"]['name']["S"] == "aws_accountid":
                    # If aws_accountid attribute, copy existing account Ids to updated schema.
                    logger.info(f'Preserved existing account Ids for attribute update: {existing_attribute["M"]["name"]["S"]}')
                    updated_attribute["M"]["listvalue"]["S"] = existing_attribute["M"]["listvalue"]["S"]
                elif not updated_attribute:
                    # attribute does not existing in updated schema, will be copied.
                    logger.info(f'Preserved existing attribute not present in updated system schema: {existing_attribute["M"]["name"]["S"]}')
                    updated_schema["attributes"]["L"].append(existing_attribute)
                else:
                    logger.info(f'Attribute overwritten with updated system schema: {existing_attribute["M"]["name"]["S"]}')
    else:
        logger.info(f'Adding new schema : {updated_schema["schema_name"]["S"]}')

    # apply new schema.
    ddb_client.put_item(
        TableName=SCHEMA_TABLE,
        Item=updated_schema
    )


def merge_updated_and_existing_polices(existing_entity_access_policy, updated_entity_access):
    # This is an existing schema in the policy.
    logger.info(
        f'Merging existing entity access for entity: {existing_entity_access_policy["M"]["schema_name"]["S"]} with updated system policy')
    for existing_attribute_access in existing_entity_access_policy["M"].get('attributes',{}).get("L", []):
        updated_attribute_access = next(
            (updated_attribute_access for updated_attribute_access in updated_entity_access["M"].get('attributes',{}).get("L", []) if
             updated_attribute_access["M"]["attr_name"]["S"] == existing_attribute_access["M"]["attr_name"]["S"]), None)
        if not updated_attribute_access:
            # entity access is present in policy and not in updated policy, preserving access.
            logger.info(
                f'Preserved existing attribute access {existing_attribute_access["M"]["attr_name"]["S"]} for schema {existing_entity_access_policy["M"]["schema_name"]["S"]}, not present in updated system policy.')
            if "attributes" not in updated_entity_access["M"]:
                updated_entity_access["M"]["attributes"] = {"L": []}
            updated_entity_access["M"]["attributes"]["L"].append(existing_attribute_access)


def update_policy(ddb_client, existing_policies, updated_policy):

    existing_policy = next((existing_policy for existing_policy in existing_policies if existing_policy["policy_name"]["S"] == updated_policy["policy_name"]["S"]), None)

    if existing_policy:
        logger.info(
            f'Updating existing policy: {existing_policy["policy_name"]["S"]}')
        # Search existing schema and merge existing with new where required.
        for existing_entity_access_policy in existing_policy['entity_access']["L"]:
            updated_entity_access = next(
                (updated_entity_access_schema for updated_entity_access_schema in updated_policy['entity_access']["L"] if updated_entity_access_schema["M"]["schema_name"]["S"] == existing_entity_access_policy["M"]["schema_name"]["S"]), None)

            if updated_entity_access:
                merge_updated_and_existing_polices(existing_entity_access_policy, updated_entity_access)
            else:
                # attribute does not existing in updated schema, will be copied.
                logger.info(f'Preserved existing entity access not present in updated system policy: {existing_entity_access_policy["M"]["schema_name"]["S"]}')
                updated_policy['entity_access']["L"].append(existing_entity_access_policy)

    # apply updated policy.
    ddb_client.put_item(
        TableName=POLICY_TABLE,
        Item=updated_policy
    )


def update_policies(ddb_client):
    existing_policies = get_all_ddb_table_items(POLICY_TABLE)

    logger.info("Updating default policies")
    for updated_policy in default_policies:
        update_policy(ddb_client, existing_policies, updated_policy)


def update_schemas(ddb_client):
    existing_schemas = get_all_ddb_table_items(SCHEMA_TABLE)

    logger.info("Updating default schemas")
    for item in default_schema:
        update_schema(ddb_client, existing_schemas, item)


def update_cmf_system_defaults():
    ddb_client = cmf_boto.client('dynamodb')

    update_schemas(ddb_client)

    logger.info("Replacing default roles")
    for item in default_roles:
        ddb_client.put_item(
            TableName=ROLE_TABLE,
            Item=item
        )

    update_policies(ddb_client)

    logger.info("Replacing default integration tasks")
    for item in default_tasks:
        ddb_client.put_item(
            TableName=SCRIPTS_TABLE,
            Item=add_last_modified_attributes(item)
        )

    logger.info("Replacing default pipeline templates")
    load_default_pipeline_templates_and_tasks()


def get_all_ddb_table_items(ddb_table_name):
    client_ddb = cmf_boto.client('dynamodb')
    response = client_ddb.scan(
        TableName=ddb_table_name,
        ConsistentRead=True
    )
    ddb_table_items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = client_ddb.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        ddb_table_items.extend(response['Items'])

    return ddb_table_items


def lambda_handler(event, context):
    try:
        logger.info('Event:\n {}'.format(event))
        logger.info('Context:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            logger.info('Create action')
            load_cmf_system_defaults()
            status = 'SUCCESS'
            message = 'Default schema loaded successfully'

        elif event['RequestType'] == 'Update':
            logger.info('Update action')
            update_cmf_system_defaults()
            status = 'SUCCESS'
            message = 'No update required'

        elif event['RequestType'] == 'Delete':
            logger.info('Delete action')
            status = 'SUCCESS'
            message = 'No deletion required'

        else:
            logger.info('SUCCESS!')
            status = 'SUCCESS'
            message = 'Unexpected event received from CloudFormation'

    except Exception as e:
        logger.info('FAILED!')
        logger.info(e)
        status = 'FAILED'
        message = 'Exception during processing'
        traceback.print_exc()

    response_data = {'Message': message}
    response = respond(event, context, status, response_data)

    return {
        'Response': response
    }


def respond(event, context, response_status, response_data):
    # Build response payload required by CloudFormation
    response_body = {}
    response_body['Status'] = response_status
    response_body['Reason'] = 'Details in: ' + context.log_stream_name
    response_body['PhysicalResourceId'] = context.log_stream_name
    response_body['StackId'] = event['StackId']
    response_body['RequestId'] = event['RequestId']
    response_body['LogicalResourceId'] = event['LogicalResourceId']
    response_body['Data'] = response_data

    # Convert json object to string and log it
    json_response_body = json.dumps(response_body)
    logger.info('Response body: {}'.format(str(json_response_body)))

    # Set response URL
    response_url = event['ResponseURL']

    # Set headers for preparation for a PUT
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    # Return the response to the signed S3 URL
    try:
        response = requests.put(response_url,
                                data=json_response_body,
                                headers=headers,
                                timeout=30)

        logger.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        logger.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'
