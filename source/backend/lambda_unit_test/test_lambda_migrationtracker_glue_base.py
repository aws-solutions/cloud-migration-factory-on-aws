#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
from unittest.mock import ANY
import json

from test_common_utils import default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'application': 'cmf',
    'environment': 'unittest',
    'local_bucket': 'cmf_test_local_bucket',
    'remote_bucket': 'cmf_test_remote_bucket',
    'key_prefix': 'cmf_test_key_prefix',
}


class StringContainsMatcher:
    """
    used to check whether the string is contained in the actual parameter
    to be used in mock.call_with
    """

    def __init__(self, expected):
        self.expected = expected

    def __eq__(self, actual):
        return self.expected in actual

    def __repr__(self):
        return self.expected


class LambdaContext:
    def __init__(self, aws_request_id):
        self.aws_request_id = aws_request_id


class RequestsResponse:
    def __init__(self, reason):
        self.reason = reason


@mock.patch.dict('os.environ', mock_os_environ)
class LambdaMigrationTrackerGlueBaseTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.test_aws_account_id = '111111111111'
        self.event_create = {
            'RequestType': 'Create',
            'ResponseURL': 'http://example.com',
            'StackId': 'MyStack',
            'RequestId': 'MyRequest',
            'LogicalResourceId': 'Resource101'
        }
        self.event_update = {
            'RequestType': 'Update',
            'ResponseURL': 'http://example.com',
            'StackId': 'MyStack',
            'RequestId': 'MyRequest',
            'LogicalResourceId': 'Resource101'
        }
        self.event_delete = {
            'RequestType': 'Delete',
            'ResponseURL': 'http://example.com',
            'StackId': 'MyStack',
            'RequestId': 'MyRequest',
            'LogicalResourceId': 'Resource101'
        }
        self.event_unknown = {
            'RequestType': 'Unknown',
            'ResponseURL': 'http://example.com',
            'StackId': 'MyStack',
            'RequestId': 'MyRequest',
            'LogicalResourceId': 'Resource101'
        }
        self.lamda_context = LambdaContext(self.test_aws_account_id)

    def assert_response(self, response):
        # the send_response function doesn't return anything, so the return is always  {'Response':  None},
        # even in failures
        self.assertEqual({'Response': None}, response)

    def assert_requests_called_with(self, mock_requests, message, status):
        mock_requests.put.assert_called_once_with('http://example.com',
                                                  data=json.dumps({'Status': status,
                                                                   'PhysicalResourceId': self.test_aws_account_id,
                                                                   'Reason': message,
                                                                   'StackId': 'MyStack',
                                                                   'RequestId': 'MyRequest',
                                                                   'LogicalResourceId': 'Resource101',
                                                                   }),
                                                  headers=ANY,
                                                  timeout=ANY)

    def assert_requests_called_with_success(self, mock_requests, message):
        self.assert_requests_called_with(mock_requests, message, 'SUCCESS')

    def assert_requests_called_with_failure(self, mock_requests, message):
        self.assert_requests_called_with(mock_requests, message, 'FAILED')
