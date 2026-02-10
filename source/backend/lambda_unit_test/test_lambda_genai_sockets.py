#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import unittest
from unittest import mock

from moto import mock_aws

import test_common_utils # used for cmf_boto

def setup_module_mocks():
    """
    Setup mocks for the lambda_genai_sockets module before importing it.
    
    Returns:
        The imported lambda_genai_sockets module with mocks in place
    """
    # Mock environment variables
    with mock.patch.dict('os.environ', {
        'application': 'test-app',
        'environment': 'test-env'
    }):
        # Mock boto3 clients and resources
        with mock.patch('boto3.client') as mock_client, \
             mock.patch('cmf_boto.resource') as mock_resource:
            
            # Mock SQS queue URL response
            mock_sqs = mock.Mock()
            mock_sqs.get_queue_url.return_value = {'QueueUrl': 'https://sqs.test-region.amazonaws.com/test-queue'}
            mock_client.return_value = mock_sqs
            
            # Mock DynamoDB table
            mock_table = mock.Mock()
            mock_resource.return_value.Table.return_value = mock_table
            
            # Import the module with mocks in place
            import lambda_genai_sockets
            return lambda_genai_sockets

@mock_aws
class LambdaGenAISocketsTest(unittest.TestCase):

    def setUp(self) -> None:
        """
        Set up the test environment with mocked modules and test events.
        """
        # Import the module with mocks in place
        self.lambda_module = setup_module_mocks()
        
        # Reset mocks between tests
        self.mock_sqs = mock.Mock()
        self.mock_sqs.get_queue_url.return_value = {'QueueUrl': 'https://sqs.test-region.amazonaws.com/test-queue'}
        self.mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}
        self.lambda_module.sqs = self.mock_sqs
        
        self.mock_table = mock.Mock()
        self.lambda_module.connections_table = self.mock_table
        
        # Create test events
        self.connect_event = {
            "requestContext": {
                "connectionId": "test-connection-id",
                "domainName": "test-domain.execute-api.us-east-1.amazonaws.com",
                "stage": "test",
                "eventType": "CONNECT",
                "authorizer": {
                    "user_id": "test-user-id"
                }
            }
        }
        
        self.disconnect_event = {
            "requestContext": {
                "connectionId": "test-connection-id",
                "domainName": "test-domain.execute-api.us-east-1.amazonaws.com",
                "stage": "test",
                "eventType": "DISCONNECT"
            }
        }
        
        self.message_event = {
            "requestContext": {
                "connectionId": "test-connection-id",
                "domainName": "test-domain.execute-api.us-east-1.amazonaws.com",
                "stage": "test",
                "eventType": "MESSAGE"
            },
            "body": json.dumps({
                "action": "TEST_ACTION",
                "data": "test-data"
            })
        }
        
        self.invalid_event = {
            "requestContext": {}
        }
        
        self.invalid_message_event = {
            "requestContext": {
                "connectionId": "test-connection-id",
                "domainName": "test-domain.execute-api.us-east-1.amazonaws.com",
                "stage": "test",
                "eventType": "MESSAGE"
            },
            "body": "invalid-json"
        }
        
        super().setUp()

    def tearDown(self) -> None:
        """Clean up after each test."""
        mock.patch.stopall()
        super().tearDown()

    def test_lambda_handler_connect_success(self):
        """
        Test lambda_handler with a valid CONNECT event.
        Expected: Returns a success response.
        """
        # Mock process_connect to return a success response
        with mock.patch.object(self.lambda_module, 'process_connect', return_value={"statusCode": 200, "body": "Connection successful"}):
            response = self.lambda_module.lambda_handler(self.connect_event, None)
            self.assertEqual(response["statusCode"], 200)

    def test_lambda_handler_disconnect_success(self):
        """
        Test lambda_handler with a valid DISCONNECT event.
        Expected: Returns a success response.
        """
        # Mock process_disconnect to return a success response
        with mock.patch.object(self.lambda_module, 'process_disconnect', return_value={"statusCode": 200, "body": "Disconnect successful"}):
            response = self.lambda_module.lambda_handler(self.disconnect_event, None)
            self.assertEqual(response["statusCode"], 200)

    def test_lambda_handler_message_success(self):
        """
        Test lambda_handler with a valid MESSAGE event.
        Expected: Returns a success response.
        """
        # Mock process_message to return a success response
        with mock.patch.object(self.lambda_module, 'process_message', return_value={"statusCode": 200, "body": "Message sent for processing"}):
            response = self.lambda_module.lambda_handler(self.message_event, None)
            self.assertEqual(response["statusCode"], 200)

    def test_lambda_handler_invalid_request_context(self):
        """
        Test lambda_handler with an invalid request context.
        Expected: Returns an error response.
        """
        response = self.lambda_module.lambda_handler(self.invalid_event, None)
        self.assertEqual(response["statusCode"], 400)

    def test_lambda_handler_exception(self):
        """
        Test lambda_handler with an exception during processing.
        Expected: Returns an error response.
        """
        # Mock _validate_request_context to raise an exception
        with mock.patch.object(self.lambda_module, '_validate_request_context', side_effect=Exception("Test error")):
            response = self.lambda_module.lambda_handler(self.connect_event, None)
            self.assertEqual(response["statusCode"], 500)

    def test_process_connect(self):
        """
        Test process_connect function.
        Expected: Stores connection in DynamoDB and returns success.
        """
        # Mock DynamoDB put_item
        self.mock_table.put_item.return_value = {}
        
        # Call the function under test
        response = self.lambda_module.process_connect("test-connection-id", "test-user-id", "some-token")
        
        # Verify DynamoDB put_item was called with correct arguments
        self.mock_table.put_item.assert_called_once()
        args, kwargs = self.mock_table.put_item.call_args
        self.assertEqual(kwargs["Item"]["connection_id"], "test-connection-id")
        self.assertEqual(kwargs["Item"]["user_id"], "test-user-id")
        self.assertTrue("connected_at" in kwargs["Item"])
        self.assertTrue("ttl" in kwargs["Item"])
        
        # Verify response
        self.assertEqual(response["statusCode"], 200)

    def test_process_connect_error(self):
        """
        Test process_connect function with DynamoDB error.
        Expected: Returns an error response.
        """
        # Mock DynamoDB put_item to raise an exception
        error_response = {'Error': {'Code': 'ConditionalCheckFailedException'}}
        self.mock_table.put_item.side_effect = self.lambda_module.ClientError(error_response, 'PutItem')
        
        # Call the function under test
        response = self.lambda_module.process_connect("test-connection-id", "test-user-id", "some-token")
        
        # Verify response
        self.assertEqual(response["statusCode"], 500)

    def test_process_disconnect(self):
        """
        Test process_disconnect function.
        Expected: Deletes connection from DynamoDB and returns success.
        """
        # Mock DynamoDB delete_item
        self.mock_table.delete_item.return_value = {"Attributes": {"connection_id": "test-connection-id"}}
        
        # Call the function under test
        response = self.lambda_module.process_disconnect("test-connection-id")
        
        # Verify DynamoDB delete_item was called with correct arguments
        self.mock_table.delete_item.assert_called_once_with(
            Key={"connection_id": "test-connection-id"},
            ReturnValues="ALL_OLD"
        )
        
        # Verify response
        self.assertEqual(response["statusCode"], 200)

    def test_process_disconnect_not_found(self):
        """
        Test process_disconnect function with connection not found.
        Expected: Still returns success.
        """
        # Mock DynamoDB delete_item with no attributes returned
        self.mock_table.delete_item.return_value = {}
        
        # Call the function under test
        response = self.lambda_module.process_disconnect("test-connection-id")
        
        # Verify response
        self.assertEqual(response["statusCode"], 200)

    def test_process_disconnect_error(self):
        """
        Test process_disconnect function with DynamoDB error.
        Expected: Returns an error response.
        """
        # Mock DynamoDB delete_item to raise an exception
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        self.mock_table.delete_item.side_effect = self.lambda_module.ClientError(error_response, 'DeleteItem')
        
        # Call the function under test
        response = self.lambda_module.process_disconnect("test-connection-id")
        
        # Verify response
        self.assertEqual(response["statusCode"], 500)

    def test_process_message(self):
        """
        Test process_message function.
        Expected: Sends message to SQS and returns success.
        """
        # Call the function under test
        response = self.lambda_module.process_message(self.message_event, "test-connection-id", "test-domain", "test")
        
        # Verify SQS send_message was called with correct arguments
        self.mock_sqs.send_message.assert_called_once()
        args, kwargs = self.mock_sqs.send_message.call_args
        self.assertEqual(kwargs["QueueUrl"], "https://sqs.test-region.amazonaws.com/test-queue")
        
        # Parse the message body to verify its contents
        message_body = json.loads(kwargs["MessageBody"])
        self.assertEqual(message_body["connection"]["connection_id"], "test-connection-id")
        self.assertEqual(message_body["action"], "TEST_ACTION")
        self.assertTrue("timestamp" in message_body)
        
        # Verify response
        self.assertEqual(response["statusCode"], 200)

    def test_process_message_invalid_json(self):
        """
        Test process_message function with invalid JSON.
        Expected: Returns an error response.
        """
        # Call the function under test
        response = self.lambda_module.process_message(self.invalid_message_event, "test-connection-id", "test-domain", "test")
        
        # Verify response
        self.assertEqual(response["statusCode"], 400)

    def test_process_message_missing_action(self):
        """
        Test process_message function with missing action.
        Expected: Returns an error response.
        """
        # Create event with missing action
        event = {
            "requestContext": {
                "connectionId": "test-connection-id",
                "domainName": "test-domain.execute-api.us-east-1.amazonaws.com",
                "stage": "test",
                "eventType": "MESSAGE"
            },
            "body": json.dumps({
                "data": "test-data"
            })
        }
        
        # Call the function under test
        response = self.lambda_module.process_message(event, "test-connection-id", "test-domain", "test")
        
        # Verify response
        self.assertEqual(response["statusCode"], 400)

    def test_process_message_sqs_error(self):
        """
        Test process_message function with SQS error.
        Expected: Returns an error response.
        """
        # Mock SQS send_message to raise an exception
        error_response = {'Error': {'Code': 'ServiceUnavailable'}}
        self.mock_sqs.send_message.side_effect = self.lambda_module.ClientError(error_response, 'SendMessage')
        
        # Call the function under test
        response = self.lambda_module.process_message(self.message_event, "test-connection-id", "test-domain", "test")
        
        # Verify response
        self.assertEqual(response["statusCode"], 500)

    def test_validate_request_context_success(self):
        """
        Test _validate_request_context function with valid context.
        Expected: Returns the context and None for error response.
        """
        # Call the function under test
        context, error = self.lambda_module._validate_request_context(self.connect_event)
        
        # Verify results
        self.assertEqual(context, self.connect_event["requestContext"])
        self.assertIsNone(error)

    def test_validate_request_context_missing(self):
        """
        Test _validate_request_context function with missing context.
        Expected: Returns empty context and error response.
        """
        # Call the function under test
        context, error = self.lambda_module._validate_request_context({})
        
        # Verify results
        self.assertEqual(context, {})
        self.assertEqual(error["statusCode"], 400)

    def test_validate_request_context_incomplete(self):
        """
        Test _validate_request_context function with incomplete context.
        Expected: Returns context and error response.
        """
        # Create event with incomplete context
        event = {
            "requestContext": {
                "connectionId": "test-connection-id"
                # Missing domainName and stage
            }
        }
        
        # Call the function under test
        context, error = self.lambda_module._validate_request_context(event)
        
        # Verify results
        self.assertEqual(context, event["requestContext"])
        self.assertEqual(error["statusCode"], 400)

    def test_get_response(self):
        """
        Test _get_response function.
        Expected: Returns properly formatted response.
        """
        # Call the function under test
        response = self.lambda_module._get_response(200, "Test message")
        
        # Verify response format
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], "Test message")
        self.assertTrue("headers" in response)

    def test_get_response_with_dict(self):
        """
        Test _get_response function with dict body.
        Expected: Returns properly formatted response with JSON string body.
        """
        # Call the function under test
        response = self.lambda_module._get_response(200, {"message": "Test message"})
        
        # Verify response format
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], json.dumps({"message": "Test message"}))
        self.assertTrue("headers" in response)