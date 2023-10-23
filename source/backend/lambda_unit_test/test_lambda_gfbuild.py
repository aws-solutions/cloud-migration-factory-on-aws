#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
from unittest import mock

from moto import mock_dynamodb, mock_s3

from test_lambda_gfcommon import LambdaGFCommonTest, mock_getUserResourceCreationPolicy, default_mock_os_environ


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_dynamodb
@mock_s3
class LambdaGFBuildTest(LambdaGFCommonTest):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self):
        import lambda_gfbuild
        super().setUp(lambda_gfbuild)

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy')
    def test_lambda_handler_mfAuth_deny(self, mock_MFAuth):
        import lambda_gfbuild
        self.assert_lambda_handler_mfAuth_deny(lambda_gfbuild, mock_MFAuth)

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_wave_id(self):
        import lambda_gfbuild
        self.assert_lambda_handler_no_wave_id(lambda_gfbuild)


    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_account_id(self):
        import lambda_gfbuild
        self.assert_lambda_handler_no_account_id(lambda_gfbuild)

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_malformed_input(self):
        import lambda_gfbuild
        self.assert_lambda_handler_malformed_input(lambda_gfbuild)

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_success(self):
        import lambda_gfbuild
        response = lambda_gfbuild.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(200, response['statusCode'])
        response_body = response['body']
        response_message_start = 'EC2 Cloud Formation Template Generation Completed. 2 template S3 URIs created:'
        self.assertTrue(response_body.startswith(response_message_start))
        # check the generated template(s) are uploaded to S3
        buckets = self.s3_client.list_buckets()
        self.assertEqual(1, len(buckets['Buckets']))
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.account_id)
        self.assertEqual(2, len(s3_objects['Contents']))
        template_obj_in_s3 = self.s3_client.get_object(Bucket=self.bucket_name, Key='111111111111/Wave1/CFN_Template_1_Wordpress.yaml')
        template_as_str = template_obj_in_s3['Body'].read().decode('utf-8')
        with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/CFN_Template_1_Wordpress.yaml') as yaml_file:
            expected_template_as_str = yaml_file.read()
        self.assertEqual(expected_template_as_str, template_as_str)
        self.assert_servers_table_updated(lambda_gfbuild.servers_table, 'CF Template Generated')

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_non_existent_wave_id(self):
        import lambda_gfbuild
        self.assert_lambda_handler_non_existent_wave_id(lambda_gfbuild)

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_apps_table(self):
        import lambda_gfbuild
        self.assert_lambda_hander_no_table_fail(lambda_gfbuild,
                                                'apps_table',
                                                'ERROR: Unable to Retrieve Data from Dynamo DB App table')

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_servers_table(self):
        import lambda_gfbuild
        self.assert_lambda_hander_no_table_fail(lambda_gfbuild,
                                                'servers_table',
                                                'ERROR: Unable to Retrieve Data from Dynamo DB Server table')

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_waves_table(self):
        import lambda_gfbuild
        self.assert_lambda_hander_no_table_fail(lambda_gfbuild,
                                                'waves_table',
                                                'Unable to Retrieve Data from Dynamo DB Wave Table')

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_exception_main(self):
        import lambda_gfbuild
        self.assert_lambda_handler_exception_main(lambda_gfbuild)

    @mock.patch('lambda_gfbuild.Template')
    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_get_server_list_fail(self, mock_template):
        import lambda_gfbuild
        test_exception_message = 'Simulated template object creation error in get server list'
        mock_template.side_effect = Exception(test_exception_message)
        response = lambda_gfbuild.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('ERROR: Getting server list failed. Failed with Error:' + test_exception_message, response['body'])
        self.assertEqual(lambda_gfbuild.default_http_headers, response['headers'])

    @mock.patch('lambda_gfbuild.Template.add_output')
    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_template_gen_fail(self, mock_template):
        import lambda_gfbuild
        test_exception_message = 'Simulated Template Generation Error'
        mock_template.side_effect = Exception(test_exception_message)
        response = lambda_gfbuild.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('ERROR: EC2 CFT Template Generation Failed With Error: ' + test_exception_message, response['body'])
        self.assertEqual(lambda_gfbuild.default_http_headers, response['headers'])
