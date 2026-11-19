#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import unittest
from unittest import mock

from moto import mock_aws

import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lambda_functions/"))

import test_common_utils


def setup_module_mocks():
    """
    Setup mocks for the lambda_genai_sockets_handler module before importing it.

    Returns:
        The imported lambda_genai_sockets_handler module with mocks in place
    """
    # Mock boto3 client and botocore Config
    with mock.patch("boto3.client"), mock.patch("botocore.config.Config"):
        import lambda_genai_sockets_handler
        import shared.header_mapping

        return lambda_genai_sockets_handler, shared.header_mapping


@mock_aws
class LambdaGenAISocketsHandlerTest(unittest.TestCase):
    @mock.patch.dict(
        "os.environ", {**test_common_utils.default_mock_os_environ, "model": "anthropic.claude-3-sonnet-20240229-v1:0"}
    )
    @mock.patch("botocore.config.Config")
    def setUp(self, mock_config) -> None:
        """
        Set up the test environment with mocked modules and test events.
        """
        # Configure the Config mock
        self.mock_config = mock_config

        # Import the modules with mocks in place
        self.lambda_module, self.map_headers_module = setup_module_mocks()

        # Reset mocks between tests
        self.mock_api_gateway = mock.Mock()
        self.test_connection_id = "test-connection-id"
        self.mock_bedrock_runtime = mock.Mock()
        self.lambda_module.bedrock_runtime = self.mock_bedrock_runtime

        # Load test data from JSON files
        sample_data_dir = os.path.join(os.path.dirname(__file__), "sample_data")
        with open(os.path.join(sample_data_dir, "bedrock_map_header_request.json"), "r") as f:
            request_data = json.load(f)

        # Create test events
        self.valid_message = {
            "messageId": "test-message-id",
            "body": json.dumps(
                {
                    "connection": {
                        "connection_id": "test-connection-id",
                        "domain_name": "test-domain.execute-api.us-east-1.amazonaws.com",
                        "stage": "test",
                    },
                    "action": "MAP_HEADERS",
                    "request": request_data,
                }
            ),
        }

        self.invalid_json_message = {"messageId": "test-message-id", "body": "invalid json"}

        self.missing_connection_message = {
            "messageId": "test-message-id",
            "body": json.dumps({"action": "MAP_HEADERS", "request": request_data}),
        }

        self.missing_action_message = {
            "messageId": "test-message-id",
            "body": json.dumps(
                {
                    "connection": {
                        "connection_id": "test-connection-id",
                        "domain_name": "test-domain.execute-api.us-east-1.amazonaws.com",
                        "stage": "test",
                    },
                    "request": request_data,
                }
            ),
        }

        self.unknown_action_message = {
            "messageId": "test-message-id",
            "body": json.dumps(
                {
                    "connection": {
                        "connection_id": "test-connection-id",
                        "domain_name": "test-domain.execute-api.us-east-1.amazonaws.com",
                        "stage": "test",
                    },
                    "action": "UNKNOWN_ACTION",
                    "request": request_data,
                }
            ),
        }

        self.missing_request_message = {
            "messageId": "test-message-id",
            "body": json.dumps(
                {
                    "connection": {
                        "connection_id": "test-connection-id",
                        "domain_name": "test-domain.execute-api.us-east-1.amazonaws.com",
                        "stage": "test",
                    },
                    "action": "MAP_HEADERS",
                }
            ),
        }

        self.empty_request_message = {
            "messageId": "test-message-id",
            "body": json.dumps(
                {
                    "connection": {
                        "connection_id": "test-connection-id",
                        "domain_name": "test-domain.execute-api.us-east-1.amazonaws.com",
                        "stage": "test",
                    },
                    "action": "MAP_HEADERS",
                    "request": {},
                }
            ),
        }

        super().setUp()

    def tearDown(self) -> None:
        """Clean up after each test."""
        mock.patch.stopall()
        super().tearDown()

    def test_lambda_handler_success(self):
        """
        Test lambda_handler with a valid message.
        Expected: Returns a success result.
        """
        # Mock process_message to return a success result
        with mock.patch.object(self.lambda_module, "process_message", return_value={"status": "success"}):
            response = self.lambda_module.lambda_handler({"Records": [self.valid_message]}, None)
            self.assertEqual(len(response["batchItemFailures"]), 0)

    def test_lambda_handler_error(self):
        """
        Test lambda_handler with an error in processing.
        Expected: Returns an error result.
        """
        # Mock process_message to raise an exception
        with mock.patch.object(self.lambda_module, "process_message", side_effect=Exception("Test error")):
            response = self.lambda_module.lambda_handler({"Records": [self.valid_message]}, None)

            self.assertEqual(1, len(response["batchItemFailures"]))
            self.assertEqual(self.valid_message["messageId"], response["batchItemFailures"][0]["itemIdentifier"])

    def test_lambda_handler_multiple_messages(self):
        """
        Test lambda_handler with multiple messages.
        Expected: Returns results for all messages.
        """
        # Mock process_message to return success for first message and raise exception for second
        with mock.patch.object(self.lambda_module, "process_message", side_effect=[None, Exception("Test error")]):
            response = self.lambda_module.lambda_handler({"Records": [self.valid_message, self.valid_message]}, None)
            self.assertEqual(1, len(response["batchItemFailures"]))

    def test_process_message_invalid_json(self):
        """
        Test process_message with invalid JSON.
        Expected: Raises ValueError.
        """
        with self.assertRaises(ValueError):
            self.lambda_module.process_message(self.invalid_json_message)

    def test_process_message_missing_connection(self):
        """
        Test process_message with missing connection field.
        Expected: Raises ValueError.
        """
        with self.assertRaises(ValueError):
            self.lambda_module.process_message(self.missing_connection_message)

    def test_process_message_missing_action(self):
        """
        Test process_message with missing action field.
        Expected: Raises ValueError.
        """
        with self.assertRaises(ValueError):
            self.lambda_module.process_message(self.missing_action_message)

    def test_process_message_unknown_action(self):
        """
        Test process_message with unknown action.
        Expected: Raises ValueError.
        """
        with self.assertRaises(ValueError):
            self.lambda_module.process_message(self.unknown_action_message)

    def test_process_message_missing_request(self):
        """
        Test process_message with missing request data.
        Expected: Raises ValueError.
        """
        with self.assertRaises(ValueError):
            self.lambda_module.process_message(self.missing_request_message)

    def test_process_message_empty_request(self):
        """
        Test process_message with empty request data.
        Expected: Raises ValueError.
        """
        with self.assertRaises(ValueError):
            self.lambda_module.process_message(self.empty_request_message)

    @mock.patch("boto3.client")
    @mock.patch("lambda_genai_sockets_handler.process_map_headers_request")
    @mock.patch("lambda_genai_sockets_handler.post_to_connection")
    def test_process_message_map_headers_success(
        self, mock_post_to_connection, mock_process_map_headers, mock_boto3_client
    ):
        """
        Test process_message with MAP_HEADERS action.
        Expected: Calls process_map_headers_request and posts result to connection with action.
        """
        # Mock API Gateway client
        mock_api_gateway = mock.Mock()
        mock_boto3_client.return_value = mock_api_gateway

        # Set return value for the mocked process_map_headers_request
        mock_process_map_headers.return_value = {"result": "success"}

        # Call the function under test
        self.lambda_module.process_message(self.valid_message)

        # Verify process_map_headers_request was called with correct arguments
        mock_process_map_headers.assert_called_once()
        args = mock_process_map_headers.call_args[0]
        self.assertEqual(json.loads(self.valid_message["body"])["request"], args[0])
        self.assertEqual(self.mock_bedrock_runtime, args[1])
        self.assertEqual("anthropic.claude-3-sonnet-20240229-v1:0", args[2])

        # Verify post_to_connection was called with correct arguments
        mock_post_to_connection.assert_called_once()
        args = mock_post_to_connection.call_args[0]
        self.assertIsInstance(args[0], mock.Mock)  # API Gateway client
        self.assertEqual("test-connection-id", args[1])
        self.assertEqual({"action": "MAP_HEADERS", "result": {"result": "success"}}, args[2])

    def test_validate_message_structure_success(self):
        """
        Test _validate_message_structure with valid message.
        Expected: No exception raised.
        """
        message_data = json.loads(self.valid_message["body"])
        try:
            self.lambda_module._validate_message_structure(message_data)
        except ValueError:
            self.fail("_validate_message_structure raised ValueError unexpectedly!")

    def test_validate_message_structure_missing_connection(self):
        """
        Test _validate_message_structure with missing connection.
        Expected: Raises ValueError.
        """
        message_data = json.loads(self.missing_connection_message["body"])
        with self.assertRaises(ValueError):
            self.lambda_module._validate_message_structure(message_data)

    def test_validate_message_structure_missing_connection_field(self):
        """
        Test _validate_message_structure with missing connection field.
        Expected: Raises ValueError.
        """
        message_data = json.loads(self.valid_message["body"])
        del message_data["connection"]["connection_id"]
        with self.assertRaises(ValueError):
            self.lambda_module._validate_message_structure(message_data)

    def test_validate_message_structure_missing_action(self):
        """
        Test _validate_message_structure with missing action.
        Expected: Raises ValueError.
        """
        message_data = json.loads(self.missing_action_message["body"])
        with self.assertRaises(ValueError):
            self.lambda_module._validate_message_structure(message_data)

    def test_lambda_post_to_connection_success(self):
        """
        Test post_to_connection in lambda_genai_sockets_handler with successful execution.
        Expected: Calls post_to_connection on API Gateway client.
        """
        data = {"test": "data"}
        self.lambda_module.post_to_connection(self.mock_api_gateway, self.test_connection_id, data)

        # Verify post_to_connection was called with correct arguments
        self.mock_api_gateway.post_to_connection.assert_called_once_with(
            ConnectionId=self.test_connection_id, Data=json.dumps(data)
        )

    def test_lambda_post_to_connection_error(self):
        """
        Test post_to_connection in lambda_genai_sockets_handler with an error.
        Expected: Raises RuntimeError and logs the error.
        """
        # Mock API Gateway client to raise an exception
        self.mock_api_gateway.post_to_connection.side_effect = Exception("Test error")

        with mock.patch.object(self.lambda_module, "logger") as mock_logger:
            with self.assertRaises(RuntimeError):
                self.lambda_module.post_to_connection(self.mock_api_gateway, self.test_connection_id, {"test": "data"})

            # Verify error was logged
            mock_logger.warning.assert_called_once()
            self.assertIn("Error posting to connection", mock_logger.warning.call_args[0][0])

    @mock.patch("lambda_genai_sockets_handler._send_error_response")
    def test_process_message_model_not_supported(self, mock_send_error):
        """
        Test process_message when model is "Not Supported".
        Expected: Raises ValueError and calls _send_error_response.
        """
        # Temporarily change the model to "Not Supported"
        original_model = self.lambda_module.model
        self.lambda_module.model = "Not Supported"

        try:
            with self.assertRaises(ValueError) as context:
                self.lambda_module.process_message(self.valid_message)

            # Verify the error message
            self.assertIn("No preferred model was available", str(context.exception))

            # Verify _send_error_response was called
            mock_send_error.assert_called_once()
            call_args = mock_send_error.call_args[0]
            self.assertEqual("test-connection-id", call_args[1])
            self.assertEqual("MAP_HEADERS", call_args[2])
            self.assertIn("Processing error", call_args[3])
        finally:
            # Restore original model
            self.lambda_module.model = original_model

    def test_send_error_response_success(self):
        """
        Test _send_error_response with successful execution.
        Expected: Calls post_to_connection with error response.
        """
        with mock.patch.object(self.lambda_module, "logger") as mock_logger:
            self.lambda_module._send_error_response(
                self.mock_api_gateway, self.test_connection_id, "MAP_HEADERS", "Test error message"
            )

            # Verify post_to_connection was called with error response
            expected_data = {"action": "MAP_HEADERS", "error": "Test error message"}
            self.mock_api_gateway.post_to_connection.assert_called_once_with(
                ConnectionId=self.test_connection_id, Data=json.dumps(expected_data)
            )

            # Verify success was logged
            mock_logger.info.assert_called_once_with(f"Error response sent to connection {self.test_connection_id}")

    def test_send_error_response_no_connection(self):
        """
        Test _send_error_response with no connection ID.
        Expected: Returns early without calling post_to_connection.
        """
        self.lambda_module._send_error_response(self.mock_api_gateway, None, "MAP_HEADERS", "Test error")
        self.mock_api_gateway.post_to_connection.assert_not_called()

    def test_send_error_response_no_api_gateway(self):
        """
        Test _send_error_response with no API Gateway client.
        Expected: Returns early without calling post_to_connection.
        """
        self.lambda_module._send_error_response(None, self.test_connection_id, "MAP_HEADERS", "Test error")
        # No assertion needed as there's no mock to check

    def test_send_error_response_post_error(self):
        """
        Test _send_error_response when post_to_connection fails.
        Expected: Logs warning about failure.
        """
        # Mock API Gateway client to raise an exception
        self.mock_api_gateway.post_to_connection.side_effect = Exception("Post error")

        with mock.patch.object(self.lambda_module, "logger") as mock_logger:
            self.lambda_module._send_error_response(
                self.mock_api_gateway, self.test_connection_id, "MAP_HEADERS", "Test error"
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            self.assertIn("Failed to send error response", mock_logger.warning.call_args[0][0])

    def test_send_error_response_unknown_action(self):
        """
        Test _send_error_response with None action.
        Expected: Uses "UNKNOWN" as action in error response.
        """
        with mock.patch.object(self.lambda_module, "logger"):
            self.lambda_module._send_error_response(
                self.mock_api_gateway, self.test_connection_id, None, "Test error"
            )

            # Verify post_to_connection was called with "UNKNOWN" action
            expected_data = {"action": "UNKNOWN", "error": "Test error"}
            self.mock_api_gateway.post_to_connection.assert_called_once_with(
                ConnectionId=self.test_connection_id, Data=json.dumps(expected_data)
            )


if __name__ == "__main__":
    unittest.main()
