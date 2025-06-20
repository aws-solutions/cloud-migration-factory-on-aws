#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch
import boto3
from moto import mock_aws
import os
from test_common_utils import create_and_populate_tasks, create_and_populate_ssm_scripts, create_and_populate_pipelines
from unittest import TestCase, mock
import datetime

@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region':'us-east-1', 'application': 'cmf', 'environment': 'unittest', 'SCRIPTS_TABLE_NAME': '{}-{}-'.format('cmf', 'unittest') + 'scripts', 'PIPELINES_TABLE_NAME': '{}-{}-'.format('cmf', 'unittest') + 'pipelines', 'TASK_EXECUTIONS_TABLE_NAME': '{}-{}-'.format('cmf', 'unittest') + 'task_executions', 'EVENT_BUS_NAME': 'eventBusName'})
@mock_aws
class LambdaPipelineTaskOrchestratorTest(TestCase):
    @mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region':'us-east-1', 'application': 'cmf', 'environment': 'unittest', 'EVENT_BUS_NAME': 'eventBusName'})
    @mock_aws
    def setUp(self) -> None:
        self.task_executions_table_name = '{}-{}-'.format('cmf', 'unittest') + 'task_executions'
        self.scripts_table_name = '{}-{}-'.format('cmf', 'unittest') + 'scripts'
        self.pipeline_table_name = '{}-{}-'.format('cmf', 'unittest') + 'pipelines'
        boto3.setup_default_session()

        self.ddb_client = boto3.client('dynamodb')
        create_and_populate_tasks(self.ddb_client, self.task_executions_table_name)
        create_and_populate_ssm_scripts(self.ddb_client, self.scripts_table_name)
        create_and_populate_pipelines(self.ddb_client, self.pipeline_table_name)

    def pipeline_event_lambda_task(self):
        event = {
            'Records' : [
                {
                    'dynamodb': {
                        'OldImage': {
                            'pipeline_id': {'S': '1'},
                            'pipeline_status': {'S': 'Provisioning'},
                            'task_execution_id': {
                                'S': "1"
                            }, # see sample data: this task is of type Automated and lambda suffix not starting with SSM, making it a lambda automation
                        },
                        'NewImage': {
                            'pipeline_id': {'S': '1'},
                            'pipeline_status': {'S': 'Not Started'},
                            'task_execution_id': {
                                'S': "1"
                            },
                        }
                    },
                    'eventSourceARN': '-pipelines'
                 }
            ],
        }
        return event
    
    def pipeline_event_manual_task(self):
        event = {
            'Records' : [
                {
                    'dynamodb': {
                        'OldImage': {
                            'pipeline_id': {'S': '7'},
                            'pipeline_status': {'S': 'Provisioning'},
                            'task_execution_id': {
                                'S': "9"
                            }, # see sample data: this task is of type Manual
                        },
                        'NewImage': {
                            'pipeline_id': {'S': '7'},
                            'pipeline_status': {'S': 'Not Started'},
                            'task_execution_id': {
                                'S': "9"
                            },
                        }
                    },
                    'eventSourceARN': '-pipelines'
                 }
            ],
        }
        return event
    
    def pipeline_event_email_task(self):
        event = {
            'Records' : [
                {
                    'dynamodb': {
                        'OldImage': {
                            'pipeline_id': {'S': '11'},
                            'pipeline_status': {'S': 'Provisioning'},
                            'task_execution_id': {
                                'S': "10"
                            }, # see sample data: this task is of type Manual
                        },
                        'NewImage': {
                            'pipeline_id': {'S': '11'},
                            'pipeline_status': {'S': 'Not Started'},
                            'task_execution_id': {
                                'S': "10"
                            },
                        }
                    },
                    'eventSourceARN': '-pipelines'
                 }
            ],
        }
        return event

    def pipeline_event_provisioned(self):
        event = {
            'Records' : [
                {
                    'dynamodb': {
                        'OldImage': {
                            'pipeline_id': {'S': '1'},
                            'pipeline_status': {'S': 'Provisioning'}
                        },
                        'NewImage': {
                            'pipeline_id': {'S': '1'},
                            'pipeline_status': {'S': 'Not Started'}
                        }
                    },
                    'eventSourceARN': '-pipelines'
                 }
            ],
        }
        return event

    def task_executions_event_complete(self, pipeline_id, task_execution_id):
        import cmf_pipeline # Import the enum from your lambda layer
        event = {
            'Records' : [
                {
                    'dynamodb': {
                        'OldImage': {
                            'pipeline_id': {'S': pipeline_id},
                            'task_execution_id': {
                                'S': task_execution_id
                            },
                            'task_execution_status': {
                                'S': 'In Progress'
                            }
                        },
                        'NewImage': {
                            'pipeline_id': {'S': pipeline_id},
                            'task_execution_id': {
                                'S': task_execution_id
                            },
                            'task_execution_status': {
                                'S': 'Complete'
                            }
                        }
                    },
                    'eventSourceARN': '-task_executions'
                 }
            ],
        }
        return event

    
    def task_executions_event(self, pipeline_id, task_execution_id, previous_status, current_status):
        event = {
            'Records': [
                {
                    'dynamodb': {
                        'OldImage': {
                            'pipeline_id': {'S': f'{pipeline_id}'},
                            'task_execution_id': {'S': f'{task_execution_id}'},
                            'task_execution_status': {'S': previous_status},
                            'task_successors': {'L': [{'S': '6'}]},
                            'task_execution_inputs': {'M': {'mi_id': {'S': 'testmi'}}},
                            'task_version': {'S': '1'},
                            'task_id': {'S': '11111111-1111-1111-1111-111111112'},
                            '_history': {'M': {
                                'lastModifiedTimestamp': {'S': 'test'},
                                'lastModifiedBy': {'S': 'test'}
                            }}
                        },
                        'NewImage': {
                            'pipeline_id': {'S': f'{pipeline_id}'},
                            'task_execution_id': {'S': f'{task_execution_id}'},
                            'task_execution_status': {'S': current_status},
                            'task_successors': {'L': [{'S': '6'}]},
                            'task_execution_inputs': {'M': {'mi_id': {'S': 'testmi'}}},
                            'task_version': {'S': '1'},
                            'task_id': {'S': '11111111-1111-1111-1111-111111112'},
                            '_history': {'M': {
                                'lastModifiedTimestamp': {'S': 'test'},
                                'lastModifiedBy': {'S': 'test'}
                            }}
                        }
                    },
                    'eventSourceARN': '-task_executions'
                }
            ]
        }
        return event

    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_pipeline_provisioned(self, mock_lambda_client):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.pipeline_event_provisioned(), None)

        item = self.ddb_client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': "1" }}
        )['Item']
        self.assertEqual(cmf_pipeline.TaskExecutionStatus.IN_PROGRESS.value, item['task_execution_status']['S'])

    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_completed_task(self, mock_lambda_client):
        import cmf_pipeline # Import the enum from your lambda layer
        import lambda_task_orchestrator

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.task_executions_event_complete(2, 2), None)

        item = self.ddb_client.get_item(
            TableName=self.pipeline_table_name,
            Key={'pipeline_id': { 'S': "2" }}
        )['Item']
        self.assertEqual(cmf_pipeline.TaskExecutionStatus.IN_PROGRESS.value, item['pipeline_status']['S'])

    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_completed_task_with_successors(self, mock_lambda_client):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.task_executions_event_complete(3, 3), None)

        item = self.ddb_client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': "3" }}
        )['Item']
        self.assertEqual(cmf_pipeline.TaskExecutionStatus.COMPLETE.value, item['task_execution_status']['S'])
        
    
    @patch('lambda_task_orchestrator.lambda_client')
    @patch('lambda_task_orchestrator.update_task_execution_status')
    def test_lambda_handler_abandon_not_started_task_with_successors(self, mock_update_status, mock_lambda_client):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.task_executions_event(3, 5, cmf_pipeline.TaskExecutionStatus.NOT_STARTED.value, cmf_pipeline.TaskExecutionStatus.ABANDONED.value), None)

        item = self.ddb_client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': "5" }}
        )['Item']
        self.assertEqual(cmf_pipeline.TaskExecutionStatus.ABANDONED.value, item['task_execution_status']['S'])
        #Assert the function was called with expected values
        self.assertEqual(mock_update_status.call_count, 2)
        actual_calls = mock_update_status.call_args_list
        for call_args in actual_calls:
            task_id, status = call_args[0]  # get arguments from the call
            # Verify task_id is one of expected values
            self.assertIn(task_id, ['6','7'])
            #Verify successor with non-abandoned task is not included 
            self.assertNotIn(task_id, ['8'])
            # Verify successor status is ABANDONED
            self.assertEqual(status.value, cmf_pipeline.TaskExecutionStatus.ABANDONED.value)
            
    @patch('lambda_task_orchestrator.lambda_client')
    @patch('lambda_task_orchestrator.update_task_execution_status')
    def test_lambda_handler_abandon_pending_approval_task_with_successors(self, mock_update_status, mock_lambda_client):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.task_executions_event(3, 5, cmf_pipeline.TaskExecutionStatus.PENDING_APPROVAL.value, cmf_pipeline.TaskExecutionStatus.ABANDONED.value), None)

        item = self.ddb_client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': "5" }}
        )['Item']
        self.assertEqual(cmf_pipeline.TaskExecutionStatus.ABANDONED.value, item['task_execution_status']['S'])
        #Assert the function was called with expected values
        self.assertEqual(mock_update_status.call_count, 2)
        actual_calls = mock_update_status.call_args_list
        for call_args in actual_calls:
            task_id, status = call_args[0]  # get arguments from the call
            # Verify task_id is one of expected values
            self.assertIn(task_id, ['6','7'])
            #Verify successor with non-abandoned task is not included 
            self.assertNotIn(task_id, ['8'])
            # Verify successor status is ABANDONED
            self.assertEqual(status.value, cmf_pipeline.TaskExecutionStatus.ABANDONED.value)
    
    
    @patch('lambda_task_orchestrator.lambda_client')
    @patch('lambda_task_orchestrator.update_task_execution_status')
    def test_lambda_handler_abandon_when_previous_status_is_invalid(self, mock_update_status, mock_lambda_client):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }
        invalid_status = [cmf_pipeline.TaskExecutionStatus.COMPLETE.value, cmf_pipeline.TaskExecutionStatus.FAILED.value, cmf_pipeline.TaskExecutionStatus.IN_PROGRESS.value, cmf_pipeline.TaskExecutionStatus.RETRY.value, cmf_pipeline.TaskExecutionStatus.SKIPPED.value,]
        
        for status in invalid_status:
            lambda_task_orchestrator.lambda_handler(self.task_executions_event(3, 5, status, cmf_pipeline.TaskExecutionStatus.ABANDONED.value), None)
            #Assert the function was called with expected values
            self.assertEqual(mock_update_status.call_count, 0)

    @mock.patch('lambda_task_orchestrator.eventsClient.put_events')
    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_ssm_task_failure(self, mock_lambda_client, mock_put_events):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        # Mock failed response from EventBridge
        mock_put_events.return_value = {
            'FailedEntryCount': 0,
            'Entries': [{'EventId': 'test-event-id'}]
        }

        lambda_task_orchestrator.lambda_handler(self.task_executions_event(11, 21, cmf_pipeline.TaskExecutionStatus.IN_PROGRESS.value, cmf_pipeline.TaskExecutionStatus.FAILED.value), None)

        # Verify the event was published with correct parameters
        mock_put_events.assert_called_once()

    @mock.patch('lambda_task_orchestrator.eventsClient.put_events')
    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_manual_task(self, mock_lambda_client, mock_put_events):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 500
        }

        # Mock failed response from EventBridge
        mock_put_events.return_value = {
            'FailedEntryCount': 0,
            'Entries': [{'EventId': 'test-event-id'}]
        }

        lambda_task_orchestrator.lambda_handler(self.pipeline_event_manual_task(), None)

        # Verify the event was published with correct parameters
        mock_put_events.assert_called_once_with(
            Entries=[{
                'Source': 'cmf-unittest-task-orchestrator',
                'DetailType': 'TaskManualApprovalNeeded',
                'Detail': mock.ANY,
                'EventBusName': 'eventBusName',
                'Time': mock.ANY
            }]
        )

    @mock.patch('lambda_task_orchestrator.eventsClient.put_events')
    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_send_email_task(self, mock_lambda_client, mock_put_events):
        import lambda_task_orchestrator
        import cmf_pipeline # Import the enum from your lambda layer

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 500
        }

        # Mock failed response from EventBridge
        mock_put_events.return_value = {
            'FailedEntryCount': 0,
            'Entries': [{'EventId': 'test-event-id'}]
        }

        lambda_task_orchestrator.lambda_handler(self.pipeline_event_email_task(), None)

        # Verify the event was published with correct parameters
        mock_put_events.assert_called_once_with(
            Entries=[{
                'Source': 'cmf-unittest-task-orchestrator',
                'DetailType': 'EmailAutomationTaskType',
                'Detail': mock.ANY,
                'EventBusName': 'eventBusName',
                'Time': mock.ANY
            }]
        )

    def test_is_pipeline_abandoned_all_abandoned(self):
        import lambda_task_orchestrator
        import cmf_pipeline
        
        # All end tasks are abandoned
        all_abandoned_tasks = [
            {'task_execution_id': '1', 'task_successors': [], 'task_execution_status': cmf_pipeline.TaskExecutionStatus.ABANDONED.value},
            {'task_execution_id': '2', 'task_successors': [], 'task_execution_status': cmf_pipeline.TaskExecutionStatus.ABANDONED.value},
            {'task_execution_id': '3', 'task_successors': ['1', '2'], 'task_execution_status': cmf_pipeline.TaskExecutionStatus.COMPLETE.value}
        ]
        self.assertTrue(lambda_task_orchestrator.is_pipeline_abandoned(all_abandoned_tasks))
    
    def test_is_pipeline_abandoned_mixed_statuses(self):
        import lambda_task_orchestrator
        import cmf_pipeline
        
        # Mixed end tasks (some abandoned, some complete)
        mixed_tasks = [
            {'task_execution_id': '1', 'task_successors': [], 'task_execution_status': cmf_pipeline.TaskExecutionStatus.ABANDONED.value},
            {'task_execution_id': '2', 'task_successors': [], 'task_execution_status': cmf_pipeline.TaskExecutionStatus.COMPLETE.value},
            {'task_execution_id': '3', 'task_successors': ['1', '2'], 'task_execution_status': cmf_pipeline.TaskExecutionStatus.COMPLETE.value}
        ]
        self.assertFalse(lambda_task_orchestrator.is_pipeline_abandoned(mixed_tasks))
    
