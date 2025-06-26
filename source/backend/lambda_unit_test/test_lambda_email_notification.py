#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
import json
from unittest import mock
from unittest.mock import patch, call
import botocore
from test_common_utils import default_mock_os_environ

mock_os_environ = {
    **default_mock_os_environ,
    'application': 'cmf',
    'environment': 'unittest',
    'user_pool_id': 'us-east-1_testpool',
    'sns_topic_arn': 'arn:aws:sns:us-east-1:123456789012:test-topic',
    'AWS_DEFAULT_REGION': 'us-east-1'
}

TEST_EMAIL_BASE_SUBJECT = "cmf - unittest env"

@mock.patch.dict('os.environ', mock_os_environ)
class LambdaEmailNotificationTest(unittest.TestCase):
    """Test cases for lambda_email_notification.py"""

    def create_mock_cognito_response(self, users, next_token=None):
        """Helper to create mock Cognito response"""
        response = {
            'Users': [
                {
                    'Username': f'user{i}',
                    'Attributes': [{'Name': 'email', 'Value': email}]
                }
                for i, email in enumerate(users)
            ]
        }
        if next_token:
            response['NextToken'] = next_token
        return response

    def setUp(self):
        """Set up test fixtures"""
        # Mock Cognito response for groups
        self.mock_cognito_response = {
            'Users': [
                {
                    'Username': 'user1',
                    'Attributes': [{'Name': 'email', 'Value': 'group1@example.com'}]
                },
                {
                    'Username': 'user2',
                    'Attributes': [{'Name': 'email', 'Value': 'group2@example.com'}]
                }
            ]
        }

    def create_event(self, detail_type='TaskFailed', task_id='b7d8f25a-e9a0-4e6c-8e3d-123456789abc', pipeline_id='13'):
        """Create a test event"""
        return {
            'detail-type': detail_type,
            'detail': {
                'pipeline_id': pipeline_id,
                'task_id': task_id,
                'type': detail_type,
                'task_name': 'Test Task',
                'content': 'Test error message',
                'timestamp': '2024-01-01T00:00:00Z'
            },
            'source': 'cmf.pipeline'
        }

    def create_pipeline_data(self, pipeline_id='13', task_id='b7d8f25a-e9a0-4e6c-8e3d-123456789abc', task_name='Test Task',
                           enable_notifications=True, task_recipients=None, task_email_body=None,
                           default_recipients=None, default_groups=None, task_groups=None, task_email_enabled=False, task_override_defaults=False):
        """Create pipeline test data"""
        pipeline_data = {
            'Item': {
                'pipeline_id': pipeline_id,
                'current_task_id': task_id,
                'pipeline_name': 'SEOUL',
                'pipeline_description': 'Test Description',
                'pipeline_status': 'Complete',
                'pipeline_template_id': '3',
                'pipeline_enable_email_notifications': enable_notifications,
                'pipeline_default_email_groups': [],
                'pipeline_default_email_recipients': [],
                'task_level_email_settings': [],
                'task_arguments': {
                    'mi_id': 'i-0daaf798e18d69849'
                },
                '_history': {
                    'createdBy': {
                        'email': 'serviceaccount@yourdomain.com',
                        'userRef': '44c834d8-6081-70c3-3d60-64418d774f4d'
                    },
                    'createdTimestamp': '2025-03-15T21:42:16.869013+00:00',
                    'lastModifiedTimestamp': '2025-03-15T21:42:21.009398+00:00'
                }
            }
        }

        # Add default recipients if provided
        if default_recipients:
            pipeline_data['Item']['pipeline_default_email_recipients'] = [
                {'email': email} for email in default_recipients
            ]

        # Add default groups if provided
        if default_groups:
            pipeline_data['Item']['pipeline_default_email_groups'] = [
                {'group_name': group} for group in default_groups
            ]

        # Add task level config if provided
        
        task_config = {
            'task_id': f'SEOUL:{task_name}',
            'email_groups': [],
            'email_users': [],
            'enabled': task_email_enabled,
            'override_defaults': task_override_defaults
        }

        if task_recipients:
            task_config['email_users'] = [
                {'email': email} for email in task_recipients
            ]

        if task_groups:
            task_config['email_groups'] = [
                {'group_name': group} for group in task_groups
            ]

        if task_email_body:
            task_config['email_body'] = task_email_body

        pipeline_data['Item']['task_level_email_settings'] = [task_config]

        return pipeline_data

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_task_level_config_complete(self, mock_table, mock_sns, mock_cognito):
        """Test when task has both recipients and custom email body"""
        import lambda_email_notification

        # Mock Cognito response for task group
        mock_cognito.list_users_in_group.return_value = self.mock_cognito_response

        # Mock pipeline data with task level config
        mock_table.get_item.return_value = self.create_pipeline_data(
            task_recipients=['task@example.com'],
            task_groups=['readonly'],
            task_email_body='HELLO WORLD!',
            default_recipients=['default@example.com'],
            task_override_defaults=True,
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(
                json.loads(response['body'])['message'],
                'Email Notification sent to task level recipients'
            )

            # Verify get_item call
            mock_table.get_item.assert_called_once_with(
                Key={'pipeline_id': '13'}
            )

            # Verify Cognito call for group members
            mock_cognito.list_users_in_group.assert_called_once_with(
                UserPoolId='us-east-1_testpool',
                GroupName='readonly',
                Limit=60
            )

        actual_call = mock_sns.publish.call_args

        # Extract the actual recipients from the MessageAttributes
        actual_recipients = json.loads(
            actual_call.kwargs['MessageAttributes']['Email']['StringValue']
        )

        # Verify each part of the call separately
        self.assertEqual(actual_call.kwargs['TopicArn'], 'arn:aws:sns:us-east-1:123456789012:test-topic')
        self.assertIn('HELLO WORLD!', actual_call.kwargs['Message']) # Verify custom message was used with task recipients
        self.assertEqual(
            actual_call.kwargs['Subject'],
            f'Task Execution Failed - {TEST_EMAIL_BASE_SUBJECT}'
        )
        self.assertEqual(actual_call.kwargs['MessageAttributes']['Email']['DataType'], 'String.Array')

        # Compare sorted recipients
        expected_recipients = ['group1@example.com', 'group2@example.com', 'task@example.com']
        self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

        # Verify logging
        mock_logger.info.assert_called_with('Successfully published notification: test-message-id')

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_task_level_recipients_only(self, mock_table, mock_sns, mock_cognito):
        """Test when task has only recipients (no email body)"""
        import lambda_email_notification

        # Define test cases
        test_cases = [
            {
                'detail_type': 'TaskFailed',
                'expected_subject': f'Task Execution Failed - {TEST_EMAIL_BASE_SUBJECT}',
                'expected_message_contains': ['Task Execution Failed', 'Test Task', 'Pipeline Name: SEOUL']
            },
            {
                'detail_type': 'TaskManualApprovalNeeded',
                'expected_subject': f'Manual Approval Needed - {TEST_EMAIL_BASE_SUBJECT}',
                'expected_message_contains': ['Manual Approval Required', 'Test Task', 'Pipeline Name: SEOUL']
            },
            {
                'detail_type': 'EmailAutomationTaskType',
                'expected_subject': f'Email Automation - {TEST_EMAIL_BASE_SUBJECT}',
                'expected_message_contains': ['Email Automation', 'Test Task', 'Pipeline Name: SEOUL']
            }
        ]

        for test_case in test_cases:
            with self.subTest(detail_type=test_case['detail_type']):
                # Mock Cognito response for task group
                mock_cognito.list_users_in_group.return_value = self.mock_cognito_response

                # Mock pipeline data with only task recipients
                mock_table.get_item.return_value = self.create_pipeline_data(
                    task_recipients=['task@example.com'],
                    task_groups=['readonly'],
                    default_recipients=['default@example.com'],
                    task_email_enabled=True,
                    task_override_defaults=True
                )

                # Mock SNS response
                mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
                mock_sns.publish.reset_mock()  # Reset mock for each test case

                # Create event with current detail_type
                event = self.create_event(detail_type=test_case['detail_type'])

                with patch('lambda_email_notification.logger') as mock_logger:
                    response = lambda_email_notification.lambda_handler(event, None)

                    self.assertEqual(response['statusCode'], 200)
                    self.assertEqual(
                        json.loads(response['body'])['message'],
                        'Email Notification sent to task level recipients'
                    )

                    # Verify Cognito call for group members
                    mock_cognito.list_users_in_group.assert_called_with(
                        UserPoolId='us-east-1_testpool',
                        GroupName='readonly',
                        Limit=60
                    )

                    # Verify default message was used with all recipients
                    expected_recipients = ['group1@example.com', 'group2@example.com', 'task@example.com']
                    actual_call = mock_sns.publish.call_args

                    # Extract the actual recipients from the MessageAttributes
                    actual_recipients = json.loads(
                        actual_call.kwargs['MessageAttributes']['Email']['StringValue']
                    )

                    # Verify each part of the call separately
                    self.assertEqual(actual_call.kwargs['TopicArn'], 'arn:aws:sns:us-east-1:123456789012:test-topic')

                    self.assertEqual(
                        actual_call.kwargs['Subject'],
                        test_case['expected_subject']
                    )
                    self.assertEqual(actual_call.kwargs['MessageAttributes']['Email']['DataType'], 'String.Array')

                    # Compare sorted recipients
                    expected_recipients = ['group1@example.com', 'group2@example.com', 'task@example.com']
                    self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

                    # Verify message content
                    for expected_text in test_case['expected_message_contains']:
                        self.assertIn(expected_text, actual_call.kwargs['Message'])

                    # Verify successful message was logged
                    mock_logger.info.assert_called_with('Successfully published notification: test-message-id')

                    # Reset mocks for next test case
                    mock_logger.reset_mock()
                    mock_cognito.reset_mock()
                    mock_table.reset_mock()
                    mock_sns.reset_mock()

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_default_recipients_only(self, mock_table, mock_sns, mock_cognito):
        """Test when no task level config exists"""
        import lambda_email_notification

        # Mock Cognito response for default group
        mock_cognito.list_users_in_group.return_value = self.mock_cognito_response

        # Mock pipeline data with only default recipients
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_recipients=['default@example.com'],
            default_groups=['readonly'],
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(
                json.loads(response['body']),
                {'message': 'Email Notification sent to default recipients'}
            )

            # Verify Cognito call for group members
            mock_cognito.list_users_in_group.assert_called_once_with(
                UserPoolId='us-east-1_testpool',
                GroupName='readonly',
                Limit=60
            )

            actual_call = mock_sns.publish.call_args

            # Extract the actual recipients from the MessageAttributes
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )

            # Verify each part of the call separately
            self.assertEqual(actual_call.kwargs['TopicArn'], 'arn:aws:sns:us-east-1:123456789012:test-topic')
            self.assertEqual(
                actual_call.kwargs['Subject'],
                f'Task Execution Failed - {TEST_EMAIL_BASE_SUBJECT}'
            )
            self.assertEqual(actual_call.kwargs['MessageAttributes']['Email']['DataType'], 'String.Array')

            # Compare sorted recipients
            expected_recipients = ['group1@example.com', 'group2@example.com', 'default@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

            # Verify default message was used with task recipients
            self.assertIn('Task Execution Failed', actual_call.kwargs['Message'])
            self.assertIn('Test error message', actual_call.kwargs['Message'])
            self.assertIn('Test Task', actual_call.kwargs['Message'])
            self.assertIn('Pipeline Name: SEOUL', actual_call.kwargs['Message'])

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_notifications_disabled(self, mock_table, mock_sns, mock_cognito):
        """Test when notifications are disabled"""
        import lambda_email_notification

        # Mock pipeline data with notifications disabled
        mock_table.get_item.return_value = self.create_pipeline_data(
            enable_notifications=False
        )

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(
                json.loads(response['body'])['message'],
                'Email notifications are disabled for pipeline with pipeline id 13'
            )

            # Verify no Cognito or SNS calls were made
            mock_cognito.list_users_in_group.assert_not_called()
            mock_sns.publish.assert_not_called()

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_pipeline_not_found(self, mock_table, mock_sns, mock_cognito):
        """Test when pipeline is not found"""
        import lambda_email_notification

        # Mock pipeline data not found
        mock_table.get_item.return_value = {}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 500)
            self.assertEqual(
                json.loads(response['body'])['error'],
                'Pipeline with pipeline id 13 not found'
            )

            # Verify no Cognito or SNS calls were made
            mock_cognito.list_users_in_group.assert_not_called()
            mock_sns.publish.assert_not_called()

    def test_invalid_event_payload(self):
        """Test with invalid event payload"""
        import lambda_email_notification

        invalid_event = {
            'detail': {
                'pipeline_id': '13',
                'task_id': 'test-task'
            }
        }

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(invalid_event, None)

            self.assertEqual(response['statusCode'], 400)
            self.assertEqual(
                json.loads(response['body'])['error'],
                'Invalid event payload'
            )

            # Verify error was logged
            mock_logger.error.assert_called_with("Missing required event fields. Required: ['detail-type', 'detail', 'source']")

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_sns_publish_error(self, mock_table, mock_sns, mock_cognito):
        """Test handling of SNS publish error"""
        import lambda_email_notification

        # Mock Cognito response for default group
        mock_cognito.list_users_in_group.return_value = self.mock_cognito_response

        # Mock pipeline data
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_recipients=['default@example.com'],
            default_groups=['readonly'],
            task_email_enabled=True
        )

        # Mock SNS error
        mock_sns.publish.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'InvalidParameter', 'Message': 'Invalid parameter'}},
            'Publish'
        )

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 500)
            self.assertEqual(
                json.loads(response['body'])['error'],
                'Failed to send email notification to any recipients'
            )

            # Verify error was logged
            mock_logger.error.assert_called_with(
                'Error publishing notification: An error occurred (InvalidParameter) when calling the Publish operation: Invalid parameter'
            )

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_single_group_no_pagination(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler with single Cognito group and no pagination"""
        import lambda_email_notification

        # Mock Cognito response with no pagination
        mock_cognito.list_users_in_group.return_value = {
            'Users': [
                {
                    'Username': 'user1',
                    'Attributes': [{'Name': 'email', 'Value': 'user1@example.com'}]
                },
                {
                    'Username': 'user2', 
                    'Attributes': [{'Name': 'email', 'Value': 'user2@example.com'}]
                }
            ]
        }

        # Mock pipeline data with single group
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_groups=['test-group'],
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(
                json.loads(response['body'])['message'],
                'Email Notification sent to default recipients'
            )

            # Verify Cognito call
            mock_cognito.list_users_in_group.assert_called_once_with(
                UserPoolId='us-east-1_testpool',
                GroupName='test-group',
                Limit=60
            )

            # Verify SNS was called with group emails
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )
            expected_recipients = ['user1@example.com', 'user2@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_multiple_groups(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler with multiple Cognito groups"""
        import lambda_email_notification

        # Mock different responses for different groups
        def mock_list_users_side_effect(**kwargs):
            group_name = kwargs['GroupName']
            if group_name == 'group1':
                return {
                    'Users': [
                        {
                            'Username': 'user1',
                            'Attributes': [{'Name': 'email', 'Value': 'user1@example.com'}]
                        }
                    ]
                }
            elif group_name == 'group2':
                return {
                    'Users': [
                        {
                            'Username': 'user2',
                            'Attributes': [{'Name': 'email', 'Value': 'user2@example.com'}]
                        },
                        {
                            'Username': 'user3',
                            'Attributes': [{'Name': 'email', 'Value': 'user3@example.com'}]
                        }
                    ]
                }
            return {'Users': []}

        mock_cognito.list_users_in_group.side_effect = mock_list_users_side_effect

        # Mock pipeline data with multiple groups
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_groups=['group1', 'group2'],
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)

            # Verify Cognito calls for both groups
            self.assertEqual(mock_cognito.list_users_in_group.call_count, 2)
            mock_cognito.list_users_in_group.assert_any_call(
                UserPoolId='us-east-1_testpool',
                GroupName='group1',
                Limit=60
            )
            mock_cognito.list_users_in_group.assert_any_call(
                UserPoolId='us-east-1_testpool',
                GroupName='group2',
                Limit=60
            )

            # Verify SNS was called with all group emails
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )
            expected_recipients = ['user1@example.com', 'user2@example.com', 'user3@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_with_extensive_pagination(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler with Cognito group pagination across multiple pages"""
        import lambda_email_notification

        # Create 3 pages of results with 60, 60, and 30 users respectively
        page1_users = [f'user{i}@example.com' for i in range(1, 61)]  # 60 users
        page2_users = [f'user{i}@example.com' for i in range(61, 121)]  # 60 more users
        page3_users = [f'user{i}@example.com' for i in range(121, 151)]  # 30 more users

        # Set up mock responses with pagination
        mock_cognito.list_users_in_group.side_effect = [
            self.create_mock_cognito_response(page1_users, 'token1'),
            self.create_mock_cognito_response(page2_users, 'token2'),
            self.create_mock_cognito_response(page3_users)
        ]

        # Mock pipeline data with task level config
        mock_table.get_item.return_value = self.create_pipeline_data(
            task_recipients=['direct@example.com'],
            task_groups=['large-group'],
            task_email_enabled=True,
            task_override_defaults=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(
                json.loads(response['body'])['message'],
                'Email Notification sent to task level recipients'
            )

            # Verify Cognito calls for paginated results
            mock_cognito.list_users_in_group.assert_has_calls([
                call(UserPoolId='us-east-1_testpool', GroupName='large-group', Limit=60),
                call(UserPoolId='us-east-1_testpool', GroupName='large-group', Limit=60, NextToken='token1'),
                call(UserPoolId='us-east-1_testpool', GroupName='large-group', Limit=60, NextToken='token2')
            ])

            # Verify SNS publish was called with all recipients
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )

            # Build expected recipients list
            expected_recipients = ['direct@example.com']  # Direct recipient
            expected_recipients.extend(page1_users)  # Page 1 group members
            expected_recipients.extend(page2_users)  # Page 2 group members
            expected_recipients.extend(page3_users)  # Page 3 group members

            # Verify all recipients were included
            self.assertEqual(len(actual_recipients), 151)  # 1 direct + 150 from groups
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_users_without_email(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler with Cognito users missing email attributes"""
        import lambda_email_notification

        # Mock response with users missing email
        mock_cognito.list_users_in_group.return_value = {
            'Users': [
                {
                    'Username': 'user1',
                    'Attributes': [{'Name': 'email', 'Value': 'user1@example.com'}]
                },
                {
                    'Username': 'user2',
                    'Attributes': [{'Name': 'phone_number', 'Value': '+1234567890'}]  # No email
                },
                {
                    'Username': 'user3',
                    'Attributes': []  # No attributes at all
                },
                {
                    'Username': 'user4',
                    'Attributes': [{'Name': 'email', 'Value': 'user4@example.com'}]
                }
            ]
        }

        # Mock pipeline data with group
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_groups=['test-group'],
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)

            # Verify warnings were logged for users without email
            warning_calls = [call for call in mock_logger.warning.call_args_list]
            self.assertEqual(len(warning_calls), 2)
            self.assertIn("No email found for user 'user2'", str(warning_calls[0]))
            self.assertIn("No email found for user 'user3'", str(warning_calls[1]))

            # Verify SNS was called with only valid emails
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )
            expected_recipients = ['user1@example.com', 'user4@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_empty_group(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler with empty Cognito group"""
        import lambda_email_notification

        # Mock empty response
        mock_cognito.list_users_in_group.return_value = {
            'Users': []
        }

        # Mock pipeline data with empty group and direct recipients
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_recipients=['direct@example.com'],
            default_groups=['empty-group'],
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)

            # Verify Cognito call was made
            mock_cognito.list_users_in_group.assert_called_once_with(
                UserPoolId='us-east-1_testpool',
                GroupName='empty-group',
                Limit=60
            )

            # Verify SNS was called with only direct recipients
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )
            expected_recipients = ['direct@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_duplicate_emails_across_groups(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler with duplicate emails across multiple Cognito groups"""
        import lambda_email_notification

        # Mock responses where same user appears in multiple groups
        def mock_list_users_side_effect(**kwargs):
            return {
                'Users': [
                    {
                        'Username': 'shared_user',
                        'Attributes': [{'Name': 'email', 'Value': 'shared@example.com'}]
                    },
                    {
                        'Username': f'user_{kwargs["GroupName"]}',
                        'Attributes': [{'Name': 'email', 'Value': f'{kwargs["GroupName"]}@example.com'}]
                    }
                ]
            }

        mock_cognito.list_users_in_group.side_effect = mock_list_users_side_effect

        # Mock pipeline data with multiple groups
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_groups=['group1', 'group2'],
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)

            # Verify SNS was called with deduplicated emails
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )
            expected_recipients = ['shared@example.com', 'group1@example.com', 'group2@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_client_error_partial_failure(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler when some Cognito groups fail with ClientError"""
        import lambda_email_notification

        # Mock ClientError for first group, success for second
        def mock_list_users_side_effect(**kwargs):
            group_name = kwargs['GroupName']
            if group_name == 'error-group':
                raise botocore.exceptions.ClientError(
                    {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Group not found'}},
                    'ListUsersInGroup'
                )
            else:
                return {
                    'Users': [
                        {
                            'Username': 'user1',
                            'Attributes': [{'Name': 'email', 'Value': 'user1@example.com'}]
                        }
                    ]
                }

        mock_cognito.list_users_in_group.side_effect = mock_list_users_side_effect

        # Mock pipeline data with both error and valid groups
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_groups=['error-group', 'valid-group'],
            task_email_enabled=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Error retrieving users in group 'error-group'", error_call)

            # Verify SNS was called with emails from valid group only
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )
            expected_recipients = ['user1@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_all_groups_error(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler when all Cognito groups fail with ClientError"""
        import lambda_email_notification

        # Mock ClientError for all groups
        mock_cognito.list_users_in_group.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'ListUsersInGroup'
        )

        # Mock pipeline data with groups only (no direct recipients)
        mock_table.get_item.return_value = self.create_pipeline_data(
            default_groups=['group1', 'group2'],
            task_email_enabled=True
        )

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            # Should fail since no recipients could be retrieved
            self.assertEqual(response['statusCode'], 500)
            self.assertEqual(
                json.loads(response['body'])['error'],
                'Failed to send email notification to any recipients'
            )

            # Verify errors were logged for both groups
            self.assertEqual(mock_logger.error.call_count, 2)

            # Verify SNS was not called
            mock_sns.publish.assert_not_called()

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_cognito_group_emails_mixed_task_and_default_groups(self, mock_table, mock_sns, mock_cognito):
        """Test lambda_handler with both task-level and default-level Cognito groups"""
        import lambda_email_notification

        # Mock different responses for task vs default groups
        def mock_list_users_side_effect(**kwargs):
            group_name = kwargs['GroupName']
            if group_name == 'task-group':
                return {
                    'Users': [
                        {
                            'Username': 'task_user',
                            'Attributes': [{'Name': 'email', 'Value': 'task@example.com'}]
                        }
                    ]
                }
            elif group_name == 'default-group':
                return {
                    'Users': [
                        {
                            'Username': 'default_user',
                            'Attributes': [{'Name': 'email', 'Value': 'default@example.com'}]
                        }
                    ]
                }
            return {'Users': []}

        mock_cognito.list_users_in_group.side_effect = mock_list_users_side_effect

        # Mock pipeline data with both task and default groups
        mock_table.get_item.return_value = self.create_pipeline_data(
            task_groups=['task-group'],
            default_groups=['default-group'],
            task_email_enabled=True,
            task_override_defaults=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(
                json.loads(response['body'])['message'],
                'Email Notification sent to task level recipients'
            )

            # Verify both groups were called (lambda processes defaults first, then task-level)
            # but task-level recipients are used for sending
            self.assertEqual(mock_cognito.list_users_in_group.call_count, 2)
            mock_cognito.list_users_in_group.assert_any_call(
                UserPoolId='us-east-1_testpool',
                GroupName='default-group',
                Limit=60
            )
            mock_cognito.list_users_in_group.assert_any_call(
                UserPoolId='us-east-1_testpool',
                GroupName='task-group',
                Limit=60
            )

            # Verify SNS was called with task group emails only (task overrides defaults)
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )
            expected_recipients = ['task@example.com']
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

    @patch('lambda_email_notification.cognito')
    @patch('lambda_email_notification.sns')
    @patch('lambda_email_notification.pipeline_table')
    def test_paginated_group_members(self, mock_table, mock_sns, mock_cognito):
        """Test handling of paginated responses from list_users_in_group"""
        import lambda_email_notification

        # Create paginated responses
        page1_users = [f'user{i}@example.com' for i in range(1, 61)]  # 60 users
        page2_users = [f'user{i}@example.com' for i in range(61, 121)]  # 60 more users
        page3_users = [f'user{i}@example.com' for i in range(121, 151)]  # 30 more users

        # Set up mock responses with pagination
        mock_cognito.list_users_in_group.side_effect = [
            self.create_mock_cognito_response(page1_users, 'token1'),
            self.create_mock_cognito_response(page2_users, 'token2'),
            self.create_mock_cognito_response(page3_users)
        ]

        # Mock pipeline data with task level config
        mock_table.get_item.return_value = self.create_pipeline_data(
            task_recipients=['direct@example.com'],
            task_groups=['readonly'],
            task_email_body='Test notification',
            task_email_enabled=True,
            task_override_defaults=True
        )

        # Mock SNS response
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

        event = self.create_event()

        with patch('lambda_email_notification.logger') as mock_logger:
            response = lambda_email_notification.lambda_handler(event, None)

            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(
                json.loads(response['body'])['message'],
                'Email Notification sent to task level recipients'
            )

            # Verify Cognito calls for paginated results
            mock_cognito.list_users_in_group.assert_has_calls([
                call(UserPoolId='us-east-1_testpool', GroupName='readonly', Limit=60),
                call(UserPoolId='us-east-1_testpool', GroupName='readonly', Limit=60, NextToken='token1'),
                call(UserPoolId='us-east-1_testpool', GroupName='readonly', Limit=60, NextToken='token2')
            ])

            # Verify SNS publish was called with all recipients
            actual_call = mock_sns.publish.call_args
            actual_recipients = json.loads(
                actual_call.kwargs['MessageAttributes']['Email']['StringValue']
            )

            # Build expected recipients list
            expected_recipients = ['direct@example.com']  # Direct recipient
            expected_recipients.extend(page1_users)  # Page 1 group members
            expected_recipients.extend(page2_users)  # Page 2 group members
            expected_recipients.extend(page3_users)  # Page 3 group members

            # Verify all recipients were included
            self.assertEqual(len(actual_recipients), 151)  # 1 direct + 150 from groups
            self.assertEqual(sorted(actual_recipients), sorted(expected_recipients))

            # Verify other SNS parameters
            self.assertEqual(actual_call.kwargs['TopicArn'], 'arn:aws:sns:us-east-1:123456789012:test-topic')
            self.assertIn('Test notification', actual_call.kwargs['Message'])
            self.assertEqual(actual_call.kwargs['Subject'], f'Task Execution Failed - {TEST_EMAIL_BASE_SUBJECT}')

            # Verify success was logged
            mock_logger.info.assert_called_with('Successfully published notification: test-message-id')

if __name__ == '__main__':
    unittest.main()
