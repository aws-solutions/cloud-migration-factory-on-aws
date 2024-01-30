#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import unittest
from unittest import mock
from unittest.mock import patch

from test_common_utils import logger, default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'ssm_bucket': 'test_ssm_bucket',
    'ssm_automation_document': 'test_ssm_automation_document',
    'mf_userapi': 'test_mf_userapi',
    'mf_loginapi': 'test_mf_loginapi',
    'mf_toolsapi': 'test_mf_toolsapi',
    'userpool': 'test_userpool',
    'clientid': 'test_clientid',
    'mf_vpce_id': 'fd00:ec2::253'
}


class InstanceTypes:
    ManagedInstance = 'ManagedInstance'
    EC2Instance = 'EC2Instance'


class InstanceInfoIterator:

    def __init__(self):
        self.data = [
            {
                'InstanceInformationList': [
                    {
                        'InstanceId': 'instance_001',
                        'PingStatus': 'Online',
                        'ResourceType': InstanceTypes.ManagedInstance,
                        'ComputerName': 'instance_001'
                    }
                ]
            },
            {
                'InstanceInformationList': [
                    {
                        'InstanceId': 'instance_002',
                        'PingStatus': 'Online',
                        'ResourceType': InstanceTypes.ManagedInstance
                    }
                ]
            },
            {
                'InstanceInformationList': [
                    {
                        'InstanceId': 'instance_003',
                        'PingStatus': 'Online',
                        'ResourceType': InstanceTypes.EC2Instance
                    }
                ]
            },
            {
                'InstanceInformationList': [
                    {
                        'InstanceId': 'instance_004',
                        'PingStatus': 'Online',
                        'ResourceType': InstanceTypes.EC2Instance
                    }
                ]
            },
            {
                'InstanceInformationList': [
                    {
                        'InstanceId': 'instance_005',
                        'PingStatus': 'Offline',
                        'ResourceType': InstanceTypes.EC2Instance
                    }
                ]
            }
        ]

    def paginate(self, Filters=None, PaginationConfig=None):
        resource_type_filter = [f for f in Filters if f['Key'] == 'ResourceType'][0]['Values'][0]
        return [x for x in self.data if x['InstanceInformationList'][0]['ResourceType'] == resource_type_filter]


def mock_ssm_list_tags_for_resource(ResourceType, ResourceId):
    logger.debug(f'ResourceType = {ResourceType}, ResourceId = {ResourceId}')
    if ResourceId == 'instance_001':
        return {
            'TagList': [
                {
                    'Key': 'role',
                    'Value': 'mf_automation'
                }
            ]
        }
    else:
        return {
            'TagList': [
            ]
        }


def mock_ec2_describe_tags(Filters):
    if Filters[0]['Values'] == ['instance_003']:
        return {
            'Tags': [
                {
                    'Key': 'role',
                    'Value': 'mf_automation',
                    'ResourceType': 'instance',
                    'ResourceId': 'instance_003'
                }
            ]
        }
    else:
        return {
            'Tags': [
            ]
        }


def mock_getUserResourceCreationPolicy(event, schema):
    logger.debug(f'calling mock_getUserResourceCreationPolicy({event}, {schema})')
    return {'action': 'allow', 'user': 'testuser@testuser'}

def mock_getUserResourceCreationPolicyDeny(event, schema):
    logger.debug(f'calling mock_getUserResourceCreationPolicyDeny({event}, {schema})')
    return {'action': 'deny', 'user': 'testuser@testuser'}


def mock_lamda_invoke(FunctionName, InvocationType, Payload, ClientContext=None):
    logger.debug(f'mock_lamda_invoke({FunctionName}, {InvocationType}, {Payload}, {ClientContext})')

    class LambdaPaylod:
        def read(self):
            return json.dumps({
                'body': json.dumps([
                    {
                        'package_uuid': 'test_uuid_1',
                    },
                    {
                        'package_uuid': 'test_uuid_2',
                    }
                ])
            })

    return {
        'Payload': LambdaPaylod()
    }


def mock_start_automation_execution(DocumentName, DocumentVersion, Parameters):
    logger.debug(f'callig mock_start_automation_execution({DocumentName}, {DocumentVersion}, {Parameters})')
    return {
        'AutomationExecutionId': 'automation_101'
    }


@mock.patch.dict('os.environ', mock_os_environ)
class LambdaSSMTest(unittest.TestCase):

    def setUp(self) -> None:
        self.event_get = {
            'httpMethod': 'GET'
        }
        self.event_post_invalid = {
            'httpMethod': 'POST',
            'body': json.dumps({
            })
        }
        self.event_post_package_version_doesnt_exist = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'jobname': 'test_job',
                'mi_id': 'test_mi_id',
                'script': {
                    'package_uuid': 'test_uuid',
                    'script_version': 'test_version',
                    'script_arguments': [1, 2]
                }
            })
        }
        self.event_post_package_version_invalid = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'jobname': 'test_job',
                'mi_id': 'test_mi_id',
                'script': {
                    'package_uuid': 'test_uuid',
                    'script_version': '0',
                    'script_arguments': [1, 2]
                }
            })
        }
        self.event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'jobname': 'test_job',
                'mi_id': 'test_mi_id',
                'script': {
                    'package_uuid': 'test_uuid_1',
                    'script_version': '0',
                    'script_arguments': [1, 2]
                }
            })
        }

    @patch('lambda_ssm.ec2')
    @patch('lambda_ssm.ssm')
    def test_lambda_handler_get_success(self, mock_ssm, mock_ec2):
        import lambda_ssm
        mock_ssm.get_paginator.return_value = InstanceInfoIterator()
        mock_ssm.list_tags_for_resource.side_effect = mock_ssm_list_tags_for_resource
        mock_ec2.describe_tags.side_effect = mock_ec2_describe_tags
        response = lambda_ssm.lambda_handler(self.event_get, None)
        expected = {
            'headers': lambda_ssm.default_http_headers,
            'body': json.dumps([
                {
                    'mi_id': 'instance_001',
                    'online': True,
                    'mi_name': 'instance_001'
                },
                {
                    'mi_id': 'instance_003',
                    'online': True,
                    'mi_name': ''
                }
            ]),
        }
        self.assertEqual(expected, response)

    @patch('lambda_ssm.ec2')
    @patch('lambda_ssm.ssm')
    def test_lambda_handler_get_exception(self, mock_ssm, mock_ec2):
        os.environ['solution_identifier'] = 'SO101'
        import lambda_ssm
        mock_ssm.get_paginator.side_effect = Exception('Simulated Exception')
        self.assertRaises(Exception, lambda_ssm.lambda_handler, self.event_get, None)
        mock_ssm.list_tags_for_resource.assert_not_called()
        mock_ec2.describe_tags.assert_not_called()

    @patch('lambda_ssm.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_post_validation_error(self, mock_MFAuth):
        import lambda_ssm
        mock_MFAuth.side_effect = mock_getUserResourceCreationPolicy
        response = lambda_ssm.lambda_handler(self.event_post_invalid, None)
        expected = {
            'headers': lambda_ssm.default_http_headers,
            'statusCode': 400,
            'body': 'Request parameters missing: jobname,mi_id,script',
        }
        self.assertEqual(expected, response)

    @unittest.skip
    @patch('lambda_ssm.lambda_client')
    @patch('lambda_ssm.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_post_package_version_doesnt_exist(self, mock_MFAuth, mock_lamda):
        import lambda_ssm
        mock_MFAuth.side_effect = mock_getUserResourceCreationPolicy
        mock_lamda.invoke.side_effect = mock_lamda_invoke
        response = lambda_ssm.lambda_handler(self.event_post_package_version_doesnt_exist, None)
        expected = {
            'headers': lambda_ssm.default_http_headers,
            'statusCode': 400,
            'body': 'Invalid package uuid or version provided. \'test_uuid, version test_version \' does not exist.',
        }
        self.assertEqual(expected, response)

    @unittest.skip
    @patch('lambda_ssm.lambda_client')
    @patch('lambda_ssm.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_post_package_version_invalid(self, mock_MFAuth, mock_lamda):
        import lambda_ssm
        mock_MFAuth.side_effect = mock_getUserResourceCreationPolicy
        mock_lamda.invoke.side_effect = mock_lamda_invoke
        response = lambda_ssm.lambda_handler(self.event_post_package_version_invalid, None)
        expected = {
            'headers': lambda_ssm.default_http_headers,
            'statusCode': 400,
            'body': 'Invalid script uuid provided, using default version. UUID:\'test_uuid\' does not exist.',
        }
        self.assertEqual(expected, response)

    @patch('lambda_ssm.ssm')
    @patch('lambda_ssm.lambda_client')
    @patch('lambda_ssm.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_post_success(self, mock_MFAuth, mock_lamda, mock_ssm):
        import lambda_ssm
        mock_MFAuth.side_effect = mock_getUserResourceCreationPolicy
        mock_lamda.invoke.side_effect = mock_lamda_invoke
        mock_ssm.start_automation_execution = mock_start_automation_execution
        response = lambda_ssm.lambda_handler(self.event_post, None)
        self.assertEqual(lambda_ssm.default_http_headers, response['headers'])
        self.assertTrue('"SSMId: test_mi_id' in response['body'])

    @patch('lambda_ssm.ssm')
    @patch('lambda_ssm.lambda_client')
    @patch('lambda_ssm.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_post_unhandled_exception(self, mock_MFAuth, mock_lamda, mock_ssm):
        import lambda_ssm
        mock_MFAuth.side_effect = Exception('Simulated Exception')
        self.assertRaises(Exception, lambda_ssm.lambda_handler, self.event_post, None)
        mock_lamda.invoke.assert_not_called()
        mock_ssm.assert_not_called()

    @patch('lambda_ssm.ssm')
    @patch('lambda_ssm.lambda_client')
    @patch('lambda_ssm.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_post_handled_exception(self, mock_MFAuth, mock_lamda, mock_ssm):
        import lambda_ssm
        mock_MFAuth.side_effect = mock_getUserResourceCreationPolicy
        mock_lamda.invoke.side_effect = Exception('Simulated Exception')
        mock_ssm.start_automation_execution = Exception('Simulated Exception')
        response = lambda_ssm.lambda_handler(self.event_post, None)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(lambda_ssm.default_http_headers, response['headers'])

    @patch('lambda_ssm.ssm')
    @patch('lambda_ssm.lambda_client')
    @patch('lambda_ssm.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_post_mfauth_deny(self, mock_MFAuth, mock_lamda, mock_ssm):
        import lambda_ssm
        mock_MFAuth.side_effect = mock_getUserResourceCreationPolicyDeny
        response = lambda_ssm.lambda_handler(self.event_post, None)
        mock_lamda.invoke.assert_not_called()
        mock_ssm.assert_not_called()
        expected = {
            'headers': lambda_ssm.default_http_headers,
            'statusCode': 401,
            'body': '{"action": "deny", "user": "testuser@testuser"}',
        }
        self.assertEqual(expected, response)
