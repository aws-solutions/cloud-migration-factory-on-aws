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


import unittest
from unittest import mock
from unittest.mock import patch, ANY
import common_utils

common_utils.init()
logger = common_utils.logger

# classes for duck typing
class Context:
    def __init__(self, log_stream_name):
        self.log_stream_name = log_stream_name


class HelperTest(unittest.TestCase):

    def setUp(self):
        self.test_event = {
            'StackId': 'testStackId',
            'RequestId': 'testRequestId',
            'LogicalResourceId': 'testLogicalResourceId',
            'ResponseURL': 'testResponseURL',
        }
        self.test_context = Context('testLogStreamName')

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
