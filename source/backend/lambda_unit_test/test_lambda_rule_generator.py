#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock

import boto3
from moto import mock_aws

import test_common_utils
from test_common_utils import logger, default_mock_os_environ as mock_os_environ


@mock_aws
@mock.patch.dict('os.environ', {**mock_os_environ, 'model': 'test-model', 'SCHEMA_TABLE_NAME': 'test-schema-table'})
class LambdaRuleGeneratorTest(unittest.TestCase):

    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        self.ddb_client = boto3.client('dynamodb')
        self.schema_table_name = 'test-schema-table'
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name)

    def test_lambda_handler_success_prioritizing(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.converse.return_value = {
                'output': {
                    'message': {
                        'content': [{
                            'toolUse': {
                                'input': {
                                    "rule_type": "PRIORITIZING",
                                    "rule_name": "test-rule",
                                    "rule_description": "Test rule",
                                    "sub_type": "SCORING",
                                    "status": "ENABLED",
                                    "asset_type": "server",
                                    "attr_key": "server_storage_size",
                                    "scoring_criteria": [{"complexity_score": 50}]
                                }
                            }
                        }]
                    }
                }
            }
            
            event = {
                "body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "prioritize servers by storage size"})
            }
            
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(200, response['statusCode'])
            self.assertIn('rule_type', json.loads(response['body']))

    def test_lambda_handler_success_grouping(self):
        import lambda_rule_generator

        with patch("lambda_rule_generator.bedrock_runtime") as mock_bedrock:
            mock_bedrock.converse.return_value = {
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "input": {
                                        "rule_type": "GROUPING_INCLUSIVE",
                                        "rule_name": "test-rule",
                                        "relationships": [{"asset_type": "server", "asset_key": "app_ids"}],
                                    }
                                }
                            }
                        ]
                    }
                }
            }

            event = {"body": json.dumps({"rule_type": "GROUPING", "user_input": "Group apps sharing servers"})}

            response = lambda_rule_generator.lambda_handler(event, None)

            self.assertEqual(200, response["statusCode"])
            self.assertIn("rule_type", json.loads(response["body"]))

    def test_lambda_handler_malformed_json(self):
        import lambda_rule_generator
        
        event = {"body": "invalid json"}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertEqual("malformed json input", response['body'])

    def test_lambda_handler_missing_rule_type(self):
        import lambda_rule_generator
        
        event = {"body": json.dumps({})}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertIn("rule_type is required. Supported values: PRIORITIZING, GROUPING", response['body'])

    def test_lambda_handler_empty_rule_type(self):
        import lambda_rule_generator
        
        event = {"body": json.dumps({"rule_type": ""})}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertIn("rule_type is invalid. Supported values: PRIORITIZING, GROUPING", response['body'])

    def test_lambda_handler_invalid_rule_type(self):
        import lambda_rule_generator
        
        event = {"body": json.dumps({"rule_type": "xyz"})}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertIn("rule_type is invalid. Supported values: PRIORITIZING, GROUPING", response['body'])

    def test_lambda_handler_numeric_rule_type(self):
        import lambda_rule_generator
        
        event = {"body": json.dumps({"rule_type": 1})}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertIn("rule_type is invalid. Supported values: PRIORITIZING, GROUPING", response['body'])

    def test_lambda_handler_object_rule_type(self):
        import lambda_rule_generator
        
        event = {"body": json.dumps({"rule_type": {}})}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertIn("rule_type is invalid. Supported values: PRIORITIZING, GROUPING", response['body'])

    def test_lambda_handler_empty_user_input(self):
        import lambda_rule_generator
        
        event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": ""})}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertIn("user_input is required", response['body'])

    def test_lambda_handler_whitespace_user_input(self):
        import lambda_rule_generator
        
        event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "   "})}
        response = lambda_rule_generator.lambda_handler(event, None)
        
        self.assertEqual(400, response['statusCode'])
        self.assertIn("user_input is required", response['body'])

    def test_lambda_handler_bedrock_access_denied(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.converse.side_effect = Exception("AccessDeniedException")
            
            event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "test input"})}
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(400, response['statusCode'])
            self.assertIn("Access denied to AI model", response['body'])

    def test_lambda_handler_bedrock_validation_error(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.converse.side_effect = Exception("ValidationException")
            
            event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "test input"})}
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(400, response['statusCode'])
            self.assertIn("Invalid request to AI model", response['body'])

    def test_lambda_handler_bedrock_throttling_error(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.converse.side_effect = Exception("ThrottlingException")
            
            event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "test input"})}
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(400, response['statusCode'])
            self.assertIn("AI service is busy", response['body'])

    def test_lambda_handler_generic_exception(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.get_schema', side_effect=Exception("Generic error")):
            event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "test input"})}
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(500, response['statusCode'])
            self.assertEqual("internal server exception", response['body'])

    @mock.patch.dict('os.environ', {**mock_os_environ, 'model': 'test-model', 'SCHEMA_TABLE_NAME': 'test-schema-table', 'BEDROCK_GUARDRAIL_ID': 'test-guardrail-id', 'BEDROCK_GUARDRAIL_VERSION': '1'})
    def test_lambda_handler_guardrail_intervened(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.apply_guardrail.return_value = {
                'action': 'GUARDRAIL_INTERVENED'
            }
            
            event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "test input"})}
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(400, response['statusCode'])
            self.assertIn("Content blocked by guardrail policy", response['body'])

    @mock.patch.dict('os.environ', {**mock_os_environ, 'model': 'test-model', 'SCHEMA_TABLE_NAME': 'test-schema-table', 'BEDROCK_GUARDRAIL_ID': 'test-guardrail-id', 'BEDROCK_GUARDRAIL_VERSION': '1'})
    def test_lambda_handler_guardrail_success(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.apply_guardrail.return_value = {
                'action': 'NONE'
            }
            mock_bedrock.converse.return_value = {
                'output': {
                    'message': {
                        'content': [{
                            'toolUse': {
                                'input': {
                                    "rule_type": "PRIORITIZING",
                                    "rule_name": "test-rule",
                                    "rule_description": "Test rule",
                                    "sub_type": "SCORING",
                                    "status": "ENABLED",
                                    "asset_type": "server",
                                    "attr_key": "server_storage_size",
                                    "scoring_criteria": [{"complexity_score": 50}]
                                }
                            }
                        }]
                    }
                }
            }
            
            event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "test input"})}
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(200, response['statusCode'])
            self.assertIn('rule_type', json.loads(response['body']))
            mock_bedrock.apply_guardrail.assert_called_once()
            mock_bedrock.converse.assert_called_once()

    def test_get_schema_success(self):
        import lambda_rule_generator
        
        # Add test data to schema table
        self.ddb_client.put_item(
            TableName=self.schema_table_name,
            Item={
                'schema_name': {'S': 'server'},
                'attributes': {
                    'L': [
                        {
                            'M': {
                                'name': {'S': 'server_id'},
                                'type': {'S': 'string'},
                                'description': {'S': 'Server ID'}
                            }
                        },
                        {
                            'M': {
                                'name': {'S': 'server_storage_size'},
                                'type': {'S': 'integer'},
                                'listvalue': {'S': '100,200,500'}
                            }
                        },
                        {
                            'M': {
                                'name': {'S': 'app_ids'},
                                'type': {'S': 'multivalue-relationship'},
                            }
                        }
                    ]
                }
            }
        )
        
        schema = lambda_rule_generator.get_schema(lambda_rule_generator.RuleType.GROUPING)
        
        self.assertIn('server', schema)
        self.assertEqual(schema['server'][0]['name'], 'server_id')
        self.assertEqual(schema['server'][1]['name'], 'server_storage_size')
        self.assertEqual(schema['server'][2]['name'], 'app_ids')

        schema = lambda_rule_generator.get_schema(lambda_rule_generator.RuleType.PRIORITIZING)
        
        self.assertIn('server', schema)
        self.assertEqual(len(schema['server']), 2)
        self.assertEqual(schema['server'][0]['name'], 'server_id')
        self.assertEqual(schema['server'][1]['name'], 'server_storage_size')

    def test_get_schema_filters_schema_names(self):
        import lambda_rule_generator
        
        # Add schemas with different names
        self.ddb_client.put_item(
            TableName=self.schema_table_name,
            Item={
                'schema_name': {'S': 'app'},
                'attributes': {'L': [{'M': {'name': {'S': 'app_id'}, 'type': {'S': 'string'}}}]}
            }
        )
        self.ddb_client.put_item(
            TableName=self.schema_table_name,
            Item={
                'schema_name': {'S': 'app_group'},
                'schema_type': {'S': 'custom'},
                'attributes': {'L': [{'M': {'name': {'S': 'app_ids'}, 'type': {'S': 'multivalue-relationship'}}}]}
            }
        )
        self.ddb_client.put_item(
            TableName=self.schema_table_name,
            Item={
                'schema_name': {'S': 'invalid_schema'},
                'attributes': {'L': [{'M': {'name': {'S': 'invalid_id'}, 'type': {'S': 'string'}}}]}
            }
        )
        for rule_type in [lambda_rule_generator.RuleType.GROUPING, lambda_rule_generator.RuleType.PRIORITIZING]:
            schema = lambda_rule_generator.get_schema(rule_type)        
            self.assertIn('app', schema)
            self.assertIn('app_group', schema)
            self.assertNotIn('invalid_schema', schema)

    def test_get_schema_handles_missing_attributes(self):
        import lambda_rule_generator
        
        self.ddb_client.put_item(
            TableName=self.schema_table_name,
            Item={'schema_name': {'S': 'database'}}
        )
        
        for rule_type in [lambda_rule_generator.RuleType.GROUPING, lambda_rule_generator.RuleType.PRIORITIZING]:
            schema = lambda_rule_generator.get_schema(rule_type)        
            self.assertIn('database', schema)
            self.assertEqual(schema['database'], [])

    def test_get_schema_exception_handling(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.cmf_boto.resource') as mock_resource:
            mock_resource.side_effect = Exception("DynamoDB error")
            
            for rule_type in [lambda_rule_generator.RuleType.GROUPING, lambda_rule_generator.RuleType.PRIORITIZING]:
                schema = lambda_rule_generator.get_schema(rule_type)
                self.assertEqual(schema, {})

    def test_generate_rule_success_prioritizing(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.converse.return_value = {
                'output': {
                    'message': {
                        'content': [{
                            'toolUse': {
                                'input': {
                                    "rule_type": "PRIORITIZING",
                                    "rule_name": "test-rule",
                                    "rule_description": "Test rule",
                                    "sub_type": "SCORING",
                                    "status": "ENABLED",
                                    "asset_type": "server",
                                    "attr_key": "server_storage_size",
                                    "scoring_criteria": [{"complexity_score": 50}]
                                }
                            }
                        }]
                    }
                }
            }
            
            schemas = {"server": []}
            result = lambda_rule_generator.generate_rule(lambda_rule_generator.RuleType.PRIORITIZING, "test input", schemas)
            
            self.assertEqual(result['rule_type'], 'PRIORITIZING')
            self.assertEqual(result['rule_name'], 'test-rule')
            
            # Verify bedrock was called with tool configuration
            mock_bedrock.converse.assert_called_once()
            call_args = mock_bedrock.converse.call_args
            self.assertIn('toolConfig', call_args[1])
            # Format the expected tool spec with the schema names
            expected_tool_spec = lambda_rule_generator.TOOL_SPECS[lambda_rule_generator.RuleType.PRIORITIZING].format(
                schema_names=json.dumps(list(schemas.keys()))
            )
            expected_tool_spec_json = json.loads(expected_tool_spec)
            actual_tool_spec = call_args[1]["toolConfig"]["tools"][0]["toolSpec"]
            
            # Compare the formatted and parsed JSON objects
            self.assertEqual(actual_tool_spec, expected_tool_spec_json)
            self.assertEqual(call_args[1]['toolConfig']['toolChoice']['tool']['name'], 'rule_generator')

    def test_generate_rule_success_grouping(self):
        import lambda_rule_generator

        with patch("lambda_rule_generator.bedrock_runtime") as mock_bedrock:
            mock_bedrock.converse.return_value = {
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "input": {
                                        "rule_type": "GROUPING_EXCLUSIVE",
                                        "rule_name": "Split apps and servers by subnet",
                                        "relationships": [{"asset_type": "server", "asset_key": "subnet_IDs"}],
                                        "rule_description": "This rule segments servers based on their subnet IDs, ensuring servers in different subnets are placed in separate groups",
                                        "status": "ENABLED",
                                    }
                                }
                            }
                        ]
                    }
                }
            }

            schemas = {"server": []}
            result = lambda_rule_generator.generate_rule(lambda_rule_generator.RuleType.GROUPING, "test input", schemas)

            self.assertEqual(result["rule_type"], "GROUPING_EXCLUSIVE")
            self.assertEqual(result["rule_name"], "Split apps and servers by subnet")

            # Verify bedrock was called with tool configuration
            mock_bedrock.converse.assert_called_once()
            call_args = mock_bedrock.converse.call_args
            self.assertIn("toolConfig", call_args[1])

            # Format the expected tool spec with the schema names
            expected_tool_spec = lambda_rule_generator.TOOL_SPECS[lambda_rule_generator.RuleType.GROUPING].format(
                schema_names=json.dumps(list(schemas.keys()))
            )
            expected_tool_spec_json = json.loads(expected_tool_spec)
            actual_tool_spec = call_args[1]["toolConfig"]["tools"][0]["toolSpec"]
            
            # Compare the formatted and parsed JSON objects
            self.assertEqual(actual_tool_spec, expected_tool_spec_json)
            self.assertEqual(call_args[1]["toolConfig"]["toolChoice"]["tool"]["name"], "rule_generator")

    def test_generate_rule_invalid_response_structure(self):
        import lambda_rule_generator
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.converse.return_value = {
                'output': {
                    'message': {
                        'content': [{
                            'toolUse': {
                                'input': "invalid structure"
                            }
                        }]
                    }
                }
            }
            
            result = lambda_rule_generator.generate_rule(lambda_rule_generator.RuleType.PRIORITIZING, "test input", {"server": []})
            self.assertEqual(result, "invalid structure")

    def test_generate_rule_bedrock_exceptions(self):
        import lambda_rule_generator
        
        test_cases = [
            ("AccessDeniedException", "Access denied to AI model"),
            ("ValidationException", "Invalid request to AI model"),
            ("ThrottlingException", "AI service is busy"),
            ("GenericException", "AI service error")
        ]
        
        schemas = {"server": []}
        for exception_type, expected_message in test_cases:
            with self.subTest(exception=exception_type):
                with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
                    mock_bedrock.converse.side_effect = Exception(exception_type)
                    
                    with self.assertRaises(ValueError) as context:
                        lambda_rule_generator.generate_rule(lambda_rule_generator.RuleType.PRIORITIZING, "test input", schemas)
                    
                    self.assertIn(expected_message, str(context.exception))

    def test_generate_rule_prompt_contains_schema_prioritizing(self):
        import lambda_rule_generator
        
        test_schema = {"server": [{"name": "server_id", "type": "string"}]}
        
        with patch('lambda_rule_generator.bedrock_runtime') as mock_bedrock:
            mock_bedrock.converse.return_value = {
                'output': {
                    'message': {
                        'content': [{
                            'toolUse': {
                                'input': {"rule_type": "PRIORITIZING"}
                            }
                        }]
                    }
                }
            }
            
            lambda_rule_generator.generate_rule(lambda_rule_generator.RuleType.PRIORITIZING, "test input", test_schema)
            
            # Verify the prompt contains the schema
            call_args = mock_bedrock.converse.call_args
            prompt_text = call_args[1]['messages'][0]['content'][0]['text']
            self.assertIn(json.dumps(test_schema), prompt_text)
            self.assertIn("test input", prompt_text)
            self.assertIn("SCORING", prompt_text)
            self.assertIn("SORTING", prompt_text)
            self.assertIn("complexity_score", prompt_text)

    def test_generate_rule_prompt_contains_schema_grouping(self):
        import lambda_rule_generator

        test_schema = {"server": [{"name": "server_id", "type": "string"}]}

        with patch("lambda_rule_generator.bedrock_runtime") as mock_bedrock:
            mock_bedrock.converse.return_value = {
                "output": {"message": {"content": [{"toolUse": {"input": {"rule_type": "GROUPING_INCLUSIVE"}}}]}}
            }

            lambda_rule_generator.generate_rule(lambda_rule_generator.RuleType.GROUPING, "group input", test_schema)

            # Verify the prompt contains the schema
            call_args = mock_bedrock.converse.call_args
            prompt_text = call_args[1]["messages"][0]["content"][0]["text"]
            self.assertIn(json.dumps(test_schema), prompt_text)
            self.assertIn("group input", prompt_text)
            self.assertIn("GROUPING_INCLUSIVE", prompt_text)
            self.assertIn("GROUPING_EXCLUSIVE", prompt_text)

    def test_lambda_handler_model_not_supported(self):
        """Test lambda_handler when model is 'Not Supported'."""
        import lambda_rule_generator
        
        with patch.object(lambda_rule_generator, 'model', 'Not Supported'):
            event = {"body": json.dumps({"rule_type": "PRIORITIZING", "user_input": "test input"})}
            response = lambda_rule_generator.lambda_handler(event, None)
            
            self.assertEqual(500, response['statusCode'])
            self.assertIn("No preferred model was available", response['body'])

if __name__ == '__main__':
    unittest.main()