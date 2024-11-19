from unittest.mock import patch

import boto3
from moto import mock_aws
import os
from test_common_utils import create_and_populate_tasks, create_and_populate_ssm_scripts, create_and_populate_pipelines

from unittest import TestCase, mock

@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region':'us-east-1', 'application': 'cmf', 'environment': 'unittest', 'SCRIPTS_TABLE_NAME': '{}-{}-'.format('cmf', 'unittest') + 'scripts', 'PIPELINES_TABLE_NAME': '{}-{}-'.format('cmf', 'unittest') + 'pipelines', 'TASK_EXECUTIONS_TABLE_NAME': '{}-{}-'.format('cmf', 'unittest') + 'task_executions'})
@mock_aws
class LambdaPipelineTaskOrchestratorTest(TestCase):
    @mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region':'us-east-1', 'application': 'cmf', 'environment': 'unittest'})
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


    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_pipeline_provisioned(self, mock_lambda_client):
        import lambda_task_orchestrator

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.pipeline_event_provisioned(), None)

        item = self.ddb_client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': "1" }}
        )['Item']
        self.assertEqual("In Progress", item['task_execution_status']['S'])


    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_completed_task(self, mock_lambda_client):
        import lambda_task_orchestrator

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.task_executions_event_complete(2, 2), None)

        item = self.ddb_client.get_item(
            TableName=self.pipeline_table_name,
            Key={'pipeline_id': { 'S': "2" }}
        )['Item']
        print(item)
        self.assertEqual("In Progress", item['pipeline_status']['S'])


    @patch('lambda_task_orchestrator.lambda_client')
    def test_lambda_handler_completed_task_with_successors(self, mock_lambda_client):
        import lambda_task_orchestrator

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200
        }

        lambda_task_orchestrator.lambda_handler(self.task_executions_event_complete(3, 3), None)

        item = self.ddb_client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': "3" }}
        )['Item']
        self.assertEqual("Complete", item['task_execution_status']['S'])
