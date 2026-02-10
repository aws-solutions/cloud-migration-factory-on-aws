#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import sys

from aws_lambda_powertools.utilities.typing import LambdaContext


def init():
    import os

    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    import sys
    from pathlib import Path

    file = Path(__file__).resolve()
    package_root_directory = file.parents[1]
    for directory in os.listdir(str(package_root_directory) + '/lambda_layers/'):
        sys.path.append(str(package_root_directory) + '/lambda_layers/' + directory + '/python')
    for directory in os.listdir(str(package_root_directory) + '/lambda_functions/'):
        sys.path.append(str(package_root_directory) + '/lambda_functions/' + directory)
    from cmf_logger import logger
    logger.debug(f'sys.path: {list(sys.path)}')


init()
from cmf_logger import logger

default_mock_os_environ = {
    'AWS_ACCESS_KEY_ID': 'testing',
    'AWS_SECRET_ACCESS_KEY': 'testing',
    'AWS_SECURITY_TOKEN': 'testing',
    'AWS_SESSION_TOKEN': 'testing',
    'AWS_DEFAULT_REGION': 'us-east-1',
    'region': 'us-east-1',
    'application': 'cmf',
    'environment': 'unittest',
}


def create_and_populate_table(ddb_client, entity_name, table_name=None, pk_name=None, range_key=None, 
                             additional_attributes=None, gsi_keys=None, data_file_name=None):
    """
    Generic function to create and populate a DynamoDB table based on entity name
    
    Args:
        ddb_client: DynamoDB client
        entity_name: Base entity name (e.g., 'wave', 'app')
        table_name: Optional table name override (default: entity_name + 's')
        pk_name: Optional primary key name override (default: entity_name + '_id')
        range_key: Optional range key with format (name, type)
        additional_attributes: List of additional attribute names to define
        gsi_keys: List of GSI configurations
        data_file_name: Optional JSON file with data to populate the table
    """
    try:
        # Use conventions for table name and primary key
        actual_table_name = table_name or f"{entity_name}s"
        hash_key = pk_name or f"{entity_name}_id"
        name_key = f"{entity_name}_name"
        
        # Check if table already exists
        try:
            ddb_client.describe_table(TableName=actual_table_name)
            logger.info(f"Table {actual_table_name} already exists")
        except ddb_client.exceptions.ResourceNotFoundException:
            # Build key schema
            key_schema = [{'AttributeName': hash_key, 'KeyType': 'HASH'}]
            if range_key:
                key_schema.append({'AttributeName': range_key[0], 'KeyType': 'RANGE'})
            
            # Build attribute definitions
            attribute_definitions = [{'AttributeName': hash_key, 'AttributeType': 'S'},]
            if name_key != hash_key:
                attribute_definitions.append({'AttributeName': name_key, 'AttributeType': 'S'})
            if range_key:
                attribute_definitions.append({'AttributeName': range_key[0], 'AttributeType': range_key[1]})
            
            # Add additional attributes if specified
            if additional_attributes:
                for attr_name, attr_type in additional_attributes:
                    if not any(attr['AttributeName'] == attr_name for attr in attribute_definitions):
                        attribute_definitions.append({'AttributeName': attr_name, 'AttributeType': attr_type})
            
            # Build GSIs (including NameIndex GSI)
            global_secondary_indexes = [{
                "IndexName": "NameIndex",
                "KeySchema": [{"AttributeName": name_key, "KeyType" : "HASH"}],
                "Projection": { "ProjectionType": "KEYS_ONLY" }
            }]
            if gsi_keys:
                for gsi in gsi_keys:
                    gsi_hash = gsi.get('hash')
                    gsi_name = gsi.get('name', f"{gsi_hash}-index")
                    
                    gsi_schema = [{'AttributeName': gsi_hash, 'KeyType': 'HASH'}]
                    if 'range' in gsi:
                        gsi_schema.append({'AttributeName': gsi['range'], 'KeyType': 'RANGE'})
                    
                    global_secondary_indexes.append({
                        'IndexName': gsi_name,
                        'KeySchema': gsi_schema,
                        'Projection': {'ProjectionType': 'ALL'}
                    })
            
            # Create table
            create_params = {
                'TableName': actual_table_name,
                'BillingMode': 'PAY_PER_REQUEST',
                'KeySchema': key_schema,
                'AttributeDefinitions': attribute_definitions
            }
            
            create_params['GlobalSecondaryIndexes'] = global_secondary_indexes
                
            ddb_client.create_table(**create_params)
            
            # Wait for table to be created
            waiter = ddb_client.get_waiter('table_exists')
            waiter.wait(TableName=actual_table_name)
            logger.info(f"Created table {actual_table_name}")
        
        # Populate table if data file provided
        if data_file_name:
            populate_table(ddb_client, actual_table_name, data_file_name)
        
        return actual_table_name
    except Exception as e:
        logger.error(f"Error creating/populating table for entity {entity_name}: {str(e)}")
        raise


# Simplified table creation functions using the convention-based approach
def create_and_populate_tasks(ddb_client, tasks_table_name, data_file_name='tasks.json'):
    create_and_populate_table(
        ddb_client, 'task_execution', tasks_table_name,
        additional_attributes=[('pipeline_id', 'S'), ('task_id', 'S')],
        gsi_keys=[{'hash': 'pipeline_id', 'range': 'task_id'}],
        data_file_name=data_file_name
    )


def create_and_populate_servers(ddb_client, servers_table_name, data_file_name='servers.json'):
    create_and_populate_table(
        ddb_client, 'server', servers_table_name,
        data_file_name=data_file_name
    )


def create_and_populate_apps(ddb_client, apps_table_name, data_file_name='apps.json'):
    create_and_populate_table(
        ddb_client, 'app', apps_table_name,
        data_file_name=data_file_name
    )

def create_and_populate_apps_ulid(ddb_client, apps_ulid_table_name, data_file_name='apps_ulid.json'):
    create_and_populate_table(ddb_client, 'app_ulid', apps_ulid_table_name, data_file_name=data_file_name)


def create_and_populate_pipeline_templates(ddb_client, table_name, data_file_name=None):
    create_and_populate_table(
        ddb_client, 'pipeline_template', table_name,
        data_file_name=data_file_name
    )


def create_and_populate_pipeline_template_tasks(ddb_client, table_name, data_file_name=None):
    create_and_populate_table(
        ddb_client, 'pipeline_template_task', table_name,
        data_file_name=data_file_name
    )


def create_and_populate_waves(ddb_client, waves_table_name, data_file_name='waves.json'):
    create_and_populate_table(
        ddb_client, 'wave', waves_table_name,
        data_file_name=data_file_name
    )


def create_and_populate_schemas(ddb_client, schemas_table_name, data_file_name='schemas.json'):
    create_and_populate_table(
        ddb_client, 'schema', schemas_table_name,
        pk_name='schema_name',
        data_file_name=data_file_name
    )
    
    # Add rule schema for testing
    import boto3
    schema_table = boto3.resource('dynamodb').Table(schemas_table_name)
    schema_table.put_item(
        Item={
            'schema_name': 'rule',
            'schema_type': 'user',
            'attributes': [
                {'name': 'rule_type', 'type': 'string', 'required': True},
                {'name': 'rule_id', 'type': 'string', 'required': True},
                {'name': 'rule_name', 'type': 'string', 'required': True},
                {'name': 'status', 'type': 'string', 'required': True}
            ]
        }
    )


def create_and_populate_policies(ddb_client, policies_table_name, data_file_name='policies.json'):
    create_and_populate_table(
        ddb_client, 'policy', policies_table_name,
        data_file_name=data_file_name
    )


def create_and_populate_roles(ddb_client, table_name, data_file_name='roles.json'):
    create_and_populate_table(
        ddb_client, 'role', table_name,
        data_file_name=data_file_name
    )


def create_and_populate_ssm_jobs(ddb_client, table_name, data_file_name='ssm_jobs.json'):
    create_and_populate_table(
        ddb_client, 'ssm', table_name,
        pk_name='SSMId',
        data_file_name=data_file_name
    )


def create_and_populate_connection_ids(ddb_client, table_name, data_file_name='connection_ids.json'):
    create_and_populate_table(
        ddb_client, 'connection', table_name,
        pk_name='connectionId',
        data_file_name=data_file_name
    )


def create_and_populate_ssm_scripts(ddb_client, table_name, data_file_name='ssm_scripts.json'):
    create_and_populate_table(
        ddb_client, 'package', table_name,
        pk_name='package_uuid',
        range_key=('version', 'N'),
        gsi_keys=[{'hash': 'version'}],
        data_file_name=data_file_name
    )


def create_and_populate_pipelines(ddb_client, table_name, data_file_name='pipelines.json'):
    create_and_populate_table(
        ddb_client, 'pipeline', table_name,
        data_file_name=data_file_name
    )


def create_and_populate_move_groups(ddb_client, table_name, data_file_name='move_groups.json'):
    try:
        # Check if table already exists
        try:
            ddb_client.describe_table(TableName=table_name)
            print(f"Table {table_name} already exists")
        except ddb_client.exceptions.ResourceNotFoundException:
            # Create table if it doesn't exist
            ddb_client.create_table(
                TableName=table_name,
                BillingMode='PAY_PER_REQUEST',
                KeySchema=[
                    {'AttributeName': 'move_group_id', 'KeyType': 'HASH'},
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'move_group_id', 'AttributeType': 'S'},
                ]
            )
            # Wait for table to be created
            waiter = ddb_client.get_waiter('table_exists')
            waiter.wait(TableName=table_name)

        # Populate table
        populate_table(ddb_client, table_name, data_file_name)
    except Exception as e:
        print(f"Error creating/populating table {table_name}: {str(e)}")
        raise


def create_and_populate_wpm_jobs(ddb_client, table_name, data_file_name='wpm_jobs.json'):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'wpm_job_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'wpm_job_id', 'AttributeType': 'S'},
        ]
    )
    populate_table(ddb_client, table_name, data_file_name)


def create_and_populate_rules(ddb_client, table_name, data_file_name='rules.json'):
    """Create rules table with composite key for testing"""
    try:
        # Check if table already exists
        try:
            ddb_client.describe_table(TableName=table_name)
            logger.info(f"Table {table_name} already exists")
        except ddb_client.exceptions.ResourceNotFoundException:
            # Create table with composite key
            ddb_client.create_table(
                TableName=table_name,
                BillingMode='PAY_PER_REQUEST',
                KeySchema=[
                    {'AttributeName': 'rule_type', 'KeyType': 'HASH'},
                    {'AttributeName': 'rule_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'rule_type', 'AttributeType': 'S'},
                    {'AttributeName': 'rule_id', 'AttributeType': 'S'}
                ]
            )
            # Wait for table to be created
            waiter = ddb_client.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            logger.info(f"Created table {table_name}")
        
        # Populate table if data file exists
        if data_file_name:
            try:
                populate_table(ddb_client, table_name, data_file_name)
            except FileNotFoundError:
                logger.info(f"Data file {data_file_name} not found, skipping population")
    except Exception as e:
        logger.error(f"Error creating/populating table {table_name}: {str(e)}")
        raise


def populate_table(ddb_client, table_name, data_file_name):
    with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/' + data_file_name) as json_file:
        sample_items = json.load(json_file)
    for item in sample_items:
        ddb_client.put_item(
            TableName=table_name,
            Item=item
        )


def delete_table(ddb_client, table_name):
    ddb_client.delete_table(TableName=table_name)


# Classes matching types needed in this test case with duck typing
class RequestsResponse:
    def __init__(self, reason):
        self.reason = reason


class LambdaContextLogStream(LambdaContext):
    def __init__(self, log_stream_name):
        self._log_stream_name = log_stream_name


class LambdaContextFnArn(LambdaContext):
    def __init__(self, invoked_function_arn):
        self._invoked_function_arn = invoked_function_arn


# used to check whether a serialized object contains a key and value
# to be used in mock.call_with
class SerializedDictMatcher:
    def __init__(self, field_name, expected_value):
        self.field_name = field_name
        self.expected_value = expected_value

    def __eq__(self, other):
        dict_other = json.loads(other)
        return self.field_name in dict_other and dict_other[self.field_name] == self.expected_value


# almost in all lambdas os.environ['cors'] is set to * if not set already globally
# this utility function can be called before tests to achieve higher coverage from that global line
def set_cors_flag(test_package: str, value=True):
    if test_package in sys.modules:
        del sys.modules[test_package]
    if value:
        os.environ['cors'] = '*'
    else:
        if 'cors' in os.environ:
            del os.environ['cors']


test_account_id = '111111111111'


def mock_get_mf_auth_policy_allow(event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_allow({event}, {schema})')
    return {'action': 'allow', 'user': 'testuser@example.com'}


def mock_get_mf_auth_policy_allow_no_user(event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_allow_no_user({event}, {schema})')
    return {'action': 'allow'}


def mock_get_mf_auth_policy_default_deny(event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_default_deny({event}, {schema})')
    return {'action': 'deny', 'cause': 'Request is not Authenticated'}
