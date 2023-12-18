#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import boto3
import os
from unittest import TestCase, mock
from moto import mock_dynamodb, mock_sts, mock_iam
import test_lambda_mgn_common_util
from test_lambda_mgn_common_util import default_mock_os_environ, \
mock_get_user_resource_creation_policy_deny, \
mock_get_user_resource_creation_policy_allow, \
mock_boto_api_call, \
mock_get_servers, \
mock_update_ec2_launch_template
from test_common_utils import create_and_populate_servers, \
create_and_populate_apps
from cmf_logger import logger


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_dynamodb
@mock_sts
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

        self.event["body"] = {"waveid":"1","action":"Validate Launch Template","appidlist":["2"]}
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
    @mock_sts
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
    @mock_sts
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

    @mock_sts
    @mock_iam
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

    @mock_sts
    @mock_iam
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgn.MFAuth.get_user_resource_creation_policy', 
                new=mock_get_user_resource_creation_policy_allow)
    @mock.patch('lambda_mgn.get_servers', new=mock_get_servers)
    @mock.patch('lambda_mgn.update_ec2_launch_template', new=mock_update_ec2_launch_template)
    def test_lambda_hander_manage_mgn_actions_valid_launch_template(self):
        logger.info("Testing test_lambda_mgn: "
                    "test_lambda_hander_manage_mgn_actions_valid_launch_template")
        from lambda_mgn import lambda_handler

        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_disconnected'
        
        response = lambda_handler(self.event, {})
        logger.debug(f"Response: {response}")
        self.assertEqual(response, None)

        # Reset to default configuration
        test_lambda_mgn_common_util.MGN_TEST_SCENARIO = 'default'

    @mock_sts
    @mock_iam
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

    @mock_sts
    @mock_iam
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

    @mock_sts
    @mock_iam
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

    @mock_sts
    @mock_iam
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

    @mock_sts
    @mock_iam
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

    @mock_sts
    @mock_iam
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