#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import boto3
import os
from unittest import TestCase, mock
from moto import mock_aws
import test_lambda_mgn_common_util
from test_lambda_mgn_common_util import default_mock_os_environ, \
    mock_get_user_resource_creation_policy_deny, \
    mock_get_user_resource_creation_policy_allow, \
    mock_boto_api_call, \
    mock_get_servers, \
    mock_update_ec2_launch_template, \
    mock_get_mgn_launch_template_id, \
    mock_multiprocessing_update_success
from test_common_utils import create_and_populate_servers, \
    create_and_populate_apps
from cmf_logger import logger


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_aws
class MGNLambdaTestCase(TestCase):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self):
        # Initialize lambda event
        logger.debug("Setup start")
        self.event = {
            "resource": "/mgn",
            "path": "/mgn",
            "httpMethod": "POST",
            "headers": {
                "Accept": "application/json, text/plain, */*",
                "accept-encoding": "gzip, deflate, br"
            },
            "body": """{
                "waveid": "1",
                "action": "Validate Launch Template",
                "appidlist": [
                    "2"
                ]
            }"""
        }

        # Initialize Dynamodb tables
        self.ddb_client = boto3.client('dynamodb')
        self.iam_client = boto3.client('iam')
        self.servers_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-servers'
        self.apps_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-apps'
        create_and_populate_servers(self.ddb_client, self.servers_table_name)
        create_and_populate_apps(self.ddb_client, self.apps_table_name)
        logger.debug("Setup complete")

    def tearDown(self):
        pass

    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_deny)
    def test_lambda_handler_with_deny_action(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_handler_with_deny_action")
        from lambda_mgn import lambda_handler

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 401)

    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_with_allow_action_and_invalid_json_body(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_handler_with_allow_action_and_invalid_json_body")
        from lambda_mgn import lambda_handler

        self.event["body"] = {"waveid": "1", "action": "Validate Launch Template", "appidlist": ["2"]}
        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_with_allow_action_and_invalid_ddb_table(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_handler_with_allow_action_and_invalid_ddb_table")
        from lambda_mgn import lambda_handler

        self.ddb_client.delete_table(TableName=self.servers_table_name)
        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

        # Reset to default config
        create_and_populate_servers(self.ddb_client, self.servers_table_name)

    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_with_allow_action_and_invalid_sec_token(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_handler_with_allow_action_and_invalid_sec_token")
        from lambda_mgn import lambda_handler

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_with_allow_action_and_multi_processing_error(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_handler_with_allow_action_and_multi_processing_error")
        from lambda_mgn import lambda_handler

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_with_allow_action_and_disconnected_state_and_missing_template(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_handler_with_allow_action_and_disconnected_state_and_missing_template")
        from lambda_mgn import lambda_handler
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

        # Reset to default configuration
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    def test_lambda_handler_with_allow_action_and_disconnected_state_and_invalid_credentials(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_handler_with_allow_action_and_disconnected_state_and_invalid_credentials")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

        # Reset to default configuration
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn_template.multiprocessing_update', new=mock_multiprocessing_update_success)
    @mock.patch('lambda_mgn.get_mgn_launch_template_id', new=mock_get_mgn_launch_template_id)
    def test_lambda_hander_manage_mgn_actions_valid_launch_template(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_valid_launch_template")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        expected_response = {
            'headers':
                {'Access-Control-Allow-Origin': 'test-cors',
                 'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
                 'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
                 },
            'statusCode': 200,
            'body': '"SUCCESS: Launch templates validated for all servers in this Wave"'
        }
        self.assertEqual(response, expected_response)

        # Reset to default configuration
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_lambda_hander_manage_mgn_actions_launch_test_instances_succeeded(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_launch_test_instances_succeeded")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'

        self.initial_event = self.event
        self.event["body"] = """{
                "waveid": "1",
                "action": "Launch Test Instances",
                "appidlist": [
                    "2"
                ]
            }"""

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 200)

        # Reset to default configuration
        self.event = self.initial_event
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_lambda_hander_manage_mgn_actions_launch_test_instances_failed(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_launch_test_instances_failed")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'
        test_lambda_mgn_common_util.MGN_SERVER_ACTION_SCENARIO = \
            'launch_server_failed'

        self.initial_event = self.event
        self.event["body"] = """{
                "waveid": "1",
                "action": "Launch Test Instances",
                "appidlist": [
                    "2"
                ]
            }"""

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

        # Reset to default configuration
        self.event = self.initial_event
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'
        test_lambda_mgn_common_util.MGN_SERVER_ACTION_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_lambda_hander_manage_mgn_actions_launch_cutover_instances_succeeded(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_launch_cutover_instances_succeeded")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'

        self.initial_event = self.event
        self.event["body"] = """{
                "waveid": "1",
                "action": "Launch Cutover Instances",
                "appidlist": [
                    "2"
                ]
            }"""

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 200)

        # Reset to default configuration
        self.event = self.initial_event
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_lambda_hander_manage_mgn_actions_launch_cutover_instances_failed(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_launch_cutover_instances_failed")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'
        test_lambda_mgn_common_util.MGN_SERVER_ACTION_SCENARIO = \
            'launch_server_failed'

        self.initial_event = self.event
        self.event["body"] = """{
                "waveid": "1",
                "action": "Launch Cutover Instances",
                "appidlist": [
                    "2"
                ]
            }"""

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

        # Reset to default configuration
        self.event = self.initial_event
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'
        test_lambda_mgn_common_util.MGN_SERVER_ACTION_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_lambda_hander_manage_mgn_actions_terminate_instances_succeeded(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_terminate_instances_succeeded")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'

        self.initial_event = self.event
        self.event["body"] = """{
                "waveid": "1",
                "action": "- Terminate Launched instances",
                "appidlist": [
                    "2"
                ]
            }"""

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 200)

        # Reset to default configuration
        self.event = self.initial_event
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_lambda_hander_manage_mgn_actions_terminate_instances_failed(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_terminate_instances_failed")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'
        test_lambda_mgn_common_util.MGN_SERVER_ACTION_SCENARIO = \
            'launch_server_failed'

        self.initial_event = self.event
        self.event["body"] = """{
                "waveid": "1",
                "action": "- Terminate Launched instances",
                "appidlist": [
                    "2"
                ]
            }"""

        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response.get("statusCode"), 400)

        # Reset to default configuration
        self.event = self.initial_event
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'
        test_lambda_mgn_common_util.MGN_SERVER_ACTION_SCENARIO = 'default'

    @mock_aws
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_filter_items_with_item_ids(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_filter_items_success")
        from lambda_mgn import filter_items

        items = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'},
            {'id': 3, 'name': 'Item 3'},
            {'id': 4, 'name': 'Item 4'}
        ]
        item_ids = [1, 3]
        key = 'id'
        expected_output = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 3, 'name': 'Item 3'}
        ]
        self.assertEqual(filter_items(items, key, item_ids), expected_output)

    def test_filter_items_without_item_ids(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_filter_items_without_item_ids")
        from lambda_mgn import filter_items

        items = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'},
            {'id': 3, 'name': 'Item 3'},
            {'id': 4, 'name': 'Item 4'}
        ]
        key = 'id'

        self.assertEqual(filter_items(items, key), items)

    def test_filter_items_with_empty_list(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_filter_items_with_empty_list")
        from lambda_mgn import filter_items

        items = []
        key = 'id'
        item_ids = [1, 2]

        self.assertEqual(filter_items(items, key, item_ids), [])

    # get_mgn_launch_template_id test needed as threaded
    # @mock_aws
    # @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    # def test_get_mgn_launch_template_id(self):
    #     logger.info("Testing test_get_mgn_launch_template_id_success")
    #     from lambda_mgn import get_mgn_launch_template_id
    #
    #     get_mgn_launch_template_id()
    #
    #     items = [
    #         {'id': 1, 'name': 'Item 1'},
    #         {'id': 2, 'name': 'Item 2'},
    #         {'id': 3, 'name': 'Item 3'},
    #         {'id': 4, 'name': 'Item 4'}
    #     ]
    #     item_ids = [1, 3]
    #     key = 'id'
    #     expected_output = [
    #         {'id': 1, 'name': 'Item 1'},
    #         {'id': 3, 'name': 'Item 3'}
    #     ]
    #     self.assertEqual(filter_items(items, key, item_ids), expected_output)

    # multiprocessing_update test needed as threaded
