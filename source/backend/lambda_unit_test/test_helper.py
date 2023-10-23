#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
from unittest import mock
from unittest.mock import patch, ANY
from test_common_utils import LambdaContextLogStream


class HelperTest(unittest.TestCase):

    def setUp(self):
        self.test_event = {
            'StackId': 'testStackId',
            'RequestId': 'testRequestId',
            'LogicalResourceId': 'testLogicalResourceId',
            'ResponseURL': 'testResponseURL',
        }
        self.test_context = LambdaContextLogStream('testLogStreamName')

    @patch('helper.request')
    def test_send_response_happy_trail(self, mock_request):
        import helper
        response_status = {}
        response_data = {}
        helper.send_response(self.test_event, self.test_context, response_status, response_data)
        mock_request.Request.assert_called_once()
        mock_request.urlopen.assert_called_once()

    @patch('helper.request')
    def test_send_response_exceptions(self, mock_request):
        import helper
        response_status = {}
        response_data = {}
        mock_request.Request.side_effect = Exception('test exception')
        helper.send_response(self.test_event, self.test_context, response_status, response_data)
        mock_request.Request.assert_called_once()
        mock_request.urlopen.assert_not_called()

    @patch('helper.uuid')
    def test_lambda_handler(self, mock_uuid):
        import helper
        lambda_create_event = {
            'RequestType': 'Create',
        }
        lambda_other_event = {
            'RequestType': 'Other',
        }
        test_uuid = 'ABC123'
        mock_uuid.uuid4.return_value = test_uuid
        with patch.object(helper, 'send_response') as mock_send_response:
            helper.lambda_handler(lambda_create_event, {})
            mock_send_response.assert_called_with(lambda_create_event, {}, 'SUCCESS', {
                'UUID': test_uuid
            })
            helper.lambda_handler(lambda_other_event, {})
            mock_send_response.assert_called_with(lambda_other_event, {}, 'SUCCESS', {
                'Message': 'Return UUID'
            })
            # the exception path
            mock_send_response.side_effect = [Exception('test exception'), mock.DEFAULT]
            helper.lambda_handler(lambda_create_event, {})
            mock_send_response.assert_called_with(lambda_create_event, {}, 'FAILED', {
                'Error': ANY
            })
