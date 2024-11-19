#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import unittest
from unittest import mock

import boto3

from test_common_utils import LambdaContextFnArn, test_account_id, default_mock_os_environ, logger
import test_common_utils


class LambdaGFCommonTest(unittest.TestCase):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self, test_module):
        super().setUp()
        self.servers_table_name = test_module.servers_table_name
        self.apps_table_name = test_module.apps_table_name
        self.waves_table_name = test_module.waves_table_name
        self.ddb_client = boto3.client('dynamodb')
        self.s3_client = boto3.client('s3')
        self.create_and_populate_tables()
        self.account_id = test_account_id
        self.wave_id = '1'
        self.bucket_name = '-'.join([os.getenv('application'), os.getenv('environment'), self.account_id,
                                     'gfbuild-cftemplates'])
        self.create_bucket()

        self.lambda_context = LambdaContextFnArn(
            'arn:aws:lambda:us-east-1:' + self.account_id + ':function:migration-factory-lab-test')
        self.lambda_event_good = {
            'body': json.dumps({
                'waveid': self.wave_id,
                'accountid': self.account_id,
            })
        }

    def create_bucket(self):
        self.s3_client.create_bucket(Bucket=self.bucket_name)

    def upload_to_s3(self, file_name, bucket, key):
        self.s3_client.upload_file(file_name, bucket, key)

    def create_and_populate_tables(self):
        test_common_utils.create_and_populate_servers(self.ddb_client, self.servers_table_name)
        test_common_utils.create_and_populate_apps(self.ddb_client, self.apps_table_name)
        test_common_utils.create_and_populate_waves(self.ddb_client, self.waves_table_name)

    def create_replatform_role(self):
        iam_client = boto3.client('iam')
        role_name = 'Factory-Replatform-EC2Deploy'
        policy_name = 'ReplatformRolePolicy'
        trust_relationship_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'AWS': 'arn:aws:iam::' + self.account_id + ':root'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_relationship_policy)
        )

        policy_json = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': [
                        'iam:PassRole',
                        'sts:AssumeRole'
                    ],
                    'Resource': '*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'cloudformation:DescribeStacks',
                        'cloudformation:CreateStack',
                        'cloudformation:UpdateStack'
                    ],
                    'Resource': '*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        's3:GetObject'
                    ],
                    'Resource': [
                        'arn:aws:s3:::migration-factory-*-*-gfbuild-cftemplates',
                        'arn:aws:s3:::migration-factory-*-*-gfbuild-cftemplates/*',
                        'arn:aws:s3:::*'
                    ],
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'kms:ListAliases',
                        'kms:DescribeKey'
                    ],
                    'Resource': '*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'iam:GetInstanceProfile',
                        'ec2:DescribeAccountAttributes',
                        'ec2:DescribeAvailabilityZones',
                        'ec2:DescribeImages',
                        'ec2:DescribeInstances',
                        'ec2:DescribeInstanceTypes',
                        'ec2:DescribeInstanceAttribute',
                        'ec2:DescribeInstanceStatus',
                        'ec2:DescribeInstanceTypeOfferings',
                        'ec2:DescribeLaunchTemplateVersions',
                        'ec2:DescribeLaunchTemplates',
                        'ec2:DescribeSecurityGroups',
                        'ec2:DescribeSnapshots',
                        'ec2:DescribeSubnets',
                        'ec2:DescribeVolumes',
                        'ec2:GetEbsEncryptionByDefault',
                        'ec2:GetEbsDefaultKmsKeyId'
                    ],
                    'Resource': '*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'ec2:CreateVolume',
                        'ec2:DeleteVolume',
                        'ec2:DetachVolume',
                        'ec2:AttachVolume',
                        'ec2:ModifyVolumeAttribute'
                    ],
                    'Resource': 'arn:aws:ec2:*:*:volume/*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'ec2:RunInstances',
                        'ec2:StartInstances',
                        'ec2:StopInstances',
                        'ec2:TerminateInstances',
                        'ec2:ModifyInstanceAttribute',
                        'ec2:DetachVolume',
                        'ec2:AttachVolume'
                    ],
                    'Resource': 'arn:aws:ec2:*:*:instance/*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'ec2:RevokeSecurityGroupEgress',
                        'ec2:AuthorizeSecurityGroupIngress',
                        'ec2:AuthorizeSecurityGroupEgress'
                    ],
                    'Resource': 'arn:aws:ec2:*:*:security-group/*',
                    'Effect': 'Allow'
                },
                {
                    'Action': 'ec2:CreateSecurityGroup',
                    'Resource': 'arn:aws:ec2:*:*:vpc/*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'ec2:CreateSecurityGroup'
                    ],
                    'Resource': 'arn:aws:ec2:*:*:security-group/*',
                    'Effect': 'Allow'
                },
                {
                    'Action': [
                        'ec2:RunInstances'
                    ],
                    'Resource': [
                        'arn:aws:ec2:*:*:security-group/*',
                        'arn:aws:ec2:*:*:volume/*',
                        'arn:aws:ec2:*:*:subnet/*',
                        'arn:aws:ec2:*:*:image/*',
                        'arn:aws:ec2:*:*:network-interface/*',
                        'arn:aws:ec2:*:*:launch-template/*',
                        'arn:aws:ec2:*:*:instance/*'
                    ],
                    'Effect': 'Allow'
                },
                {
                    'Condition': {
                        'StringEquals': {
                            'ec2:CreateAction': [
                                'CreateSecurityGroup',
                                'CreateVolume',
                                'CreateSnapshot',
                                'RunInstances'
                            ]
                        }
                    },
                    'Action': 'ec2:CreateTags',
                    'Resource': [
                        'arn:aws:ec2:*:*:security-group/*',
                        'arn:aws:ec2:*:*:volume/*',
                        'arn:aws:ec2:*:*:snapshot/*',
                        'arn:aws:ec2:*:*:instance/*'
                    ],
                    'Effect': 'Allow'
                }
            ]
        }
        policy_res = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_json)
        )
        policy_arn = policy_res['Policy']['Arn']
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )

    def assert_lambda_handler_mfAuth_deny(self, test_module, mock_MFAuth):
        auth_response = {'action': 'deny'}
        mock_MFAuth.return_value = auth_response
        response = test_module.lambda_handler({}, None)
        self.assertEqual(401, response['statusCode'])
        self.assertEqual(auth_response, json.loads(response['body']))

    def assert_lambda_handler_no_wave_id(self, test_module):
        event = {
            'body': json.dumps({
                'no_waveid': self.wave_id,
                'accountid': self.account_id,
            })
        }
        response = test_module.lambda_handler(event, None)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('waveid is required', response['body'])

    def assert_lambda_handler_no_account_id(self, test_module):
        event = {
            'body': json.dumps({
                'waveid': self.wave_id,
                'no_accountid': self.account_id,
            })
        }
        response = test_module.lambda_handler(event, None)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Target AWS Account Id is required', response['body'])

    def assert_lambda_handler_malformed_input(self, test_module):
        event = {
            'body': 'malformed'
        }
        response = test_module.lambda_handler(event, None)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('malformed json input', response['body'])

    def assert_lambda_hander_no_table(self, test_module, table_name_attr_name, message, status_code):
        # simulate dynamo db scan error (or no error) by setting the table to None
        table_bak = getattr(test_module, table_name_attr_name)
        setattr(test_module, table_name_attr_name, None)
        response = test_module.lambda_handler(self.lambda_event_good, self.lambda_context)
        self.assertEqual(status_code, response['statusCode'])
        self.assertEqual(message, response['body'])
        self.assertEqual(test_module.default_http_headers, response['headers'])
        # restore the table
        setattr(test_module, table_name_attr_name, table_bak)

    def assert_lambda_hander_no_table_fail(self, test_module, table_name_attr_name, error_message):
        # simulate dynamo db scan error by setting the table to None
        self.assert_lambda_hander_no_table(test_module, table_name_attr_name, error_message, 400)

    def assert_lambda_handler_exception_main(self, test_module):
        lambda_context_bad = "lambda_context_in_wrong_format"
        response = test_module.lambda_handler(self.lambda_event_good, lambda_context_bad)
        self.assertEqual(400, response['statusCode'])
        self.assertTrue(response['body'].startswith('Lambda Handler Main Function Failed with error'))
        self.assertEqual(test_module.default_http_headers, response['headers'])

    def assert_lambda_handler_non_existent_wave_id(self, test_module):
        wave_id = '101'
        event = {
            'body': json.dumps({
                'waveid': wave_id,
                'accountid': self.account_id,
            })
        }

        response = test_module.lambda_handler(event, self.lambda_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('ERROR: Server list for wave 101 in Migration Factory is empty....', response['body'])

    def assert_servers_table_updated(self, servers_table, message):
        items_response = servers_table.scan(Limit=10)
        updated_items = [item for item in items_response['Items']
                         if item['r_type'].upper() == 'REPLATFORM' and item['migration_status'] == message]
        self.assertEqual(2, len(updated_items))


def mock_getUserResourceCreationPolicy(obj, event, schema):
    return {'action': 'allow', 'user': 'testuser@testuser'}
