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


def create_and_populate_tasks(ddb_client, tasks_table_name, data_file_name='tasks.json'):
    ddb_client.create_table(
        TableName=tasks_table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'task_execution_id', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'task_execution_id', 'AttributeType': 'S'},
            {'AttributeName': 'pipeline_id', 'AttributeType': 'S'},
            {'AttributeName': 'task_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {"IndexName": "pipeline_id-index",
             "KeySchema": [
                 {"AttributeName": "pipeline_id", "KeyType": "HASH"},
                 {"AttributeName": "task_id", "KeyType": "HASH"}
             ],
             "Projection": {
                 "ProjectionType": "ALL"}
             }
        ]
    )
    populate_table(ddb_client, tasks_table_name, data_file_name)


def create_and_populate_servers(ddb_client, servers_table_name, data_file_name='servers.json'):
    ddb_client.create_table(
        TableName=servers_table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'server_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'server_id', 'AttributeType': 'S'},
            {'AttributeName': 'app_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {'IndexName': 'app_id-index',
             'KeySchema': [
                 {'AttributeName': 'app_id', 'KeyType': 'HASH'}
             ],
             'Projection': {
                 'ProjectionType': 'ALL'}
             }
        ]
    )
    populate_table(ddb_client, servers_table_name, data_file_name)


def create_and_populate_apps(ddb_client, apps_table_name, data_file_name='apps.json'):
    ddb_client.create_table(
        TableName=apps_table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'app_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'app_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'app_id-index',
                'KeySchema': [
                    {
                        'AttributeName': 'app_id',
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ]
    )
    populate_table(ddb_client, apps_table_name, data_file_name)


def create_and_populate_pipeline_templates(ddb_client, table_name, data_file_name=None):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'pipeline_template_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pipeline_template_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'pipeline_template_id-index',
                'KeySchema': [
                    {
                        'AttributeName': 'pipeline_template_id',
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ]
    )
    if data_file_name:
        populate_table(ddb_client, table_name, data_file_name)


def create_and_populate_pipeline_template_tasks(ddb_client, table_name, data_file_name=None):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'pipeline_template_task_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pipeline_template_task_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'pipeline_template_task_id-index',
                'KeySchema': [
                    {
                        'AttributeName': 'pipeline_template_task_id',
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ]
    )
    if data_file_name:
        populate_table(ddb_client, table_name, data_file_name)

def create_and_populate_waves(ddb_client, waves_table_name, data_file_name='waves.json'):
    ddb_client.create_table(
        TableName=waves_table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'wave_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'wave_id', 'AttributeType': 'S'},
        ]
    )
    populate_table(ddb_client, waves_table_name, data_file_name)


def create_and_populate_schemas(ddb_client, schemas_table_name, data_file_name='schemas.json'):
    ddb_client.create_table(
        TableName=schemas_table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'schema_name', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'schema_name', 'AttributeType': 'S'},
        ]
    )
    populate_table(ddb_client, schemas_table_name, data_file_name)


def create_and_populate_policies(ddb_client, policies_table_name, data_file_name='policies.json'):
    ddb_client.create_table(
        TableName=policies_table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'policy_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'policy_id', 'AttributeType': 'S'},
        ]
    )
    populate_table(ddb_client, policies_table_name, data_file_name)


def create_and_populate_roles(ddb_client, table_name, data_file_name='roles.json'):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'role_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'role_id', 'AttributeType': 'S'},
        ]
    )
    populate_table(ddb_client, table_name, data_file_name)


def create_and_populate_ssm_jobs(ddb_client, table_name, data_file_name='ssm_jobs.json'):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'SSMId', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'SSMId', 'AttributeType': 'S'},
        ]
    )
    populate_table(ddb_client, table_name, data_file_name)


def create_and_populate_connection_ids(ddb_client, table_name, data_file_name='connection_ids.json'):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'connectionId', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'connectionId', 'AttributeType': 'S'},
        ]
    )
    populate_table(ddb_client, table_name, data_file_name)


def create_and_populate_ssm_scripts(ddb_client, table_name, data_file_name='ssm_scripts.json'):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {"AttributeName": "package_uuid", "KeyType": "HASH"},
            {"AttributeName": "version", "KeyType": "RANGE"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "package_uuid", "AttributeType": "S"},
            {"AttributeName": "version", "AttributeType": "N"},
        ],
        GlobalSecondaryIndexes=[
            {"IndexName": "version-index",
             "KeySchema": [
                 {"AttributeName": "version", "KeyType": "HASH"}
             ],
             "Projection": {
                 "ProjectionType": "ALL"}
             }
        ]
    )
    populate_table(ddb_client, table_name, data_file_name)


def create_and_populate_pipelines(ddb_client, table_name, data_file_name='pipelines.json'):
    ddb_client.create_table(
        TableName=table_name,
        BillingMode='PAY_PER_REQUEST',
        KeySchema=[
            {'AttributeName': 'pipeline_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pipeline_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'pipeline_id-index',
                'KeySchema': [
                    {
                        'AttributeName': 'pipeline_id',
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ]
    )
    if data_file_name:
        populate_table(ddb_client, table_name, data_file_name)


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


def mock_get_mf_auth_policy_allow(obj, event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_allow({obj}, {event}, {schema})')
    return {'action': 'allow', 'user': 'testuser@example.com'}


def mock_get_mf_auth_policy_allow_no_user(obj, event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_allow_no_user({obj}, {event}, {schema})')
    return {'action': 'allow'}


def mock_get_mf_auth_policy_default_deny(obj, event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_default_deny({obj}, {event}, {schema})')
    return {'action': 'deny', 'cause': 'Request is not Authenticated'}
