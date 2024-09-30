import boto3
import logging
import os
import test_common_utils

from moto import mock_aws
from unittest import TestCase, mock

loglevel = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger(__name__)

mock_os_environ = {
    **test_common_utils.default_mock_os_environ,
    'socket_url': 'http://example.com'
}

@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class CMFPipelineTest(TestCase):
    @mock.patch.dict('os.environ', mock_os_environ)
    @mock_aws
    def setUp(self):
        import cmf_pipeline
        self.task_executions_table_name = '{}-{}-'.format('cmf', 'unittest') + 'task_executions'
        boto3.setup_default_session()
        self.client = boto3.client("dynamodb", region_name='us-east-1')
        test_common_utils.create_and_populate_tasks(self.client, cmf_pipeline.task_executions_table_name)


    def tearDown(self):
        pass

    def test_update_task_execution_output(self):
        from lambda_layers.lambda_layer_utils.python import cmf_pipeline
        log.info("Testing cmf_pipeline: test_update_task_execution_output")

        last_output_message = 'Last Output Message'
        output = 'Current Output\n'

        cmf_pipeline.update_task_execution_output('1', last_output_message, output)
        item = self.client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': '1'}}
        )['Item']
        self.assertEqual(last_output_message, item['outputLastMessage']['S'])
        self.assertEqual(output, item['output']['S'])

    def test_update_task_execution_status(self):
        from lambda_layers.lambda_layer_utils.python import cmf_pipeline
        log.info("Testing cmf_pipeline: test_update_task_execution_status")

        cmf_pipeline.update_task_execution_status('1', cmf_pipeline.TaskExecutionStatus.COMPLETE)
        item = self.client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': '1'}}
        )['Item']
        self.assertEqual(cmf_pipeline.TaskExecutionStatus.COMPLETE.value, item['task_execution_status']['S'])

    def test_update_task_execution_conditional_check_then_pass(self):
        from lambda_layers.lambda_layer_utils.python import cmf_pipeline
        log.info("Testing cmf_pipeline: test_update_task_execution_conditional_check_then_pass")

        cmf_pipeline.update_task_execution_status('2', cmf_pipeline.TaskExecutionStatus.COMPLETE)
        item = self.client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': '2'}}
        ).get('Item')

        self.assertEqual('Complete', item['task_execution_status']['S'])
