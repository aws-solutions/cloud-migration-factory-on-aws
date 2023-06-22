#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################


import json
import os
import unittest
from unittest import mock

import boto3
from moto import mock_dynamodb, mock_s3

import common_utils
common_utils.init()
logger = common_utils.logger

mock_os_environ = {
    'AWS_ACCESS_KEY_ID': 'testing',
    'AWS_SECRET_ACCESS_KEY': 'testing',
    'AWS_SECURITY_TOKEN': 'testing',
    'AWS_SESSION_TOKEN': 'testing',
    'AWS_DEFAULT_REGION': 'us-east-1',
    'region': 'us-east-1',
    'application': 'cmf',
    'environment': 'unittest',
}


@mock.patch.dict('os.environ', mock_os_environ)
@mock_dynamodb
@mock_s3
class LambdaGFBuildTest(unittest.TestCase):

    class LambdaContext:
        def __init__(self, invoked_function_arn):
            self.invoked_function_arn = invoked_function_arn

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self):
        super().setUp()
        import lambda_gfbuild
        self.servers_table_name = lambda_gfbuild.servers_table_name
        self.apps_table_name = lambda_gfbuild.apps_table_name
        self.waves_table_name = lambda_gfbuild.waves_table_name
        self.ddb_client = boto3.client('dynamodb')
        self.s3_client = boto3.client('s3')
        self.create_and_populate_tables()
        self.account_id = '11111111111'
        self.wave_id = '1'
        self.bucket_name = '-'.join([os.getenv('application'), os.getenv('environment'), self.account_id,
                                     'gfbuild-cftemplates'])
        self.create_bucket()

        self.lambda_context = LambdaGFBuildTest.LambdaContext('arn:aws:lambda:us-east-1:' + self.account_id + ':function:migration-factory-lab-test')
        self.lambda_event_good = {
            'body': json.dumps({
                    'waveid': self.wave_id,
                    'accountid': self.account_id,
                })
        }

    def create_bucket(self):
        self.s3_client.create_bucket(Bucket=self.bucket_name)
    def create_and_populate_tables(self):
        self.create_and_populate_servers()
        self.create_and_populate_apps()
        self.create_and_populate_waves()

    def create_and_populate_servers(self):
        self.ddb_client.create_table(
            TableName=self.servers_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "server_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "server_id", "AttributeType": "S"},
                {"AttributeName": "app_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {"IndexName": "app_id-index",
                 "KeySchema": [
                     {"AttributeName": "app_id", "KeyType": "HASH"}
                 ],
                 "Projection": {
                     "ProjectionType": "ALL"}
                 }
            ]
        )
        self.populate_table(self.servers_table_name, 'servers.json')

    def create_and_populate_apps(self):
        self.ddb_client.create_table(
            TableName=self.apps_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "app_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "app_id", "AttributeType": "S"},
            ]
        )
        self.populate_table(self.apps_table_name, 'apps.json')

    def create_and_populate_waves(self):
        self.ddb_client.create_table(
            TableName=self.waves_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "wave_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "wave_id", "AttributeType": "S"},
            ]
        )
        self.populate_table(self.waves_table_name, 'waves.json')

    def populate_table(self, table_name, sample_data_file_name):
        with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/' + sample_data_file_name) as json_file:
            sample_items = json.load(json_file)
        for item in sample_items:
            self.ddb_client.put_item(
                TableName=table_name,
                Item=item
            )
    def mock_getUserResourceCreationPolicy(self, event, schema):
        return {'action': 'allow', 'user': 'testuser@testuser'}

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy')
    def test_lambda_handler_mfAuth_deny(self, mock_MFAuth):
        import lambda_gfbuild
        auth_response = {'action': 'deny'}
        mock_MFAuth.return_value = auth_response
        response = lambda_gfbuild.lambda_handler(None, None)
        self.assertEqual(401, response['statusCode'])
        self.assertEqual(auth_response, json.loads(response['body']))

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_wave_id(self):
        import lambda_gfbuild
        event = {
            'body': json.dumps({
                    'no_waveid': self.wave_id,
                    'accountid': self.account_id,
                })
        }
        response = lambda_gfbuild.lambda_handler(event, None)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('waveid is required', response['body'])

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_account_id(self):
        import lambda_gfbuild
        event = {
            'body': json.dumps({
                    'waveid': self.wave_id,
                    'no_accountid': self.account_id,
                })
        }
        response = lambda_gfbuild.lambda_handler(event, None)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Target AWS Account Id is required', response['body'])

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_malformed_input(self):
        import lambda_gfbuild
        event = {
            'body': 'malformed'
        }
        response = lambda_gfbuild.lambda_handler(event, None)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('malformed json input', response['body'])

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
        with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/cfn_generated_1.yaml') as yaml_file:
            expected_template_as_str = yaml_file.read()
        self.assertEqual(expected_template_as_str, template_as_str)


    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_non_existent_wave_id(self):
        import lambda_gfbuild
        wave_id = '101'
        event = {
            'body': json.dumps({
                    'waveid': wave_id,
                    'accountid': self.account_id,
                })
        }

        response = lambda_gfbuild.lambda_handler(event, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('ERROR: Server list for wave ' + wave_id + ' in Migration Factory is empty....', response['body'])


    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_apps_table(self):
        import lambda_gfbuild
        # simulate dynamo db scan error by setting the apps table to None
        table_bak = lambda_gfbuild.apps_table
        lambda_gfbuild.apps_table = None
        response = lambda_gfbuild.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('ERROR: Unable to Retrieve Data from Dynamo DB App table', response['body'])
        self.assertEqual(lambda_gfbuild.default_http_headers, response['headers'])
        # restore the table
        lambda_gfbuild.apps_table = table_bak

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_apps_table(self):
        import lambda_gfbuild
        # simulate dynamo db scan error by setting the servers table to None
        table_bak = lambda_gfbuild.servers_table
        lambda_gfbuild.servers_table = None
        response = lambda_gfbuild.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('ERROR: Unable to Retrieve Data from Dynamo DB Server table', response['body'])
        self.assertEqual(lambda_gfbuild.default_http_headers, response['headers'])
        # restore the table
        lambda_gfbuild.servers_table = table_bak

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_waves_table(self):
        import lambda_gfbuild
        # simulate dynamo db scan error by setting the waves table to None
        # similar to test_lambda_handler_no_apps_table, but the error handling is in different location
        table_bak = lambda_gfbuild.waves_table
        lambda_gfbuild.waves_table = None
        response = lambda_gfbuild.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Unable to Retrieve Data from Dynamo DB Wave Table', response['body'])
        self.assertEqual(lambda_gfbuild.default_http_headers, response['headers'])
        # restore the table
        lambda_gfbuild.waves_table = table_bak

    @mock.patch('lambda_gfbuild.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_exception_main(self):
        import lambda_gfbuild
        lambda_context_bad = "lambda_context_in_wrong_format"
        response = lambda_gfbuild.lambda_handler(self.lambda_event_good, lambda_context_bad)
        self.assertEqual(400, response['statusCode'])
        self.assertTrue(response['body'].startswith('Lambda Handler Main Function Failed with error'))
        self.assertEqual(lambda_gfbuild.default_http_headers, response['headers'])

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
