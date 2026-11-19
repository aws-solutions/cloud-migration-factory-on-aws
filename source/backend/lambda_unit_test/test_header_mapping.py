#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import unittest
from unittest import mock

from moto import mock_aws

import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lambda_functions/shared/"))

import test_common_utils


class MapHeadersTest(unittest.TestCase):
    def setUp(self) -> None:
        """
        Set up the test environment with mocked modules.
        """
        # Load test data from JSON files
        sample_data_dir = os.path.join(os.path.dirname(__file__), "sample_data")

        with open(os.path.join(sample_data_dir, "bedrock_map_header_request.json"), "r") as f:
            self.test_request = json.load(f)

        with open(os.path.join(sample_data_dir, "bedrock_map_header_response.json"), "r") as f:
            self.bedrock_response = json.load(f)

        self.mock_bedrock_runtime = mock.Mock()
        self.test_model = "anthropic.claude-3-sonnet-20240229-v1:0"

        super().setUp()

    def tearDown(self) -> None:
        """Clean up after each test."""
        mock.patch.stopall()
        super().tearDown()

    def test_process_map_headers_request_success(self):
        """
        Test process_map_headers_request with successful execution.
        Expected: Returns the mapping result and calls query_bedrock.
        """

        import header_mapping

        # Mock query_bedrock
        expected_result = self.bedrock_response["output"]["message"]["content"][0]["toolUse"]["input"]
        with mock.patch("header_mapping.query_bedrock", return_value=expected_result) as mock_query:
            # Call the function
            result = header_mapping.process_map_headers_request(
                self.test_request, self.mock_bedrock_runtime, self.test_model
            )

            # Verify query_bedrock was called with correct arguments
            mock_query.assert_called_once_with(self.test_request, self.mock_bedrock_runtime, self.test_model)

            # Verify the function returns the expected result
            self.assertEqual(expected_result, result)

    def test_process_map_headers_request_error(self):
        """
        Test process_map_headers_request with an error.
        Expected: Raises RuntimeError and logs the error.
        """

        import header_mapping

        # Mock query_bedrock to raise an exception
        with mock.patch("header_mapping.query_bedrock", side_effect=Exception("Test error")):
            with mock.patch("header_mapping.logger") as mock_logger:
                with self.assertRaises(RuntimeError):
                    header_mapping.process_map_headers_request(
                        self.test_request, self.mock_bedrock_runtime, self.test_model
                    )

                # Verify error was logged
                mock_logger.warning.assert_called_once()
                self.assertIn("Unable to query bedrock", mock_logger.warning.call_args[0][0])

    def test_query_bedrock_success(self):
        """
        Test query_bedrock with successful execution.
        Expected: Returns processed mappings and calls sort_mappings_by_confidence for each schema type.
        """
        import header_mapping

        # Mock bedrock_runtime.converse
        self.mock_bedrock_runtime.converse.return_value = self.bedrock_response

        # Mock sort_mappings_by_confidence
        with mock.patch("header_mapping.sort_mappings_by_confidence") as mock_sort:
            # Call the function
            result = header_mapping.query_bedrock(self.test_request, self.mock_bedrock_runtime, self.test_model)

            # Verify bedrock_runtime.converse was called with correct parameters
            call_args = self.mock_bedrock_runtime.converse.call_args[1]
            self.assertEqual(self.test_model, call_args["modelId"])
            self.assertEqual("header_map", call_args["toolConfig"]["toolChoice"]["tool"]["name"])

            # Verify the result contains all schema types from the request
            for schema_type in self.test_request["schemas"].keys():
                self.assertIn(schema_type, result)
                self.assertIn("mappings", result[schema_type])
                self.assertIsInstance(result[schema_type]["mappings"], list)

            # Verify bedrock_runtime.converse was called
            self.mock_bedrock_runtime.converse.assert_called_once()

            # Verify sort_mappings_by_confidence was called for each schema type
            expected_calls = len(self.test_request["schemas"])
            self.assertEqual(mock_sort.call_count, expected_calls)

            # Verify sort_mappings_by_confidence was called with correct arguments
            for schema_type in self.test_request["schemas"].keys():
                mock_sort.assert_any_call(result[schema_type]["mappings"])

            # Verify the final result matches expected structure
            self.assertEqual(result, self.bedrock_response["output"]["message"]["content"][0]["toolUse"]["input"])

    def test_query_bedrock_api_error(self):
        """
        Test query_bedrock with API error.
        Expected: Raises RuntimeError.
        """
        import header_mapping

        # Mock bedrock_runtime.converse to raise an exception
        self.mock_bedrock_runtime.converse.side_effect = Exception("API error")

        with mock.patch("header_mapping.logger") as mock_logger:
            with self.assertRaises(RuntimeError):
                header_mapping.query_bedrock(self.test_request, self.mock_bedrock_runtime, self.test_model)

            # Verify error was logged
            mock_logger.warning.assert_called_once()
            self.assertIn("Bedrock API error", mock_logger.warning.call_args[0][0])

    @mock.patch.dict("os.environ", {"BEDROCK_GUARDRAIL_ID": "test-guardrail-id", "BEDROCK_GUARDRAIL_VERSION": "1"})
    def test_query_bedrock_guardrail_intervened(self):
        """
        Test query_bedrock with guardrail intervention.
        Expected: Raises RuntimeError with guardrail policy message.
        """
        import header_mapping

        # Mock bedrock_runtime.apply_guardrail to return intervention
        self.mock_bedrock_runtime.apply_guardrail.return_value = {"action": "GUARDRAIL_INTERVENED"}

        with mock.patch("header_mapping.logger") as mock_logger:
            with self.assertRaises(RuntimeError) as context:
                header_mapping.query_bedrock(self.test_request, self.mock_bedrock_runtime, self.test_model)

            # Verify the correct error message
            self.assertIn("Content blocked by guardrail policy", str(context.exception))

            # Verify apply_guardrail was called
            self.mock_bedrock_runtime.apply_guardrail.assert_called_once()

            # Verify converse was not called since guardrail intervened
            self.mock_bedrock_runtime.converse.assert_not_called()

    @mock.patch.dict("os.environ", {"BEDROCK_GUARDRAIL_ID": "test-guardrail-id", "BEDROCK_GUARDRAIL_VERSION": "1"})
    def test_query_bedrock_guardrail_success(self):
        """
        Test query_bedrock with successful guardrail validation.
        Expected: Returns processed mappings after both guardrail and LLM calls.
        """
        import header_mapping

        # Mock bedrock_runtime.apply_guardrail to pass
        self.mock_bedrock_runtime.apply_guardrail.return_value = {"action": "NONE"}
        # Mock bedrock_runtime.converse
        self.mock_bedrock_runtime.converse.return_value = self.bedrock_response

        with mock.patch("header_mapping.sort_mappings_by_confidence") as mock_sort:
            result = header_mapping.query_bedrock(self.test_request, self.mock_bedrock_runtime, self.test_model)

            # Verify both guardrail and converse were called
            self.mock_bedrock_runtime.apply_guardrail.assert_called_once()
            self.mock_bedrock_runtime.converse.assert_called_once()

            # Verify the result matches expected structure
            self.assertEqual(result, self.bedrock_response["output"]["message"]["content"][0]["toolUse"]["input"])

    def test_query_bedrock_invalid_response(self):
        """
        Test query_bedrock with invalid response format.
        Expected: Raises ValueError.
        """
        import header_mapping

        # Mock bedrock_runtime.converse with invalid response
        self.mock_bedrock_runtime.converse.return_value = {"output": {"message": "Invalid format"}}

        with mock.patch("header_mapping.logger") as mock_logger:
            with self.assertRaises(ValueError):
                header_mapping.query_bedrock(self.test_request, self.mock_bedrock_runtime, self.test_model)

            # Verify error was logged
            mock_logger.warning.assert_called_once()
            self.assertIn("Invalid response format", mock_logger.warning.call_args[0][0])

    def test_generate_prompt(self):
        """
        Test generate_prompt function.
        Expected: Returns a prompt string containing headers and schema.
        """
        import header_mapping

        headers = self.test_request["headers"]
        schemas = self.test_request["schemas"]
        tool_name = "test_tool"

        prompt = header_mapping.generate_prompt(headers, schemas, tool_name)

        # Verify prompt contains headers and schema
        self.assertIn(json.dumps(headers), prompt)
        self.assertIn(json.dumps(schemas), prompt)
        self.assertIn("<instructions>", prompt)
        self.assertIn("<strategy>", prompt)
        self.assertIn("<rules>", prompt)
        self.assertIn("<unmatched>", prompt)
        self.assertIn("<input>", prompt)
        self.assertIn("<output>", prompt)
        self.assertIn(f"Use the {tool_name} tool", prompt)

    def test_create_tool_spec(self):
        """
        Test create_tool_spec function.
        Expected: Returns a valid tool configuration with proper schema definitions.
        """
        import header_mapping

        tool_name = "test_tool"
        tool_config = header_mapping.create_tool_spec(schemas=self.test_request["schemas"], tool_name=tool_name)

        # Verify basic structure
        self.assertIsInstance(tool_config, list)
        self.assertEqual(len(tool_config), 1)
        self.assertIn("toolSpec", tool_config[0])

        # Verify tool specification
        tool_spec = tool_config[0]["toolSpec"]
        self.assertEqual(tool_name, tool_spec["name"])
        self.assertIn("description", tool_spec)
        self.assertIn("inputSchema", tool_spec)

        # Verify input schema structure
        input_schema = tool_spec["inputSchema"]["json"]
        self.assertEqual("object", input_schema["type"])

        # Verify properties for each schema type
        self.assertIn("properties", input_schema)
        for schema_type in self.test_request["schemas"].keys():
            self.assertIn(schema_type, input_schema["properties"])
            schema_properties = input_schema["properties"][schema_type]

            # Verify schema structure for each type
            self.assertEqual("object", schema_properties["type"])
            self.assertIn("properties", schema_properties)

            # Verify required properties exist
            properties = schema_properties["properties"]
            self.assertIn("mappings", properties)
            self.assertIn("unmapped_attributes", properties)
            self.assertIn("recommendations", properties)

            # Verify mappings structure
            mappings = properties["mappings"]
            self.assertEqual("array", mappings["type"])
            self.assertIn("items", mappings)
            self.assertIn("properties", mappings["items"])

            # Verify unmapped_attributes structure
            unmapped = properties["unmapped_attributes"]
            self.assertEqual("array", unmapped["type"])
            self.assertIn("items", unmapped)

            # Verify recommendations structure
            recommendations = properties["recommendations"]
            self.assertEqual("array", recommendations["type"])
            self.assertIn("items", recommendations)
            self.assertIn("properties", recommendations["items"])

        # Verify required fields
        self.assertIn("required", input_schema)
        self.assertCountEqual(list(self.test_request["schemas"].keys()), input_schema["required"])

    def test_sort_mappings_by_confidence(self):
        """
        Test sort_mappings_by_confidence with multiple mappings.
        Expected: Mappings are sorted by confidence within same target_header groups.
        """
        import header_mapping
        import copy

        # Get test data from bedrock response and create a deep copy
        test_data = copy.deepcopy(
            self.bedrock_response["output"]["message"]["content"][0]["toolUse"]["input"]["application"]["mappings"]
        )

        # Call the function
        header_mapping.sort_mappings_by_confidence(test_data)

        expected_result = [
            {"source_header": "Application", "target_header": "app_name", "confidence": 0.9},
            {"source_header": "Business Application", "target_header": "app_name", "confidence": 0.5},
            {"source_header": "Database", "target_header": "database_ids", "confidence": 0.8},
            {"source_header": "DB", "target_header": "database_ids", "confidence": 0.8},
            {"source_header": "Owner", "target_header": "app_owner"},
        ]

        self.assertEqual(test_data, expected_result)

    def test_sort_mappings_empty_list(self):
        """
        Test sort_mappings_by_confidence with empty list.
        Expected: Function handles empty list without errors.
        """
        import header_mapping

        empty_list = []
        header_mapping.sort_mappings_by_confidence(empty_list)
        self.assertEqual(empty_list, [])

    def test_sort_mappings_single_item(self):
        """
        Test sort_mappings_by_confidence with single item.
        Expected: Single item list remains unchanged.
        """
        import header_mapping

        single_item = [{"source_header": "Database", "target_header": "database_ids", "confidence": 0.8}]
        header_mapping.sort_mappings_by_confidence(single_item)
        self.assertEqual(len(single_item), 1)
        self.assertEqual(single_item[0]["confidence"], 0.8)

    def test_sort_mappings_missing_confidence(self):
        """
        Test sort_mappings_by_confidence with missing confidence values.
        Expected: Items with missing confidence are treated as confidence 0.
        """
        import header_mapping

        test_data = [
            {"source_header": "Database", "target_header": "database_ids"},
            {"source_header": "Application", "target_header": "database_ids", "confidence": 0.9},
        ]

        expected_result = [
            {"source_header": "Application", "target_header": "database_ids", "confidence": 0.9},
            {"source_header": "Database", "target_header": "database_ids"},
        ]

        header_mapping.sort_mappings_by_confidence(test_data)
        self.assertEqual(test_data, expected_result)


if __name__ == "__main__":
    unittest.main()
