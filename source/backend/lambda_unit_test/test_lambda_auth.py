#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0



import unittest
import boto3
import logging
import os
from unittest import TestCase, mock
from moto import mock_aws

# This is to get around the relative path import issue.
# Absolute paths are being used in this file after setting the root directory
import sys
from pathlib import Path

file = Path(__file__).resolve()
package_root_directory = file.parents[1]
sys.path.append(str(package_root_directory))
sys.path.append(str(package_root_directory) + '/lambda_layers/lambda_layer_policy/python/')
sys.path.append(str(package_root_directory) + '/lambda_layers/lambda_layer_auth/python/')

# Set log level
loglevel = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger(__name__)

default_http_headers = {
    'Access-Control-Allow-Origin': '*',
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}


@mock.patch('lambda_item.MFAuth')
def mock_getAdminResourcePolicy():
    return {'action': 'allow'}


# Setting the default AWS region environment variable required by the Python SDK boto3
@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region': 'us-east-1', 'application': 'cmf',
                              'environment': 'unittest', 'userpool': 'testuserpool', 'clientid': 'testclientid'})
class LambdaAuthTest(TestCase):
    def test_lambda_handler_with_method(self):
        from lambda_functions.lambda_auth import lambda_auth
        log.info("Testing lambda_auth GET with method passed")
        self.event = {'methodArn': 'test:test:test:test:test:test/apiarntest1/arn2/arn3',
                      'headers': {'Authorization': 'test'}}
        result = lambda_auth.lambda_handler(self.event, None)
        data = result
        # print("Result data: ", data)
        expected_response = {
            'policyDocument':
                {
                    'Statement': [
                        {
                            'Action': 'execute-api:Invoke',
                            'Effect': 'Deny',
                            'Resource': ['arn:aws:execute-api:test:test:test/apiarntest1/*/*']
                        }
                    ],
                    'Version': '2012-10-17'},
            'principalId': ''}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_without_method(self):
        from lambda_functions.lambda_auth import lambda_auth
        log.info("Testing lambda_auth without method passed")
        self.event = {'methodArn': 'test:test:test:test:test:test/apiarntest1/arn2/arn3',
                      'headers': {'Authorization': 'test'}}
        result = lambda_auth.lambda_handler(self.event, None)
        data = result
        # print("Result data: ", data)
        expected_response = {
                             'policyDocument':
                                 {
                                     'Statement': [
                                         {
                                             'Action': 'execute-api:Invoke',
                                             'Effect': 'Deny',
                                             'Resource': ['arn:aws:execute-api:test:test:test/apiarntest1/*/*']
                                         }
                                     ],
                                     'Version': '2012-10-17'},
                             'principalId': ''}
        self.assertEqual(data, expected_response)
