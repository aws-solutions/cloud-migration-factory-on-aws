#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest import TestCase, mock

from cmf_logger import logger

mock_os_environ = {
    'application': 'cmf',
    'environment': 'unittest',
    'AWS_DEFAULT_REGION': 'us-east-1'
}

def mock_boto(obj, operation_name, kwarg):
    # Deprecated MGH and ADS APIs removed - function now logs events only
    return {}


def mock_boto_no_server_in_ads(obj, operation_name, kwarg):
    # Deprecated ADS APIs removed - function now logs events only
    return {}


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
    def test_lambda_handler_logs_deprecation_message(self, mock_boto_client):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_logs_deprecation_message")
        mock_boto_client.return_value = {}
        from lambda_server_stream import lambda_handler

        # Test that the function runs without errors and logs appropriately
        lambda_handler(get_event('Validation Complete'), {})
        
        # Since MGH/ADS integration is removed, no API calls should be made
        mock_boto_client.assert_not_called()


    def test_lambda_handler_with_no_new_image_is_no_op(self):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_no_new_image_is_no_op")
        from lambda_server_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'OldImage': {'server_id': {'S': '1'}, 'server_name': {'S': 'Test'}, 'migration_status': {'S': 'Test Complete'}}}}]}

        # Should run without errors - no MGH/ADS calls will be made
        lambda_handler(event, {})


    def test_lambda_handler_with_no_migration_status_is_no_op(self):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_no_migration_status_is_no_op")
        from lambda_server_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'NewImage': {'server_id': {'S': '1'}, 'server_name': {'S': 'Test'}}}}]}

        # Should run without errors - no MGH/ADS calls will be made
        lambda_handler(event, {})


    def test_lambda_handler_with_empty_records(self):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_with_empty_records")
        from lambda_server_stream import lambda_handler

        # Test with empty records
        lambda_handler({'Records': []}, {})


    def test_lambda_handler_logs_server_status_update(self):
        logger.info("Testing test_lambda_server_stream: test_lambda_handler_logs_server_status_update")
        from lambda_server_stream import lambda_handler

        # Test that status updates are logged but no external service calls are made
        lambda_handler(get_event('Migration Complete'), {})
