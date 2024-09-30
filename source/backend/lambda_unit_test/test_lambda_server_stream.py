from botocore.exceptions import ClientError
from unittest import TestCase, mock

from cmf_logger import logger

mock_os_environ = {
    'application': 'cmf',
    'environment': 'unittest',
    'AWS_DEFAULT_REGION': 'us-east-1'
}

def mock_boto(obj, operation_name, kwarg):
    if operation_name == 'GetHomeRegion':
        return {
            'HomeRegion': 'us-west-2'
        }
    if operation_name == "DescribeConfigurations":
        return {}


def mock_boto_no_server_in_ads(obj, operation_name, kwarg):
    if operation_name == "DescribeConfigurations":
        raise ClientError(operation_name="DescribeConfigurations", error_response={
            "Error": {
                "Code": "InvalidParameterValueException",
                "Message": "Test"
            }
        })
    return mock_boto(obj, operation_name, kwarg)


def get_event(migration_status):
    return {'Records': [{'eventID': '1', 'eventName': 'MODIFY', 'eventVersion': '1.1', 'eventSource': 'aws:dynamodb',
            'awsRegion': 'us-west-2', 'dynamodb': {'ApproximateCreationDateTime': 1706910205.0, 'Keys':
            {'server_id': {'S': '1'}}, 'NewImage': {'server_id': {'S': '1'}, 'server_name': {'S': 'Test'}, 'migration_status': {'S': migration_status}},
             'OldImage': {'server_id': {'S': '1'}, 'server_name': {'S': 'Test'}, 'migration_status': {'S': migration_status}}}}]}


@mock.patch.dict('os.environ', mock_os_environ)
class LambdaServerStreamTest(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_no_home_region_is_no_op(self, mock_boto_client):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_no_home_region_is_no_op")
        mock_boto_client.return_value = {}
        from lambda_server_stream import lambda_handler

        lambda_handler(get_event('Validation Complete'), {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto)
    def test_lambda_handler_with_no_new_image_is_no_op(self):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_no_new_image_is_no_opdler_with_no_home_region_is_no_op")
        from lambda_server_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'OldImage': {'server_id': {'S': '1'}, 'server_name': {'S': 'Test'}, 'migration_status': {'S': 'Test Complete'}}}}]}

        lambda_handler(event, {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto)
    def test_lambda_handler_with_no_migration_status_is_no_op(self):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_no_migration_status_is_no_op")
        from lambda_server_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'NewImage': {'server_id': {'S': '1'}, 'server_name': {'S': 'Test'}}}}]}

        lambda_handler(event, {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_no_server_in_ads)
    def test_lambda_handler_with_no_server_in_ads_is_no_op(self):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_no_server_in_ads_is_no_op")
        from lambda_server_stream import lambda_handler

        lambda_handler(get_event('Validation Complete'), {})


    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_server_in_ads_updates_mgh_tracking(self, mock_boto_client):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_server_in_ads_updates_mgh_tracking")
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_server_stream import lambda_handler

        lambda_handler(get_event('Validation Complete'), {})

        for write_call in mock_boto_client.call_args_list:
            print('args: {}'.format(write_call[0]))
            print('kwargs: {}'.format(write_call[1]))

        mock_boto_client.assert_any_call('CreateProgressUpdateStream', { 'ProgressUpdateStreamName': 'CloudMigrationFactory' })
        mock_boto_client.assert_any_call('ImportMigrationTask', { 'ProgressUpdateStream': 'CloudMigrationFactory', 'MigrationTaskName': 'Validation Complete' })
        mock_boto_client.assert_any_call('AssociateDiscoveredResource',
                                         { 'ProgressUpdateStream': 'CloudMigrationFactory',
                                           'MigrationTaskName': 'Validation Complete',
                                           'DiscoveredResource': {'ConfigurationId': 'Test'} })
        mock_boto_client.assert_any_call('NotifyMigrationTaskState',
                                         { 'ProgressUpdateStream': 'CloudMigrationFactory',
                                           'MigrationTaskName': 'Validation Complete',
                                           'NextUpdateSeconds': mock.ANY,
                                           'UpdateDateTime': mock.ANY,
                                           'Task': {'Status': 'COMPLETED'} })


    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_failed_task_updates_mgh_tracking(self, mock_boto_client):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_failed_task_updates_mgh_tracking")
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_server_stream import lambda_handler

        lambda_handler(get_event('Validation Failed'), {})

        mock_boto_client.assert_any_call('CreateProgressUpdateStream', { 'ProgressUpdateStreamName': 'CloudMigrationFactory' })
        mock_boto_client.assert_any_call('ImportMigrationTask', { 'ProgressUpdateStream': 'CloudMigrationFactory', 'MigrationTaskName': 'Validation Failed' })
        mock_boto_client.assert_any_call('AssociateDiscoveredResource',
                                         {'ProgressUpdateStream': 'CloudMigrationFactory',
                                          'MigrationTaskName': 'Validation Failed',
                                          'DiscoveredResource': {'ConfigurationId': 'Test'} })
        mock_boto_client.assert_any_call('NotifyMigrationTaskState',
                                         {'ProgressUpdateStream': 'CloudMigrationFactory',
                                          'MigrationTaskName': 'Validation Failed',
                                          'NextUpdateSeconds': mock.ANY,
                                          'UpdateDateTime': mock.ANY,
                                          'Task': {'Status': 'FAILED'} })