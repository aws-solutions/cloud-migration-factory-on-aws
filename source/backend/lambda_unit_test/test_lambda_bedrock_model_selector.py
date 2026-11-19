#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock

import test_common_utils
from test_common_utils import logger, default_mock_os_environ as mock_os_environ

@mock.patch.dict('os.environ', mock_os_environ)
class LambdaBedrockModelSelectorTest(unittest.TestCase):

    def setUp(self) -> None:
        # Reset any module-level state
        import sys
        if 'lambda_bedrock_model_selector' in sys.modules:
            del sys.modules['lambda_bedrock_model_selector']

    def test_lambda_handler_create_success(self):
        """Test CREATE request triggers model selection and returns SUCCESS with model data."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.get_best_model') as mock_get_best:
            mock_get_best.return_value = {"supported": True, "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"}
            
            with patch('lambda_bedrock_model_selector.send_response') as mock_send:
                event = {
                    'RequestType': 'Create',
                    'StackId': 'test-stack',
                    'RequestId': 'test-request',
                    'LogicalResourceId': 'test-resource'
                }
                context = MagicMock()
                
                lambda_bedrock_model_selector.lambda_handler(event, context)
                
                mock_get_best.assert_called_once()
                mock_send.assert_called_once_with(event, context, 'SUCCESS', {"supported": True, "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"})

    def test_lambda_handler_update_success(self):
        """Test UPDATE request triggers model selection and handles unsupported regions."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.get_best_model') as mock_get_best:
            mock_get_best.return_value = {"supported": False, "modelArn": "Not Supported"}
            
            with patch('lambda_bedrock_model_selector.send_response') as mock_send:
                event = {'RequestType': 'Update'}
                context = MagicMock()
                
                lambda_bedrock_model_selector.lambda_handler(event, context)
                
                mock_get_best.assert_called_once()
                mock_send.assert_called_once_with(event, context, 'SUCCESS', {"supported": False, "modelArn": "Not Supported"})

    def test_lambda_handler_delete_success(self):
        """Test DELETE request skips model selection and returns SUCCESS."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.send_response') as mock_send:
            event = {'RequestType': 'Delete'}
            context = MagicMock()
            
            lambda_bedrock_model_selector.lambda_handler(event, context)
            
            mock_send.assert_called_once_with(event, context, 'SUCCESS')

    def test_lambda_handler_exception(self):
        """
        Test exception during model selection returns FAILED status.
        Please not, this should not happ
        """
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.get_best_model', side_effect=Exception("Test error")):
            with patch('lambda_bedrock_model_selector.send_response') as mock_send:
                event = {'RequestType': 'Create'}
                context = MagicMock()
                
                lambda_bedrock_model_selector.lambda_handler(event, context)
                
                mock_send.assert_called_once_with(event, context, 'FAILED')

    def test_get_foundation_models_success(self):
        """Test foundation models API returns correctly parsed model dictionary."""
        import lambda_bedrock_model_selector
        
        mock_response = {
            'modelSummaries': [
                {'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0', 'modelArn': 'arn:test:1'},
                {'modelId': 'amazon.nova-pro-v1:0', 'modelArn': 'arn:test:2'}
            ]
        }
        
        with patch.object(lambda_bedrock_model_selector.bedrock, 'list_foundation_models', return_value=mock_response):
            result = lambda_bedrock_model_selector.get_foundation_models()
            
            self.assertEqual(len(result), 2)
            self.assertIn('anthropic.claude-3-sonnet-20240229-v1:0', result)
            self.assertEqual(result['anthropic.claude-3-sonnet-20240229-v1:0']['modelArn'], 'arn:test:1')

    def test_get_inference_profiles_success(self):
        """Test inference profiles API with pagination returns profile-to-models mapping."""
        import lambda_bedrock_model_selector
        
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'inferenceProfileSummaries': [
                    {
                        'inferenceProfileArn': 'arn:test:profile:1',
                        'models': [{'modelArn': 'arn:test:model:1'}]
                    }
                ]
            }
        ]
        
        with patch.object(lambda_bedrock_model_selector.bedrock, 'get_paginator', return_value=mock_paginator):
            result = lambda_bedrock_model_selector.get_inference_profiles()
            
            self.assertEqual(len(result), 1)
            self.assertIn('arn:test:profile:1', result)
            self.assertEqual(result['arn:test:profile:1'], ['arn:test:model:1'])
            mock_paginator.paginate.assert_called_once_with(typeEquals='SYSTEM_DEFINED')

    def test_check_model_availability_on_demand(self):
        """Test ON_DEMAND model returns direct model ARN (preferred access type)."""
        import lambda_bedrock_model_selector
        
        model = {
            'modelArn': 'arn:test:model:1',
            'inferenceTypesSupported': ['ON_DEMAND']
        }
        cache = {'profiles': None}
        
        result = lambda_bedrock_model_selector.check_model_availability('test-model', model, cache)
        
        self.assertEqual(result, {"supported": True, "modelArn": "arn:test:model:1"})

    def test_check_model_availability_inference_profile(self):
        """Test INFERENCE_PROFILE model returns matching profile ARN (fallback access)."""
        import lambda_bedrock_model_selector
        
        model = {
            'modelArn': 'arn:test:model:1',
            'inferenceTypesSupported': ['INFERENCE_PROFILE']
        }
        cache = {'profiles': None}
        
        with patch('lambda_bedrock_model_selector.get_inference_profiles') as mock_get_profiles:
            mock_get_profiles.return_value = {
                'arn:test:profile:1': ['arn:test:model:1']
            }
            
            result = lambda_bedrock_model_selector.check_model_availability('test-model', model, cache)
            
            self.assertEqual(result, {"supported": True, "modelArn": "arn:test:profile:1"})
            mock_get_profiles.assert_called_once()

    def test_check_model_availability_no_match(self):
        """Test model with no matching inference profile returns None."""
        import lambda_bedrock_model_selector
        
        model = {
            'modelArn': 'arn:test:model:1',
            'inferenceTypesSupported': ['INFERENCE_PROFILE']
        }
        cache = {'profiles': {'arn:test:profile:1': ['arn:test:model:2']}}
        
        result = lambda_bedrock_model_selector.check_model_availability('test-model', model, cache)
        
        self.assertIsNone(result)

    def test_check_model_availability_no_inference_types(self):
        """Test model with no supported inference types returns None."""
        import lambda_bedrock_model_selector
        
        model = {'modelArn': 'arn:test:model:1'}
        cache = {'profiles': None}
        
        result = lambda_bedrock_model_selector.check_model_availability('test-model', model, cache)
        
        self.assertIsNone(result)

    def test_find_best_model_success_first_model(self):
        """Test highest priority model (Sonnet 4) is selected when available."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.get_foundation_models') as mock_get_models:
            mock_get_models.return_value = {
                'anthropic.claude-sonnet-4-20250514-v1:0': {
                    'modelArn': 'arn:test:sonnet4',
                    'inferenceTypesSupported': ['ON_DEMAND']
                }
            }
            
            result = lambda_bedrock_model_selector.find_best_model()
            
            self.assertEqual(result, {"supported": True, "modelArn": "arn:test:sonnet4"})

    def test_find_best_model_success_fallback_model(self):
        """Test lower priority model (Sonnet 3) is selected when higher priority unavailable."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.get_foundation_models') as mock_get_models:
            mock_get_models.return_value = {
                'anthropic.claude-3-sonnet-20240229-v1:0': {
                    'modelArn': 'arn:test:sonnet3',
                    'inferenceTypesSupported': ['ON_DEMAND']
                }
            }
            
            result = lambda_bedrock_model_selector.find_best_model()
            
            self.assertEqual(result, {"supported": True, "modelArn": "arn:test:sonnet3"})

    def test_find_best_model_no_models_available(self):
        """Test no supported models returns unsupported response."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.get_foundation_models') as mock_get_models:
            mock_get_models.return_value = {}
            
            result = lambda_bedrock_model_selector.find_best_model()
            
            self.assertEqual(result, {"supported": False, "modelArn": "Not Supported"})

    def test_get_best_model_success_first_attempt(self):
        """Test successful model selection on first attempt without retries."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.find_best_model') as mock_find:
            mock_find.return_value = {"supported": True, "modelArn": "arn:test:model"}
            
            result = lambda_bedrock_model_selector.get_best_model()
            
            self.assertEqual(result, {"supported": True, "modelArn": "arn:test:model"})
            mock_find.assert_called_once()

    def test_get_best_model_retry_success(self):
        """Test retry mechanism succeeds after initial failure with exponential backoff."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.find_best_model') as mock_find:
            mock_find.side_effect = [Exception("Temporary error"), {"supported": True, "modelArn": "arn:test:model"}]
            
            with patch('lambda_bedrock_model_selector.time.sleep'):
                result = lambda_bedrock_model_selector.get_best_model()
            
            self.assertEqual(result, {"supported": True, "modelArn": "arn:test:model"})
            self.assertEqual(mock_find.call_count, 2)

    def test_get_best_model_all_retries_fail(self):
        """Test all 3 retry attempts fail and returns unsupported response."""
        import lambda_bedrock_model_selector
        
        with patch('lambda_bedrock_model_selector.find_best_model') as mock_find:
            mock_find.side_effect = Exception("Persistent error")
            
            with patch('lambda_bedrock_model_selector.time.sleep'):
                result = lambda_bedrock_model_selector.get_best_model()
            
            self.assertEqual(result, {"supported": False, "modelArn": "Not Supported"})
            self.assertEqual(mock_find.call_count, 3)

    def test_send_response_success(self):
        """Test CloudFormation response is properly formatted and sent via HTTP PUT."""
        import lambda_bedrock_model_selector
        
        mock_http = MagicMock()
        with patch('lambda_bedrock_model_selector.urllib3.PoolManager', return_value=mock_http):
            event = {
                'ResponseURL': 'https://test.url',
                'StackId': 'test-stack',
                'RequestId': 'test-request',
                'LogicalResourceId': 'test-resource'
            }
            context = MagicMock()
            context.log_stream_name = 'test-stream'
            data = {"test": "data"}
            
            lambda_bedrock_model_selector.send_response(event, context, 'SUCCESS', data)
            
            mock_http.request.assert_called_once()
            call_args = mock_http.request.call_args
            self.assertEqual(call_args[0][0], 'PUT')
            self.assertEqual(call_args[0][1], 'https://test.url')
            
            body = json.loads(call_args[1]['body'])
            self.assertEqual(body['Status'], 'SUCCESS')
            self.assertEqual(body['Data'], {"test": "data"})

    def test_preferred_models_order(self):
        """Test model priority order - lowest priority model selected when others unavailable."""
        import lambda_bedrock_model_selector
        
        # Test that models are checked in correct priority order
        with patch('lambda_bedrock_model_selector.get_foundation_models') as mock_get_models:
            # Only make the lowest priority model available
            mock_get_models.return_value = {
                'amazon.nova-pro-v1:0': {
                    'modelArn': 'arn:test:nova',
                    'inferenceTypesSupported': ['ON_DEMAND']
                }
            }
            
            result = lambda_bedrock_model_selector.find_best_model()
            
            self.assertEqual(result, {"supported": True, "modelArn": "arn:test:nova"})

    def test_inference_profile_caching(self):
        """Test inference profiles are fetched once and cached for subsequent model checks."""
        import lambda_bedrock_model_selector
        
        model1 = {
            'modelArn': 'arn:test:model:1',
            'inferenceTypesSupported': ['INFERENCE_PROFILE']
        }
        model2 = {
            'modelArn': 'arn:test:model:2', 
            'inferenceTypesSupported': ['INFERENCE_PROFILE']
        }
        cache = {'profiles': None}
        
        with patch('lambda_bedrock_model_selector.get_inference_profiles') as mock_get_profiles:
            mock_get_profiles.return_value = {
                'arn:test:profile:1': ['arn:test:model:1', 'arn:test:model:2']
            }
            
            # First call should fetch profiles
            result1 = lambda_bedrock_model_selector.check_model_availability('test-model-1', model1, cache)
            # Second call should use cached profiles
            result2 = lambda_bedrock_model_selector.check_model_availability('test-model-2', model2, cache)
            
            # get_inference_profiles should only be called once due to caching
            mock_get_profiles.assert_called_once()
            self.assertEqual(result1, {"supported": True, "modelArn": "arn:test:profile:1"})
            self.assertEqual(result2, {"supported": True, "modelArn": "arn:test:profile:1"})

if __name__ == '__main__':
    unittest.main()