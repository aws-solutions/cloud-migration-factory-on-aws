#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
import json
import os
import sys
from unittest import mock
from unittest.mock import patch, MagicMock, call

import boto3
import botocore
from moto import mock_aws
from test_common_utils import default_mock_os_environ

# Add lambda function directory to Python path
lambda_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'lambda_functions', 'lambda_user_subscription')
if lambda_dir not in sys.path:
    sys.path.append(lambda_dir)

mock_os_environ = {
    **default_mock_os_environ,
    'topicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic',
    'application': 'cmf',
    'environment': 'unittest',
    'AWS_DEFAULT_REGION': 'us-east-1'
}

@mock.patch.dict('os.environ', mock_os_environ)
class LambdaUserSubscriptionTest(unittest.TestCase):
    """Test cases for lambda_user_subscription.py"""

    def setUp(self):
        """Set up test fixtures"""
        # Set up boto3 resources
        boto3.setup_default_session()

        # Test events
        self.valid_create_event = {
            'version': '1',
            'region': 'us-east-1',
            'userPoolId': 'us-east-1_testpool',
            'userName': 'testuser',
            'callerContext': {
                'awsSdkVersion': 'aws-sdk-unknown-unknown',
                'clientId': 'client123'
            },
            'triggerSource': 'PreSignUp_AdminCreateUser',
            'request': {
                'userAttributes': {
                    'email': 'test@example.com',
                    'email_verified': 'true'
                }
            },
            'response': {
                'autoConfirmUser': False,
                'autoVerifyEmail': False,
                'autoVerifyPhone': False
            }
        }

        self.valid_auth_event = {
            'version': '1',
            'region': 'us-east-1',
            'userPoolId': 'us-east-1_testpool',
            'userName': 'testuser',
            'callerContext': {
                'awsSdkVersion': 'aws-sdk-unknown-unknown',
                'clientId': 'client123'
            },
            'triggerSource': 'PostAuthentication_Authentication',
            'request': {
                'userAttributes': {
                    'email': 'test@example.com',
                    'email_verified': 'true'
                }
            },
            'response': {}
        }

    @mock_aws
    @patch('lambda_user_subscription.sns')
    @patch('lambda_user_subscription.subscriptions_table')
    def test_create_user_success(self, mock_table, mock_sns):
        """Test successful user creation flow"""
        import lambda_user_subscription

        # Mock SNS response
        mock_sns.subscribe.return_value = {
            'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id'
        }

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(self.valid_create_event, None)

            # Verify SNS subscription call
            mock_sns.subscribe.assert_called_once_with(
                TopicArn='arn:aws:sns:us-east-1:123456789012:test-topic',
                Protocol='email',
                Endpoint='test@example.com',
                ReturnSubscriptionArn=True,
                Attributes={
                    'FilterPolicy': json.dumps({"Email": ["test@example.com"]})
                }
            )

            # Verify DynamoDB put_item call
            mock_table.put_item.assert_called_once_with(
                Item={
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'subscription_arn': 'arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id'
                }
            )

            # Verify logging
            mock_logger.info.assert_has_calls([
                call('Created SNS subscription for user: {"SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id"}'),
                call("Stored subscription details for user with username: testuser")
            ])
            self.assertEqual(mock_logger.error.call_count, 0)

            # Verify event returned unchanged
            self.assertEqual(result, self.valid_create_event)

    @mock_aws
    @patch('lambda_user_subscription.sns')
    @patch('lambda_user_subscription.subscriptions_table')
    def test_post_auth_success_email_changed(self, mock_table, mock_sns):
        """Test successful post-authentication flow with email change"""
        import lambda_user_subscription

        # Mock SNS response
        mock_sns.subscribe.return_value = {
            'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test-topic:new-subscription-id'
        }

        # Mock DynamoDB response with different email
        mock_table.get_item.return_value = {
            'Item': {
                'username': 'testuser',
                'email': 'old@example.com',
                'subscription_arn': 'arn:aws:sns:us-east-1:123456789012:test-topic:old-subscription-id'
            }
        }

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(self.valid_auth_event, None)

            # Verify old subscription was removed
            mock_sns.unsubscribe.assert_called_once_with(
                SubscriptionArn='arn:aws:sns:us-east-1:123456789012:test-topic:old-subscription-id'
            )

            # Verify new subscription was created
            mock_sns.subscribe.assert_called_once_with(
                TopicArn='arn:aws:sns:us-east-1:123456789012:test-topic',
                Protocol='email',
                Endpoint='test@example.com',
                ReturnSubscriptionArn=True,
                Attributes={
                    'FilterPolicy': json.dumps({"Email": ["test@example.com"]})
                }
            )

            # Verify DynamoDB was updated
            mock_table.put_item.assert_called_once_with(
                Item={
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'subscription_arn': 'arn:aws:sns:us-east-1:123456789012:test-topic:new-subscription-id'
                }
            )

            # Verify logging
            mock_logger.info.assert_has_calls([
                call("Unsubscribed old subscription: arn:aws:sns:us-east-1:123456789012:test-topic:old-subscription-id"),
                call('Created SNS subscription for user: {"SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:test-topic:new-subscription-id"}'),
                call("Stored subscription details for user with username: testuser")
            ])
            self.assertEqual(mock_logger.error.call_count, 0)

            # Verify event returned unchanged
            self.assertEqual(result, self.valid_auth_event)

    @mock_aws
    @patch('lambda_user_subscription.sns')
    @patch('lambda_user_subscription.subscriptions_table')
    def test_post_auth_success_email_unchanged(self, mock_table, mock_sns):
        """Test post-authentication flow with unchanged email"""
        import lambda_user_subscription

        # Mock DynamoDB response with same email
        mock_table.get_item.return_value = {
            'Item': {
                'username': 'testuser',
                'email': 'test@example.com',
                'subscription_arn': 'arn:aws:sns:us-east-1:123456789012:test-topic:old-subscription-id'
            }
        }

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(self.valid_auth_event, None)

            # Verify no SNS calls were made
            mock_sns.unsubscribe.assert_not_called()
            mock_sns.subscribe.assert_not_called()

            # Verify no DynamoDB updates
            mock_table.put_item.assert_not_called()

            # Verify logging
            mock_logger.info.assert_called_once_with(
                "No change in email for user: testuser, SNS subscription update not needed."
            )
            self.assertEqual(mock_logger.error.call_count, 0)

            # Verify event returned unchanged
            self.assertEqual(result, self.valid_auth_event)

    @mock_aws
    @patch('lambda_user_subscription.sns')
    @patch('lambda_user_subscription.subscriptions_table')
    def test_post_auth_no_subscription(self, mock_table, mock_sns):
        """Test post-authentication with no existing subscription"""
        import lambda_user_subscription

        # Mock DynamoDB response with no existing subscription
        mock_table.get_item.return_value = {}

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(self.valid_auth_event, None)

            # Verify no SNS calls were made
            mock_sns.unsubscribe.assert_not_called()
            mock_sns.subscribe.assert_not_called()

            # Verify no DynamoDB updates
            mock_table.put_item.assert_not_called()

            # Verify logging
            mock_logger.error.assert_called_once_with("No existing subscription found for user: testuser")

            # Verify event returned unchanged
            self.assertEqual(result, self.valid_auth_event)

    @mock_aws
    @patch('lambda_user_subscription.sns')
    @patch('lambda_user_subscription.subscriptions_table')
    def test_sns_subscription_error(self, mock_table, mock_sns):
        """Test handling of SNS subscription error"""
        import lambda_user_subscription

        # Mock SNS error
        mock_sns.subscribe.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'InvalidParameter', 'Message': 'Invalid parameter'}},
            'Subscribe'
        )

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(self.valid_create_event, None)

            # Verify SNS subscription was attempted
            mock_sns.subscribe.assert_called_once_with(
                TopicArn='arn:aws:sns:us-east-1:123456789012:test-topic',
                Protocol='email',
                Endpoint='test@example.com',
                ReturnSubscriptionArn=True,
                Attributes={
                    'FilterPolicy': json.dumps({"Email": ["test@example.com"]})
                }
            )

            # Verify no DynamoDB updates
            mock_table.put_item.assert_not_called()

            # Verify error logging
            mock_logger.error.assert_called_with(
                "Error during new user creation process: An error occurred (InvalidParameter) when calling the Subscribe operation: Invalid parameter"
            )

            # Verify event returned unchanged
            self.assertEqual(result, self.valid_create_event)

    @mock_aws
    @patch('lambda_user_subscription.sns')
    @patch('lambda_user_subscription.subscriptions_table')
    def test_dynamodb_error(self, mock_table, mock_sns):
        """Test handling of DynamoDB error"""
        import lambda_user_subscription

        # Mock SNS response
        mock_sns.subscribe.return_value = {
            'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id'
        }

        # Mock DynamoDB error
        mock_table.put_item.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}},
            'PutItem'
        )

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(self.valid_create_event, None)

            # Verify SNS subscription was created
            mock_sns.subscribe.assert_called_once()

            # Verify DynamoDB put_item was attempted
            mock_table.put_item.assert_called_once()

            # Verify error logging
            mock_logger.error.assert_called_with(
                "Error during new user creation process: An error occurred (ResourceNotFoundException) when calling the PutItem operation: Table not found"
            )

            # Verify event returned unchanged
            self.assertEqual(result, self.valid_create_event)

    def test_missing_trigger_source(self):
        """Test handling of missing triggerSource"""
        import lambda_user_subscription

        event = self.valid_create_event.copy()
        del event['triggerSource']

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(event, None)

            # Verify logging
            mock_logger.error.assert_called_with("Invalid event: Missing triggerSource")

            # Verify event returned unchanged
            self.assertEqual(result, event)

    def test_invalid_trigger_source(self):
        """Test handling of invalid triggerSource"""
        import lambda_user_subscription

        event = self.valid_create_event.copy()
        event['triggerSource'] = 'InvalidTrigger'

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(event, None)

            # Verify logging
            mock_logger.error.assert_called_with("Invalid event: Unexpected triggerSource InvalidTrigger")

            # Verify event returned unchanged
            self.assertEqual(result, event)

    def test_missing_username(self):
        """Test handling of missing userName"""
        import lambda_user_subscription

        event = self.valid_create_event.copy()
        del event['userName']

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(event, None)

            # Verify logging
            mock_logger.error.assert_called_with("Invalid event: Missing userName")

            # Verify event returned unchanged
            self.assertEqual(result, event)

    def test_missing_request(self):
        """Test handling of missing request"""
        import lambda_user_subscription

        event = self.valid_create_event.copy()
        del event['request']

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(event, None)

            # Verify logging
            mock_logger.error.assert_called_with("Invalid event: Missing request or userAttributes")

            # Verify event returned unchanged
            self.assertEqual(result, event)

    def test_missing_user_attributes(self):
        """Test handling of missing userAttributes"""
        import lambda_user_subscription

        event = self.valid_create_event.copy()
        del event['request']['userAttributes']

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(event, None)

            # Verify logging
            mock_logger.error.assert_called_with("Invalid event: Missing request or userAttributes")

            # Verify event returned unchanged
            self.assertEqual(result, event)

    def test_missing_email(self):
        """Test handling of missing email"""
        import lambda_user_subscription

        event = self.valid_create_event.copy()
        del event['request']['userAttributes']['email']

        with patch('lambda_user_subscription.logger') as mock_logger:
            result = lambda_user_subscription.lambda_handler(event, None)

            # Verify logging
            mock_logger.error.assert_called_with("Invalid event: Missing email in userAttributes")

            # Verify event returned unchanged
            self.assertEqual(result, event)

if __name__ == '__main__':
    unittest.main()
