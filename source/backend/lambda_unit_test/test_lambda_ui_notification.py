#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import sys
from unittest.mock import MagicMock, patch
import boto3
from unittest import mock, TestCase
import botocore
from moto import mock_aws
import test_common_utils

mock_os_environ = {
    **test_common_utils.default_mock_os_environ,
    'socket_url': 'https://example.com'
}

@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaUINotificationTest(TestCase):
    @mock.patch.dict('os.environ', mock_os_environ)
    @mock_aws
    def setUp(self) -> None:
        import lambda_ui_notification
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_connection_ids(
            self.ddb_client, 
            lambda_ui_notification.connectionIds_table_name
        )

    def create_notification_event(self, notification_type='info'):
        """Create a test notification event"""
        return {
            "detail-type": "TaskSuccess",
            "detail": {
                "dismissible": True,
                "header": "Test Header",
                "content": "Test Content",
                "timeStamp": "2024-01-01T00:00:00Z",
                "uuid": "1f15e14b-5cd6-4e0a-bacb-b311daaed334"
            }
        }

    def test_lambda_handler_missing_required_field(self):
        """Test lambda handler with missing required field"""
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        import lambda_ui_notification
        
        invalid_event = {
            "detail-type": "TaskSuccess",
            "detail": {
                "dismissible": True,
                "content": "Test Content",
                "timeStamp": "2024-01-01T00:00:00Z",
                "uuid": "1f15e14b-5cd6-4e0a-bacb-b311daaed334"
            }
        }
        
        with self.assertRaises(ValueError) as context:
            lambda_ui_notification.lambda_handler(invalid_event, None)
        self.assertEqual(str(context.exception), "Missing required field: header")

    def test_lambda_handler_invalid_field_type(self):
        """Test lambda handler with invalid field type"""
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        import lambda_ui_notification
        
        invalid_event = {
            "detail-type": "TaskSuccess",
            "detail": {
                "dismissible": "not a boolean",
                "header": "Test Header",
                "content": "Test Content",
                "timeStamp": "2024-01-01T00:00:00Z",
                "uuid": "1f15e14b-5cd6-4e0a-bacb-b311daaed334"
            }
        }
        
        with self.assertRaises(ValueError) as context:
            lambda_ui_notification.lambda_handler(invalid_event, None)
        self.assertEqual(str(context.exception), "'dismissible' must be a bool")

    def test_lambda_handler_valid_notification(self):
        """Test lambda handler with a valid notification event"""
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        import lambda_ui_notification
        
        valid_event = self.create_notification_event()
        
        # Mock the gateway API
        with patch('lambda_ui_notification.gatewayapi') as mock_gatewayapi:
            lambda_ui_notification.lambda_handler(valid_event, None)
            
            # Verify gateway API was called correctly
            self.assertEqual(2, mock_gatewayapi.post_to_connection.call_count)
            
            # Verify the message content sent to gateway
            expected_message = {
                'type': 'TaskSuccess',
                'dismissible': True,
                'header': 'Test Header',
                'content': 'Test Content',
                'timeStamp': '2024-01-01T00:00:00Z',
                "uuid": "1f15e14b-5cd6-4e0a-bacb-b311daaed334"
            }
            
            # Get the actual message that was sent
            actual_message = json.loads(
                mock_gatewayapi.post_to_connection.call_args[1]['Data']
            )
            
            # Verify the message content matches what we expect
            self.assertEqual(expected_message, actual_message)


    @patch('lambda_ui_notification.gatewayapi')
    def test_lambda_handler_wss_success(self, mock_getwaymgtapi):
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        os.environ['socket_url'] = 'wss://example.com'
        import lambda_ui_notification
        lambda_ui_notification.gatewayapi = mock_getwaymgtapi
        event = self.create_notification_event()
        response = lambda_ui_notification.lambda_handler(event, None)
        self.assertEqual(None, response)
        self.assertEqual(2, mock_getwaymgtapi.post_to_connection.call_count)

    @patch('lambda_ui_notification.gatewayapi')
    def test_lambda_handler_wss_client_error(self, mock_getwaymgtapi):
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        os.environ['socket_url'] = 'wss://example.com'
        import lambda_ui_notification
        lambda_ui_notification.gatewayapi = mock_getwaymgtapi
        event = self.create_notification_event()
        mock_getwaymgtapi.post_to_connection.side_effect = botocore.exceptions.ClientError({
            'Error': {
                'Code': 500,
                'Message': 'Simulated Exception'
            }
        },
            'post_to_connection')
        with patch('lambda_ui_notification.logger') as mock_logger:
            lambda_ui_notification.lambda_handler(event, None)
            mock_logger.error.assert_called_with("Error posting to wss connection: 500: Simulated Exception")

        self.assertEqual(2, mock_getwaymgtapi.post_to_connection.call_count)
       
    @patch('lambda_ui_notification.gatewayapi')
    def test_lambda_handler_wss_unexpected_error(self, mock_getwaymgtapi):
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        os.environ['socket_url'] = 'wss://example.com'
        import lambda_ui_notification
        lambda_ui_notification.gatewayapi = mock_getwaymgtapi
        event = self.create_notification_event()
        mock_getwaymgtapi.post_to_connection.side_effect = Exception('network error')

        with patch('lambda_ui_notification.logger') as mock_logger:
            lambda_ui_notification.lambda_handler(event, None)
            mock_logger.error.assert_called_with("Unexpected error posting to wss connection 2: network error")

        self.assertEqual(2, mock_getwaymgtapi.post_to_connection.call_count)

    def test_lambda_handler_null_event(self):
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        import lambda_ui_notification
        
        with self.assertRaises(ValueError) as context:
            lambda_ui_notification.lambda_handler(None, None)
        self.assertEqual(str(context.exception), "Event cannot be None")

    def test_lambda_handler_empty_event(self):
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        import lambda_ui_notification
        
        empty_event = {}
        
        with self.assertRaises(ValueError) as context:
            lambda_ui_notification.lambda_handler(empty_event, None)
        self.assertEqual(str(context.exception), "Missing or invalid 'detail' in event")

    @patch('lambda_ui_notification.connectionIds_table')
    @patch('lambda_ui_notification.gatewayapi')
    def test_lambda_handler_scan_client_error(self, mock_gatewayapi, mock_table):
        """Test lambda handler when scan operation raises a ClientError"""
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        import lambda_ui_notification
        
        # Create the ClientError exception
        mock_table.scan.side_effect = botocore.exceptions.ClientError(
            error_response={
                "Error": {
                    "Code": "ProvisionedThroughputExceededException",
                    "Message": "Throughput exceeds the current capacity"
                }
            },
            operation_name="Scan"
        )
        
        # Ensure the mock is properly attached to the lambda module
        lambda_ui_notification.connectionIds_table = mock_table
        
        event = self.create_notification_event()
        
        with patch('lambda_ui_notification.logger') as mock_logger:
            lambda_ui_notification.lambda_handler(event, None)
            
            # Verify that scan was called
            mock_table.scan.assert_called_once()
            
            # Verify that the error was logged
            mock_logger.error.assert_called_with(
                "Could not scan for connections due to: "
                "ProvisionedThroughputExceededException: "
                "Throughput exceeds the current capacity"
            )

    @patch('lambda_ui_notification.connectionIds_table')
    @patch('lambda_ui_notification.gatewayapi')
    def test_lambda_handler_scan_unexpected_error(self, mock_gatewayapi, mock_table):
        """Test lambda handler when scan operation raises an unexpected error"""
        if 'lambda_ui_notification' in sys.modules:
            del sys.modules['lambda_ui_notification']
        import lambda_ui_notification
        
        # Configure the mock table to raise an unexpected error
        mock_table.scan.side_effect = Exception("Unexpected database error")
        
        # Ensure the mock is properly attached to the lambda module
        lambda_ui_notification.connectionIds_table = mock_table
        
        event = self.create_notification_event()
        
        with patch('lambda_ui_notification.logger') as mock_logger:
            lambda_ui_notification.lambda_handler(event, None)
            
            # Verify that scan was called
            mock_table.scan.assert_called_once()
            
            # Verify that the error was logged
            mock_logger.error.assert_called_with(
                "Unexpected error during scan: Unexpected database error"
            )