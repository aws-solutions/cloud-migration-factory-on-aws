#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import unittest
import boto3
from unittest import mock

from moto import mock_dynamodb, mock_s3
import test_common_utils
from test_common_utils import logger, default_mock_os_environ as mock_os_environ, \
    mock_get_mf_auth_policy_allow, mock_get_mf_auth_policy_default_deny


def mock_item_check_valid_item_create_valid(item, schema, related_items=None):
    logger.debug(f'mock_item_check_valid_item_create({item}, {schema}, {related_items})')
    return None


def mock_item_check_valid_item_create_in_valid(item, schema, related_items=None):
    logger.debug(f'mock_item_check_valid_item_create({item}, {schema}, {related_items})')
    return ['Simulated error, attribute x is required']

@mock.patch.dict('os.environ', mock_os_environ)
@mock_s3
@mock_dynamodb
class LambdaItemCommonTest(unittest.TestCase):

    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        self.ddb_client = boto3.client('dynamodb')
        self.schema_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-schema'
        self.apps_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-apps'
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name)
        test_common_utils.create_and_populate_apps(self.ddb_client, self.apps_table_name)
        self.apps_table = boto3.resource('dynamodb').Table(self.apps_table_name)

        self.event_schema_no_exist = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'NO_EXIST'
            }
        }
