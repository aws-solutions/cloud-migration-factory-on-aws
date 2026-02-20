#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from datetime import datetime, timedelta
import json
import unittest
from unittest import mock

from moto import mock_aws

import test_common_utils

# Mock the urllib.request.urlopen before importing the module
@mock.patch('urllib.request.urlopen')
def setup_module_mocks(mock_urlopen):
    """
    Setup mocks for the lambda_genai_sockets_auth module before importing it.
    This prevents actual HTTP requests when the module is imported.
    
    Args:
        mock_urlopen: Mock for urllib.request.urlopen
        
    Returns:
        The imported lambda_genai_sockets_auth module with mocks in place
    """
    # Mock the response from the jwks.json endpoint
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps({
        'keys': [
            {
                'kid': 'test-key-id',
                'kty': 'RSA',
                'n': 'test-n',
                'e': 'AQAB'
            }
        ]
    }).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    # Now it's safe to import the module
    import lambda_genai_sockets_auth
    
    # Initialize the key cache with real datetime objects
    lambda_genai_sockets_auth.key_cache['expiration'] = datetime.now() + timedelta(hours=24)
    lambda_genai_sockets_auth.key_cache['last_refresh'] = datetime.now()
    
    return lambda_genai_sockets_auth

@mock_aws
class LambdaGenAISocketsAuthTest(unittest.TestCase):

    @mock.patch.dict('os.environ', {
        **test_common_utils.default_mock_os_environ,
        'user_pool_id': 'us-east-1_testpool',
        'app_client_id': 'test-client-id',
        'aws_region': 'us-east-1'
    })
    def setUp(self) -> None:
        """
        Set up the test environment with mocked module and test events.
        """
        # Import the module with mocks in place
        self.lambda_module = setup_module_mocks()
        super().setUp()
        self.event_with_no_token = {
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:api-id/stage/GET/resource',
            'headers': {}
        }
        self.event_with_token = {
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:api-id/stage/GET/resource',
            'headers': {
                'Sec-WebSocket-Protocol': 'test-token.test-token'
            },
        }

    @mock.patch('lambda_genai_sockets_auth.verify_token')
    def test_lambda_handler_no_token(self, mock_verify_token):
        """
        Test lambda_handler when no token is provided in the request.
        Expected: Returns a Deny policy with 'user' as principalId.
        """
        response = self.lambda_module.lambda_handler(self.event_with_no_token, None)
        self.assertEqual('user', response['principalId'])
        self.assertEqual('Deny', response['policyDocument']['Statement'][0]['Effect'])
        mock_verify_token.assert_not_called()

    @mock.patch('lambda_genai_sockets_auth.verify_token')
    def test_lambda_handler_invalid_token(self, mock_verify_token):
        """
        Test lambda_handler when an invalid token is provided.
        Expected: Returns a Deny policy with 'user' as principalId.
        """
        mock_verify_token.return_value = False
        response = self.lambda_module.lambda_handler(self.event_with_token, None)
        self.assertEqual('user', response['principalId'])
        self.assertEqual('Deny', response['policyDocument']['Statement'][0]['Effect'])
        mock_verify_token.assert_called_once_with('test-token.test-token')

    @mock.patch('lambda_genai_sockets_auth.verify_token')
    def test_lambda_handler_no_admin_group(self, mock_verify_token):
        """
        Test lambda_handler when token is valid but user is not in admin group.
        Expected: Returns a Deny policy with user's sub as principalId.
        """
        mock_verify_token.return_value = {
            'sub': 'test-user-id',
            'email': 'test@example.com',
            'cognito:groups': ['user']
        }
        response = self.lambda_module.lambda_handler(self.event_with_token, None)
        self.assertEqual('test-user-id', response['principalId'])
        self.assertEqual('Deny', response['policyDocument']['Statement'][0]['Effect'])
        mock_verify_token.assert_called_once_with('test-token.test-token')

    @mock.patch('lambda_genai_sockets_auth.verify_token')
    def test_lambda_handler_no_groups(self, mock_verify_token):
        """
        Test lambda_handler when token is valid but no groups are present.
        Expected: Returns a Deny policy with user's sub as principalId.
        """
        mock_verify_token.return_value = {
            'sub': 'test-user-id',
            'email': 'test@example.com'
        }
        response = self.lambda_module.lambda_handler(self.event_with_token, None)
        self.assertEqual('test-user-id', response['principalId'])
        self.assertEqual('Deny', response['policyDocument']['Statement'][0]['Effect'])
        mock_verify_token.assert_called_once_with('test-token.test-token')

    @mock.patch('lambda_genai_sockets_auth.verify_token')
    def test_lambda_handler_with_admin_group(self, mock_verify_token):
        """
        Test lambda_handler when token is valid and user is in admin group.
        Expected: Returns an Allow policy with user context information.
        """
        mock_verify_token.return_value = {
            'sub': 'test-user-id',
            'email': 'test@example.com',
            'cognito:groups': ['admin', 'user']
        }
        response = self.lambda_module.lambda_handler(self.event_with_token, None)
        self.assertEqual('test-user-id', response['principalId'])
        self.assertEqual('Allow', response['policyDocument']['Statement'][0]['Effect'])
        self.assertEqual('test-user-id', response['context']['user_id'])
        self.assertEqual('test@example.com', response['context']['email'])
        self.assertEqual('admin user', response['context']['groups'])
        mock_verify_token.assert_called_once_with('test-token.test-token')

    def test_generate_policy_without_context(self):
        """
        Test generate_policy function without context parameter.
        Expected: Returns a policy document without context field.
        """
        policy = self.lambda_module.generate_policy('test-principal', 'Allow', 'test-resource')
        self.assertEqual('test-principal', policy['principalId'])
        self.assertEqual('Allow', policy['policyDocument']['Statement'][0]['Effect'])
        self.assertEqual('test-resource', policy['policyDocument']['Statement'][0]['Resource'])
        self.assertNotIn('context', policy)

    def test_generate_policy_with_context(self):
        """
        Test generate_policy function with context parameter.
        Expected: Returns a policy document with context field.
        """
        test_context = {'key1': 'value1', 'key2': 'value2'}
        policy = self.lambda_module.generate_policy('test-principal', 'Deny', 'test-resource', test_context)
        self.assertEqual('test-principal', policy['principalId'])
        self.assertEqual('Deny', policy['policyDocument']['Statement'][0]['Effect'])
        self.assertEqual('test-resource', policy['policyDocument']['Statement'][0]['Resource'])
        self.assertEqual(test_context, policy['context'])

    @mock.patch('urllib.request.urlopen')
    def test_get_public_keys(self, mock_urlopen):
        """
        Test get_public_keys function to ensure it returns cached keys.
        Expected: Returns a dictionary of keys with kid as the key.
        """

        mock_response = mock.Mock()
        mock_response.read.return_value = json.dumps({
            'keys': [
                {
                    'kid': 'test-key-id',
                    'kty': 'RSA',
                    'n': 'new-test-n',
                    'e': 'AQAB'
                }
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        keys = self.lambda_module.get_public_keys()
        self.assertIsInstance(keys, dict)
        self.assertIn('test-key-id', keys)
        self.assertEqual('RSA', keys['test-key-id']['kty'])
        
    @mock.patch('urllib.request.urlopen')
    def test_get_public_keys_expired_cache(self, mock_urlopen):
        """
        Test get_public_keys when cache is expired.
        Expected: Refreshes the cache and returns updated keys.
        """
        # Set up mocks with real datetime objects
        past_time = datetime.now() -  timedelta(hours=2) # 2 hours before the fixed time
        
        # Set cache expiration to past
        self.lambda_module.key_cache['expiration'] = past_time
        
        # Set up new keys for refresh
        mock_response = mock.Mock()
        mock_response.read.return_value = json.dumps({
            'keys': [
                {
                    'kid': 'new-key-id',
                    'kty': 'RSA',
                    'n': 'new-test-n',
                    'e': 'AQAB'
                }
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Call the function
        keys = self.lambda_module.get_public_keys()
        
        # Verify results
        self.assertIn('new-key-id', keys)
        mock_urlopen.assert_called_once()
        
    @mock.patch('jose.jwt.get_unverified_headers')
    @mock.patch('lambda_genai_sockets_auth.get_public_keys')
    def test_verify_token_invalid_kid(self, mock_get_public_keys, mock_get_unverified_headers):
        """
        Test verify_token when token has an invalid key ID.
        Expected: Returns False indicating invalid token.
        """
        # Setup mocks
        mock_get_unverified_headers.return_value = {'kid': 'invalid-key-id'}
        mock_get_public_keys.side_effect = [
            # First call returns empty dict to simulate key not found
            {},
            # Second call after refresh still doesn't have the key
            {}
        ]
        
        # Call the function
        result = self.lambda_module.verify_token('test-token.test-token')
        
        # Verify results
        self.assertFalse(result)
        mock_get_unverified_headers.assert_called_once_with('test-token.test-token')
        self.assertEqual(2, mock_get_public_keys.call_count)
        
    @mock.patch('jose.jwt.get_unverified_headers')
    @mock.patch('jose.jwk.construct')
    @mock.patch('jose.jwt.get_unverified_claims')
    @mock.patch('time.time')
    @mock.patch('lambda_genai_sockets_auth.get_public_keys')
    def test_verify_token_key_rotation(self, mock_get_public_keys, mock_time, 
                                      mock_get_unverified_claims, mock_construct, mock_get_unverified_headers):
        """
        Test verify_token when a key rotation has occurred.
        Expected: Refreshes the key cache and successfully verifies the token.
        """
        # Setup mocks
        mock_get_unverified_headers.return_value = {'kid': 'rotated-key-id'}
        
        # First call doesn't have the rotated key
        # Second call after refresh has the rotated key
        mock_get_public_keys.side_effect = [
            {},  # First call - key not found
            {    # Second call after refresh - key found
                'rotated-key-id': {
                    'kid': 'rotated-key-id',
                    'kty': 'RSA',
                    'n': 'rotated-n',
                    'e': 'AQAB'
                }
            }
        ]
                
        # Set up remaining mocks
        mock_public_key = mock.Mock()
        mock_public_key.verify.return_value = True
        mock_construct.return_value = mock_public_key
        
        test_claims = {
            'exp': 3000, 
            'aud': 'test-client-id',
            'sub': 'test-user-id',
            'email': 'test@example.com'
        }
        mock_get_unverified_claims.return_value = test_claims
        mock_time.return_value = 2000  # Current time is before expiration
        
        # Call the function
        result = self.lambda_module.verify_token('test-token.test-token')
        
        # Verify results
        self.assertEqual(test_claims, result)
        mock_get_unverified_headers.assert_called_once_with('test-token.test-token')
        self.assertEqual(2, mock_get_public_keys.call_count)

    @mock.patch('jose.jwt.get_unverified_headers')
    @mock.patch('jose.jwk.construct')
    @mock.patch('lambda_genai_sockets_auth.get_public_keys')
    def test_verify_token_invalid_signature(self, mock_get_public_keys, mock_construct, mock_get_unverified_headers):
        """
        Test verify_token when token has an invalid signature.
        Expected: Returns False indicating invalid token.
        """
        mock_get_unverified_headers.return_value = {'kid': 'test-key-id'}
        mock_get_public_keys.return_value = {
            'test-key-id': {
                'kid': 'test-key-id',
                'kty': 'RSA',
                'n': 'test-n',
                'e': 'AQAB'
            }
        }
        mock_public_key = mock.Mock()
        mock_public_key.verify.return_value = False
        mock_construct.return_value = mock_public_key
        
        result = self.lambda_module.verify_token('test-token.test-token')
        self.assertFalse(result)
        mock_get_unverified_headers.assert_called_once_with('test-token.test-token')
        mock_construct.assert_called_once()
        mock_public_key.verify.assert_called_once()

    @mock.patch('jose.jwt.get_unverified_headers')
    @mock.patch('jose.jwk.construct')
    @mock.patch('jose.jwt.get_unverified_claims')
    @mock.patch('time.time')
    @mock.patch('lambda_genai_sockets_auth.get_public_keys')
    def test_verify_token_expired(self, mock_get_public_keys, mock_time, mock_get_unverified_claims, mock_construct, mock_get_unverified_headers):
        """
        Test verify_token when token is expired.
        Expected: Returns False indicating invalid token.
        """
        mock_get_unverified_headers.return_value = {'kid': 'test-key-id'}
        mock_get_public_keys.return_value = {
            'test-key-id': {
                'kid': 'test-key-id',
                'kty': 'RSA',
                'n': 'test-n',
                'e': 'AQAB'
            }
        }
        mock_public_key = mock.Mock()
        mock_public_key.verify.return_value = True
        mock_construct.return_value = mock_public_key
        mock_get_unverified_claims.return_value = {'exp': 1000, 'aud': 'test-client-id'}
        mock_time.return_value = 2000  # Current time is after expiration
        
        result = self.lambda_module.verify_token('test-token.test-token')
        self.assertFalse(result)
        mock_get_unverified_headers.assert_called_once_with('test-token.test-token')
        mock_get_unverified_claims.assert_called_once_with('test-token.test-token')

    @mock.patch('jose.jwt.get_unverified_headers')
    @mock.patch('jose.jwk.construct')
    @mock.patch('jose.jwt.get_unverified_claims')
    @mock.patch('time.time')
    @mock.patch('lambda_genai_sockets_auth.get_public_keys')
    def test_verify_token_wrong_audience(self, mock_get_public_keys, mock_time, mock_get_unverified_claims, mock_construct, mock_get_unverified_headers):
        """
        Test verify_token when token has wrong audience.
        Expected: Returns False indicating invalid token.
        """
        mock_get_unverified_headers.return_value = {'kid': 'test-key-id'}
        mock_get_public_keys.return_value = {
            'test-key-id': {
                'kid': 'test-key-id',
                'kty': 'RSA',
                'n': 'test-n',
                'e': 'AQAB'
            }
        }
        mock_public_key = mock.Mock()
        mock_public_key.verify.return_value = True
        mock_construct.return_value = mock_public_key
        mock_get_unverified_claims.return_value = {'exp': 3000, 'aud': 'wrong-client-id'}
        mock_time.return_value = 2000  # Current time is before expiration
        
        result = self.lambda_module.verify_token('test-token.test-token')
        self.assertFalse(result)
        mock_get_unverified_headers.assert_called_once_with('test-token.test-token')
        mock_get_unverified_claims.assert_called_once_with('test-token.test-token')

    @mock.patch('jose.jwt.get_unverified_headers')
    @mock.patch('jose.jwk.construct')
    @mock.patch('jose.jwt.get_unverified_claims')
    @mock.patch('time.time')
    @mock.patch('lambda_genai_sockets_auth.get_public_keys')
    def test_verify_token_valid(self, mock_get_public_keys, mock_time, mock_get_unverified_claims, mock_construct, mock_get_unverified_headers):
        """
        Test verify_token with a valid token.
        Expected: Returns the token claims.
        """
        mock_get_unverified_headers.return_value = {'kid': 'test-key-id'}
        mock_get_public_keys.return_value = {
            'test-key-id': {
                'kid': 'test-key-id',
                'kty': 'RSA',
                'n': 'test-n',
                'e': 'AQAB'
            }
        }
        mock_public_key = mock.Mock()
        mock_public_key.verify.return_value = True
        mock_construct.return_value = mock_public_key
        test_claims = {
            'exp': 3000, 
            'aud': 'test-client-id',
            'sub': 'test-user-id',
            'email': 'test@example.com',
            'cognito:groups': ['admin']
        }
        mock_get_unverified_claims.return_value = test_claims
        mock_time.return_value = 2000  # Current time is before expiration
        
        result = self.lambda_module.verify_token('test-token.test-token')
        self.assertEqual(test_claims, result)
        mock_get_unverified_headers.assert_called_once_with('test-token.test-token')
        mock_get_unverified_claims.assert_called_once_with('test-token.test-token')