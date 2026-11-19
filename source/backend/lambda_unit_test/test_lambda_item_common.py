#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import unittest
from unittest import mock

import boto3
from moto import mock_aws

import test_common_utils
from test_common_utils import logger, default_mock_os_environ as mock_os_environ


def mock_item_check_valid_item_create_valid(item, schema, related_items=None):
    logger.debug(f'mock_item_check_valid_item_create({item}, {schema}, {related_items})')
    return None


def mock_item_check_valid_item_create_in_valid(item, schema, related_items=None):
    logger.debug(f'mock_item_check_valid_item_create({item}, {schema}, {related_items})')
    return ['Simulated error, attribute x is required']

@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaItemCommonTest(unittest.TestCase):

    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        self.ddb_client = boto3.client('dynamodb')
        self.schema_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-schema'
        self.apps_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-apps'
        self.servers_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-servers'
        self.apps_ulid_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-app_ulids'
        self.move_groups_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-move_groups'
        self.wpm_jobs_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-wpm_jobs'
        self.waves_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-waves'
        self.pipeline_templates_table_name = \
            f'{os.environ["application"]}-{os.environ["environment"]}-pipeline_templates'
        self.pipeline_template_tasks_table_name = \
            f'{os.environ["application"]}-{os.environ["environment"]}-pipeline_template_tasks'
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name)
        test_common_utils.create_and_populate_apps(self.ddb_client, self.apps_table_name)
        test_common_utils.create_and_populate_servers(self.ddb_client, self.servers_table_name)
        test_common_utils.create_and_populate_apps_ulid(self.ddb_client, self.apps_ulid_table_name)
        test_common_utils.create_and_populate_move_groups(self.ddb_client, self.move_groups_table_name)
        test_common_utils.create_and_populate_wpm_jobs(self.ddb_client, self.wpm_jobs_table_name)
        test_common_utils.create_and_populate_waves(self.ddb_client, self.waves_table_name)
        
        # Create rules table for composite key testing
        self.rules_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-rules'
        test_common_utils.create_and_populate_rules(self.ddb_client, self.rules_table_name)
        
        self.apps_table = boto3.resource('dynamodb').Table(self.apps_table_name)
        self.servers_table = boto3.resource('dynamodb').Table(self.servers_table_name)
        self.app_ulids_table = boto3.resource('dynamodb').Table(self.apps_ulid_table_name)
        self.move_groups_table = boto3.resource('dynamodb').Table(self.move_groups_table_name)
        self.pipeline_templates_table = boto3.resource('dynamodb').Table(self.pipeline_templates_table_name)
        self.pipeline_templates_tasks_table = boto3.resource('dynamodb').Table(
            self.pipeline_template_tasks_table_name)
        self.rules_table = boto3.resource('dynamodb').Table(self.rules_table_name)

        self.event_schema_no_exist = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'NO_EXIST'
            }
        }
