#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import unittest
from unittest import mock
from unittest.mock import patch

from moto import mock_aws


import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lambda_functions/"))

import test_common_utils
from test_common_utils import logger, default_mock_os_environ as mock_os_environ


@mock_aws
@mock.patch.dict("os.environ", {**mock_os_environ, "model": "test-model"})
class LambdaHeaderMapTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

        # Load test data from JSON files
        sample_data_dir = os.path.join(os.path.dirname(__file__), "sample_data")
        with open(os.path.join(sample_data_dir, "bedrock_map_header_request.json"), "r") as f:
            self.test_request = json.load(f)

        with open(os.path.join(sample_data_dir, "bedrock_map_header_response.json"), "r") as f:
            self.test_response = json.load(f)

    def test_lambda_handler_success(self):
        import lambda_header_map

        with patch("lambda_header_map.process_map_headers_request") as mock_process:
            mock_process.return_value = self.test_response["output"]["message"]["content"][0]["toolUse"]["input"]
            event = {
                "body": json.dumps({"headers": self.test_request["headers"], "schemas": self.test_request["schemas"]})
            }

            response = lambda_header_map.lambda_handler(event, None)

            self.assertEqual(200, response["statusCode"])
            body = json.loads(response["body"])
            self.assertIn("application", body)

    def test_lambda_handler_malformed_json(self):
        import lambda_header_map

        event = {"body": "invalid json"}
        response = lambda_header_map.lambda_handler(event, None)

        self.assertEqual(400, response["statusCode"])
        self.assertEqual("malformed json input", response["body"])

    def test_lambda_handler_missing_headers(self):
        import lambda_header_map

        event = {"body": json.dumps({"schemas": self.test_request["schemas"]})}
        response = lambda_header_map.lambda_handler(event, None)

        self.assertEqual(400, response["statusCode"])
        self.assertIn("attribute headers is required", response["body"])

    def test_lambda_handler_empty_headers(self):
        import lambda_header_map

        event = {"body": json.dumps({"headers": [], "schemas": self.test_request["schemas"]})}
        response = lambda_header_map.lambda_handler(event, None)

        self.assertEqual(400, response["statusCode"])
        self.assertIn("attribute headers is required", response["body"])

    def test_lambda_handler_missing_schema(self):
        import lambda_header_map

        event = {"body": json.dumps({"headers": self.test_request["headers"]})}
        response = lambda_header_map.lambda_handler(event, None)

        self.assertEqual(400, response["statusCode"])
        self.assertIn("attribute schemas is required", response["body"])

    def test_lambda_handler_empty_schema(self):
        import lambda_header_map

        event = {"body": json.dumps({"headers": self.test_request["headers"], "schemas": {}})}
        response = lambda_header_map.lambda_handler(event, None)

        self.assertEqual(400, response["statusCode"])
        self.assertIn("attribute schemas is required", response["body"])

    def test_lambda_handler_bedrock_exception(self):
        import lambda_header_map

        with patch("lambda_header_map.process_map_headers_request") as mock_process:
            mock_process.side_effect = Exception("Bedrock error")

            event = {
                "body": json.dumps({"headers": self.test_request["headers"], "schemas": self.test_request["schemas"]})
            }
            response = lambda_header_map.lambda_handler(event, None)

            self.assertEqual(500, response["statusCode"])
            self.assertEqual("internal server exception", response["body"])

    def test_parse_headers_success(self):
        import lambda_header_map

        body = {"headers": self.test_request["headers"]}
        result = lambda_header_map.parse_headers(body)

        self.assertEqual(self.test_request["headers"], result)

    def test_parse_headers_missing(self):
        import lambda_header_map

        body = {}
        with self.assertRaises(ValueError) as context:
            lambda_header_map.parse_headers(body)

        self.assertIn("attribute headers is required", str(context.exception))

    def test_parse_headers_empty(self):
        import lambda_header_map

        body = {"headers": []}
        with self.assertRaises(ValueError) as context:
            lambda_header_map.parse_headers(body)

        self.assertIn("attribute headers is required", str(context.exception))

    def test_parse_schema_success(self):
        import lambda_header_map

        body = {"schemas": self.test_request["schemas"]}
        result = lambda_header_map.parse_schemas(body)

        self.assertEqual(self.test_request["schemas"], result)

    def test_parse_schemas_missing(self):
        import lambda_header_map

        body = {}
        with self.assertRaises(ValueError) as context:
            lambda_header_map.parse_schemas(body)

        self.assertIn("attribute schemas is required", str(context.exception))

    def test_parse_schemas_empty(self):
        import lambda_header_map

        body = {"schemas": {}}
        with self.assertRaises(ValueError) as context:
            lambda_header_map.parse_schemas(body)

        self.assertIn("attribute schemas is required", str(context.exception))

    def test_validate_input_valid_characters(self):
        import lambda_header_map

        # Test valid inputs
        lambda_header_map.validate_input("valid_name123")
        lambda_header_map.validate_input("app name with spaces")
        lambda_header_map.validate_input("config-file")
        lambda_header_map.validate_input("version#1")
        lambda_header_map.validate_input({"key": "value", "app_name": "test app"})
        lambda_header_map.validate_input(["item1", "item-2", "item #3"])

    def test_validate_input_malicious_payload(self):
        import lambda_header_map

        # Test malicious payloads
        malicious_inputs = [
            "&amp;quot;%26%26%20dir%20C%3a%5c",
            "&& dir C:\\",
            "$(whoami)",
            "; rm -rf /",
            "<script>alert('xss')</script>",
            "app|name",
            "config&test",
            "value@domain.com"
        ]

        for malicious_input in malicious_inputs:
            with self.assertRaises(ValueError) as context:
                lambda_header_map.validate_input(malicious_input)
            self.assertIn("Invalid characters in input", str(context.exception))

    def test_validate_input_nested_malicious(self):
        import lambda_header_map

        # Test nested malicious content
        malicious_data = {
            "schemas": {
                "application": {
                    "attributes": [
                        {"name": "&& dir C:\\"}
                    ]
                }
            }
        }

        with self.assertRaises(ValueError) as context:
            lambda_header_map.validate_input(malicious_data)
        self.assertIn("Invalid characters in input", str(context.exception))

    def test_lambda_handler_malicious_payload(self):
        import lambda_header_map

        # Test malicious payload in entire request
        malicious_payload = {
            "headers": ["valid_header"],
            "schemas": {
                "application": {
                    "schema_type": "user",
                    "schema_name": "app",
                    "key_type": "ulid",
                    "attributes": [
                        {"name": "&amp;quot;%26%26%20dir%20C%3a%5c"}
                    ]
                }
            }
        }

        event = {"body": json.dumps(malicious_payload)}
        response = lambda_header_map.lambda_handler(event, None)

        self.assertEqual(400, response["statusCode"])
        self.assertIn("Invalid characters in input", response["body"])


    def test_validate_input_recursion_depth_limit(self):
        """Test validate_input function with recursion depth limit."""
        import lambda_header_map

        # Test normal depth (should pass)
        normal_data = {"level1": {"level2": {"level3": "value"}}}
        lambda_header_map.validate_input(normal_data)  # Should not raise

        # Test exceeding depth limit
        deep_data = {"level": "value"}
        for i in range(102):  # Create 102 levels (exceeds default limit of 100)
            deep_data = {"level": deep_data}

        with self.assertRaises(ValueError) as context:
            lambda_header_map.validate_input(deep_data)
        self.assertIn("Maximum recursion depth exceeded", str(context.exception))

        # Test custom depth limit
        shallow_data = {"level1": {"level2": "value"}}
        with self.assertRaises(ValueError) as context:
            lambda_header_map.validate_input(shallow_data, max_depth=1)
        self.assertIn("Maximum recursion depth exceeded", str(context.exception))

    def test_lambda_handler_model_not_supported(self):
        """Test lambda_handler when model is 'Not Supported'."""
        import lambda_header_map

        with patch.object(lambda_header_map, 'model', 'Not Supported'):
            event = {
                "body": json.dumps({"headers": self.test_request["headers"], "schemas": self.test_request["schemas"]})
            }
            response = lambda_header_map.lambda_handler(event, None)

            self.assertEqual(500, response["statusCode"])
            self.assertIn("No preferred model was available", response["body"])


if __name__ == "__main__":
    unittest.main()
