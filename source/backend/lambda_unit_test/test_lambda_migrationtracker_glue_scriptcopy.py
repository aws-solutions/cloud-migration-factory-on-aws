#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import mock
from unittest.mock import patch

from moto import mock_glue, mock_s3
import boto3

from test_lambda_migrationtracker_glue_base import mock_os_environ, RequestsResponse, LambdaMigrationTrackerGlueBaseTest

SIMULATED_EXCEPTION_STRING = 'Simulated Exception'

@mock.patch.dict('os.environ', mock_os_environ)
@mock_glue
@mock_s3
class LambdaMigrationTrackerGlueTest(LambdaMigrationTrackerGlueBaseTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self):
        super().setUp()
        import lambda_migrationtracker_glue_scriptcopy
        self.s3_client = boto3.client('s3')
        self.remote_bucket_name = os.environ.get('remote_bucket')
        self.local_bucket_name = os.environ.get('local_bucket')
        self.key_prefix = os.environ.get('key_prefix')
        self.ref_file_name = 'Migration_Tracker_All_Extract_Script.py'
        self.set_up_buckets()
        self.success_message = 'Copy Glue Script to local bucket on CFN creation'

    def set_up_buckets(self):
        import lambda_migrationtracker_glue_scriptcopy
        self.s3_client.create_bucket(Bucket=self.remote_bucket_name)
        self.s3_client.create_bucket(Bucket=self.local_bucket_name)
        for glue_file in lambda_migrationtracker_glue_scriptcopy.GLUE_JOBS:
            self.s3_client.upload_file(
                os.path.dirname(os.path.realpath(__file__)) +
                '/sample_data/Migration_Tracker_All_Extract_Script.py',
                self.remote_bucket_name, f'{self.key_prefix}/Migration_Tracker_{glue_file}_Extract_Script.py'
            )

    def assert_s3_file_contents(self, bucket_name, reference_file_name, s3_file_name):
        file_obj_in_s3 = self.s3_client.get_object(Bucket=bucket_name,
                                                   Key='GlueScript/' + s3_file_name)
        file_as_str = file_obj_in_s3['Body'].read().decode('utf-8')
        with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/' + reference_file_name) as yaml_file:
            expected_file_as_str = yaml_file.read()
        self.assertEqual(expected_file_as_str, file_as_str)

    def assert_lambda_handler_success(self, lambda_event, mock_requests,
                                      message='Copy Glue Script to local bucket on CFN creation'):
        import lambda_migrationtracker_glue_scriptcopy
        response_status = 'OK'
        mock_requests.put.return_value = RequestsResponse(response_status)
        response = lambda_migrationtracker_glue_scriptcopy.lambda_handler(lambda_event, self.lamda_context)
        self.assert_requests_called_with_success(mock_requests, message)
        self.assert_response(response)
        if lambda_event == self.event_create or lambda_event == self.event_update:
            s3_objects = self.s3_client.list_objects_v2(Bucket=self.local_bucket_name, Prefix='GlueScript')
            self.assertEqual(4, len(s3_objects['Contents']))
            for glue_file in lambda_migrationtracker_glue_scriptcopy.GLUE_JOBS:
                self.assert_s3_file_contents(
                    self.local_bucket_name,
                    self.ref_file_name,
                    f'Migration_Tracker_{glue_file}_Extract_Script.py'
                )

    @patch('lambda_migrationtracker_glue_scriptcopy.requests')
    def test_lambda_hanndler_create_success(self, mock_requests):
        self.assert_lambda_handler_success(self.event_create, mock_requests)

    @patch('lambda_migrationtracker_glue_scriptcopy.requests')
    def test_lambda_hanndler_update_success(self, mock_requests):
        self.assert_lambda_handler_success(self.event_update, mock_requests)

    @patch('lambda_migrationtracker_glue_scriptcopy.requests')
    @patch('lambda_migrationtracker_glue_scriptcopy.copy_glue_script_to_local')
    def test_lambda_handler_delete_success(self, mock_copy_glue_script_to_local, mock_requests):
        import lambda_migrationtracker_glue_scriptcopy
        response = lambda_migrationtracker_glue_scriptcopy.lambda_handler(self.event_delete, self.lamda_context)
        mock_copy_glue_script_to_local.assert_not_called()
        self.assert_response(response)
        self.assert_requests_called_with_success(mock_requests, 'No cleanup is required for this function')

    @patch('lambda_migrationtracker_glue_scriptcopy.requests')
    @patch('lambda_migrationtracker_glue_scriptcopy.copy_glue_script_to_local')
    def test_lambda_handler_unknown_success(self, mock_copy_glue_script_to_local, mock_requests):
        import lambda_migrationtracker_glue_scriptcopy
        response = lambda_migrationtracker_glue_scriptcopy.lambda_handler(self.event_unknown, self.lamda_context)
        mock_copy_glue_script_to_local.assert_not_called()
        self.assert_response(response)
        self.assert_requests_called_with_success(mock_requests, 'Unknown request type')

    @patch('lambda_migrationtracker_glue_scriptcopy.requests')
    def test_lambda_handler_create_swallowed_exception(self, mock_requests):
        import lambda_migrationtracker_glue_scriptcopy
        mock_requests.put.side_effect = Exception(SIMULATED_EXCEPTION_STRING)
        response = lambda_migrationtracker_glue_scriptcopy.lambda_handler(self.event_create, self.lamda_context)
        self.assert_requests_called_with_success(mock_requests, self.success_message)
        self.assert_response(response)

    @patch('lambda_migrationtracker_glue_scriptcopy.requests')
    @patch('lambda_migrationtracker_glue_scriptcopy.copy_glue_script_to_local')
    def test_lambda_handler_exception(self, mock_copy_glue_script_to_local, mock_requests):
        import lambda_migrationtracker_glue_scriptcopy
        mock_copy_glue_script_to_local.side_effect = Exception(SIMULATED_EXCEPTION_STRING)
        mock_requests.put.return_value = RequestsResponse('OK')
        response = lambda_migrationtracker_glue_scriptcopy.lambda_handler(self.event_create, self.lamda_context)
        self.assert_requests_called_with_failure(mock_requests, 'Exception: Simulated Exception')
        self.assert_response(response)

    @patch('lambda_migrationtracker_glue_scriptcopy.requests')
    @patch('lambda_migrationtracker_glue_scriptcopy.copy_glue_script_to_local')
    def test_lambda_handler_exception_with_physical_resource_id(self, mock_copy_glue_script_to_local, mock_requests):
        import lambda_migrationtracker_glue_scriptcopy
        mock_copy_glue_script_to_local.side_effect = Exception(SIMULATED_EXCEPTION_STRING)
        mock_requests.put.return_value = RequestsResponse('OK')
        self.event_create['PhysicalResourceId'] = self.event_create['LogicalResourceId']
        response = lambda_migrationtracker_glue_scriptcopy.lambda_handler(self.event_create, self.lamda_context)
        self.assert_requests_called_with_failure(mock_requests, 'Exception: Simulated Exception')
        self.assert_response(response)
