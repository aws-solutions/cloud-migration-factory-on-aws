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
    if operation_name == 'GetHomeRegion':
        return {
            'HomeRegion': 'us-west-2'
        }
    if operation_name == 'ListConfigurations':
        return {
            'configurations': [{'application.name': 'app1', 'application.configurationId': 'd-app1'}, {'application.name': 'app2', 'application.configurationId': 'd-app2'}]
        }
    if operation_name == 'Scan':
        for k in kwarg:
            if isinstance(kwarg[k], str) and 'LastEvaluatedKey' in kwarg[k]:
                return { 'Items': [{'app_id': '2', 'app_name': 'nonADSApp'}]}
        return { 'Items': [{'app_id': '1', 'app_name': 'app1', 'wave_id': '1'}], 'LastEvaluatedKey': 'LastEvaluatedKey'}


def mock_boto_config_not_found(obj, operation_name, kwarg):
    if operation_name == 'ListConfigurations':
        return {
            'configurations': [{'application.name': 'notFound', 'application.configurationId': 'd-app1'}]
        }
    return mock_boto(obj, operation_name, kwarg)


def get_event(wave_status):
    return {'Records': [{'eventID': '1', 'eventName': 'MODIFY', 'eventVersion': '1.1', 'eventSource': 'aws:dynamodb',
    'awsRegion': 'us-west-2', 'dynamodb': {'ApproximateCreationDateTime': 1706910205.0, 'Keys':
    {'wave_id': {'S': '1'}}, 'NewImage': {'wave_id': {'S': '1'}, 'wave_name': {'S': 'Test'}, 'wave_status': {'S': wave_status}},
    'OldImage': {'wave_id': {'S': '1'}, 'wave_name': {'S': 'Test'}, 'wave_status': {'S': 'In progress'}}}}]}


@mock.patch.dict('os.environ', mock_os_environ)
class LambdaWaveStreamTest(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_no_home_region_is_no_op(self, mock_boto_client):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_no_home_region_is_no_op")
        mock_boto_client.return_value = {}
        from lambda_wave_stream import lambda_handler

        lambda_handler(get_event('Completed'), {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto)
    def test_lambda_handler_with_no_new_image_is_no_op(self):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_no_new_image_is_no_op")
        from lambda_wave_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'OldImage': {'wave_id': {'S': '1'}, 'wave_name': {'S': 'Test'}, 'wave_status': {'S': 'In progress'}}}}]}

        lambda_handler(event, {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto)
    def test_lambda_handler_with_no_wave_status_is_no_op(self):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_no_wave_status_is_no_op")
        from lambda_wave_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'NewImage': {'wave_id': {'S': '1'}, 'wave_name': {'S': 'Test'}}}}]}

        lambda_handler(event, {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto)
    def test_lambda_handler_with_not_supported_wave_status_is_no_op(self):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_not_supported_wave_status_is_no_op")
        from lambda_wave_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'NewImage': {'wave_id': {'S': '1'}, 'wave_name': {'S': 'Test'}, 'wave_status': {'S': 'Planning'}}}}]}

        lambda_handler(event, {})


    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_in_progress_wave_status_sends_notification(self, mock_boto_client):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_in_progress_wave_status_sends_notification")
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        lambda_handler(get_event("In progress"), {})

        mock_boto_client.assert_any_call('NotifyApplicationState', { 'ApplicationId': 'd-app1', 'Status': 'IN_PROGRESS'})


    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_completed_wave_status_sends_notification(self, mock_boto_client):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_completed_wave_status_sends_notification")
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        lambda_handler(get_event("Completed"), {})

        mock_boto_client.assert_any_call('NotifyApplicationState', { 'ApplicationId': 'd-app1', 'Status': 'COMPLETED'})


    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_not_started_wave_status_sends_notification(self, mock_boto_client):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_not_started_wave_status_sends_notification")
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        lambda_handler(get_event("Not started"), {})

        mock_boto_client.assert_any_call('NotifyApplicationState', { 'ApplicationId': 'd-app1', 'Status': 'NOT_STARTED'})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_config_not_found)
    def test_lambda_handler_with_ads_app_not_found_is_no_op(self):
        logger.info("Testing test_lambda_wave_stream: test_lambda_handler_with_ads_app_not_found_is_no_op")
        from lambda_wave_stream import lambda_handler

        lambda_handler(get_event("Not started"), {})