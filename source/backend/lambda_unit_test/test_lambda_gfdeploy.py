#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
from unittest import mock
from unittest.mock import patch

from moto import mock_dynamodb, mock_s3, mock_sts, mock_iam

from test_lambda_gfcommon import LambdaGFCommonTest, mock_getUserResourceCreationPolicy, logger, default_mock_os_environ

import botocore

orig_botocore_make_api_call = botocore.client.BaseClient._make_api_call


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_dynamodb
@mock_s3
@mock_sts
@mock_iam
class LambdaGFDeployTest(LambdaGFCommonTest):
    CreateStackCalledWith = []

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self):
        import lambda_gfdeploy
        super().setUp(lambda_gfdeploy)
        LambdaGFDeployTest.CreateStackCalledWith = []

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_mfAuth_deny(self, mock_MFAuth):
        import lambda_gfdeploy
        self.assert_lambda_handler_mfAuth_deny(lambda_gfdeploy, mock_MFAuth)

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_wave_id(self):
        import lambda_gfdeploy
        self.assert_lambda_handler_no_wave_id(lambda_gfdeploy)

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_account_id(self):
        import lambda_gfdeploy
        self.assert_lambda_handler_no_account_id(lambda_gfdeploy)

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_malformed_input(self):
        import lambda_gfdeploy
        self.assert_lambda_handler_malformed_input(lambda_gfdeploy)

    def mock_boto_api_call(client, operation_name, kwargs):
        logger.debug(f"operation_name = {operation_name}, kwarg = {kwargs}")
        if operation_name == 'CreateStack':
            LambdaGFDeployTest.CreateStackCalledWith.append(kwargs)
            return {
                'StackId': 'ID_' + kwargs['StackName']
            }
        else:
            return orig_botocore_make_api_call(client, operation_name, kwargs)

    # mock cloudformation calls because the createstack call with templateURL fails on moto's mock_cloudformation
    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_success(self):
        import lambda_gfdeploy
        self.upload_to_s3(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/CFN_Template_1_Wordpress.yaml',
                          self.bucket_name,
                          '111111111111/Wave1/CFN_Template_1_Wordpress.yaml')
        self.upload_to_s3(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/CFN_Template_2_OFBiz.yaml',
                          self.bucket_name,
                          '111111111111/Wave1/CFN_Template_2_OFBiz.yaml')
        self.create_replatform_role()
        response = lambda_gfdeploy.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual('EC2 Deployment has been completed', response['body'])
        # since the mock function isn't available with new, assert the captured parameters
        self.assertEqual(2, len(LambdaGFDeployTest.CreateStackCalledWith))
        actual_call_params = sorted([call['StackName'] for call in LambdaGFDeployTest.CreateStackCalledWith])
        expected_call_params = sorted(
            ['Create-EC2-Servers-for-App-Id-2OFBiz', 'Create-EC2-Servers-for-App-Id-1Wordpress'])
        self.assertEqual(expected_call_params, actual_call_params)
        self.assert_servers_table_updated(lambda_gfdeploy.servers_table, 'CF Deployment Submitted')

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_non_existent_wave_id(self):
        import lambda_gfdeploy
        wave_id = '101'
        event = {
            'body': json.dumps({
                'waveid': wave_id,
                'accountid': self.account_id,
            })
        }

        response = lambda_gfdeploy.lambda_handler(event, self.lambda_context)
        # this doesn't result in an error!
        self.assertEqual(200, response['statusCode'])
        self.assertEqual('EC2 Deployment has been completed', response['body'])

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_apps_table(self):
        import lambda_gfdeploy
        self.assert_lambda_hander_no_table_fail(lambda_gfdeploy,
                                                'apps_table',
                                                'Unable to Retrieve Data from Dynamo DB App Table')

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_servers_table(self):
        import lambda_gfdeploy
        self.assert_lambda_hander_no_table_fail(lambda_gfdeploy,
                                                'servers_table',
                                                'Unable to Retrieve Data from Dynamo DB Server Table')

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_waves_table(self):
        import lambda_gfdeploy
        self.assert_lambda_hander_no_table_fail(lambda_gfdeploy,
                                                'waves_table',
                                                'Unable to Retrieve Data from Dynamo DB Wave Table')

    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_exception_main(self):
        import lambda_gfdeploy
        self.assert_lambda_handler_exception_main(lambda_gfdeploy)

    @mock.patch('lambda_gfdeploy.launch_stack')
    @mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_exception_launch_stack(self, mock_launch_stack):
        import lambda_gfdeploy
        error_launch_stack = 'ERROR in launch_stack'
        mock_launch_stack.return_value = error_launch_stack
        response = lambda_gfdeploy.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(error_launch_stack, response['body'])
