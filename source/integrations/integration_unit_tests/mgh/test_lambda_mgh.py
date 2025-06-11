#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest import TestCase, mock
import mgh.test_lambda_mgh_common_util
from mgh.test_lambda_mgh_common_util import mock_os_environ, \
    mock_boto_api_call, \
    get_mock_mgh_event, \
    mock_requests_get_schema_with_unsupported_required_attribute, \
    mock_factory_login, \
    mock_successful_get_requests, \
    mock_request_success, \
    mock_request_failure, \
    mock_request_item_errors, \
    mock_missing_app_request, \
    mock_import_ads_discovery_task_arguments, \
    get_mock_ec2_rec_task_arguments, \
    get_mock_create_home_region_task_arguments
from cmf_logger import logger
from polling2 import TimeoutException

import sys

@mock.patch.dict('os.environ', mock_os_environ)
class MGHLambdaTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        # save the builtin open
        cls.builtin_open = open

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self):
        pass


    def tearDown(self):
        pass

    def mock_file_open(*args, **kwargs):
        logger.info(f'mock_file_open : {args}, {kwargs}')
        file_name = args[0]
        # the schema json files are already read in setUpClass,
        logger.info(f'file to open : {file_name}')

        if file_name == 'recommendation-preferences.json':
            dir_lambda_mgh = [d for d in sys.path if 'mgh/lambdas' in d][0]
            rec_preferences_file =  dir_lambda_mgh + 'recommendation-preferences.json'
            return MGHLambdaTestCase.builtin_open(rec_preferences_file)
        else:
            return MGHLambdaTestCase.builtin_open(*args, **kwargs)


    def test_lambda_handler_with_invalid_json_body(self):
        logger.info("Testing test_lambda_mgh: test_lambda_handler_with_invalid_json_body")
        from lambda_mgh import lambda_handler

        event = get_mock_create_home_region_task_arguments()
        event["body"] = "Invalid_body"
        with self.assertRaises(Exception) as e:
            lambda_handler(event, {})
        self.assertEqual("Event body is invalid", str(e.exception))


    def test_lambda_handler_with_missing_action(self):
        logger.info("Testing test_lambda_mgh: test_lambda_handler_with_missing_action")
        from lambda_mgh import lambda_handler

        event = get_mock_mgh_event("", get_mock_create_home_region_task_arguments())
        with self.assertRaises(Exception) as e:
            lambda_handler(event, {})
        self.assertEqual("Invalid action", str(e.exception))


    def test_lambda_handler_with_invalid_action(self):
        logger.info("Testing test_lambda_mgh: test_lambda_handler_with_invalid_action")
        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Invalid", get_mock_create_home_region_task_arguments()), {})
        self.assertEqual("Invalid action", str(e.exception))


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_with_no_existing_home_region_create_home_region_succeeded(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_no_existing_home_region_create_home_region_succeeded")
        from lambda_mgh import lambda_handler

        lambda_handler(get_mock_mgh_event("Create Home Region", get_mock_create_home_region_task_arguments()), {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_with_same_home_region_create_home_region_succeeded(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_same_home_region_create_home_region_succeeded")
        mgh.test_lambda_mgh_common_util.mgh_test_get_home_region_mock_value = 'us-west-2'

        from lambda_mgh import lambda_handler

        lambda_handler(get_mock_mgh_event("Create Home Region", get_mock_create_home_region_task_arguments()), {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_with_different_home_region_then_no_control_found_create_home_region_succeeded(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_different_home_region_then_no_control_found_create_home_region_succeeded")
        mgh.test_lambda_mgh_common_util.mgh_test_get_home_region_mock_value = 'us-east-1'

        from lambda_mgh import lambda_handler

        lambda_handler(get_mock_mgh_event("Create Home Region",get_mock_create_home_region_task_arguments()), {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgh.poll')
    def test_lambda_handler_manage_mgh_actions_with_timeout_then_create_home_region_failed(self, mock_poll):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_timeout_then_create_home_region_failed")
        mgh.test_lambda_mgh_common_util.mgh_test_get_home_region_mock_value = 'us-east-1'
        mock_poll.side_effect = TimeoutException("Test")

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Create Home Region", get_mock_create_home_region_task_arguments()), {})
        self.assertEqual("ERROR: Unable to confirm original MGH Home Region was deleted", str(e.exception))


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_with_different_home_region_and_control_found_create_home_region_succeeded(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_different_home_region_and_control_found_create_home_region_succeeded")
        mgh.test_lambda_mgh_common_util.mgh_test_describe_home_region_controls_mock_value = [{"ControlId" : "control1"}]
        mgh.test_lambda_mgh_common_util.mgh_test_get_home_region_mock_value = 'us-east-1'

        from lambda_mgh import lambda_handler

        lambda_handler(get_mock_mgh_event("Create Home Region", get_mock_create_home_region_task_arguments()), {})


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch("mfcommon.factory_login",new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch('builtins.open', new=mock_file_open)
    @mock.patch("requests.put")
    def test_lambda_handler_manage_mgh_actions_import_ec2_rec_succeeded(self, mocked_requests_put):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_import_ec2_rec_succeeded")
        mocked_requests_put.return_value = mock_request_success()

        from lambda_mgh import lambda_handler

        lambda_handler(get_mock_mgh_event("Import EC2 Recommendations", get_mock_ec2_rec_task_arguments()), {})

        mocked_requests_put.assert_called_with(
            url=mock.ANY,
            headers=mock.ANY,
            timeout=mock.ANY,
            data='{"instanceType": "c6a.4xlarge", "tenancy": "SHARED"}'
        )


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch("mfcommon.factory_login",new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch("requests.put", new=mock_request_failure)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_manage_mgh_actions_with_failed_put_import_ec2_rec_failed(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_failed_put_import_ec2_rec_failed")

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import EC2 Recommendations", get_mock_ec2_rec_task_arguments()), {})
        self.assertEqual("Bad response from API: {}", str(e.exception))


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_manage_mgh_actions_import_ec2_rec_failed(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_import_ec2_rec_failed")
        mgh.test_lambda_mgh_common_util.ads_test_describe_export_tasks_mock_value = [{"exportStatus":"FAILED", "statusMessage": "Could not export"}]

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import EC2 Recommendations", get_mock_ec2_rec_task_arguments()), {})
        self.assertEqual("ERROR: Could not export", str(e.exception))


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch('lambda_mgh.poll')
    @mock.patch("requests.put", new=mock_request_success)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_manage_mgh_actions_timeout_import_ec2_rec_failed(self, mock_poll):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_timeout_import_ec2_rec_failed")
        mock_poll.side_effect = TimeoutException("Test")

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import EC2 Recommendations", get_mock_ec2_rec_task_arguments()), {})
        self.assertEqual("ERROR: Unable to confirm export ID test-export-id was completed", str(e.exception))


    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch("mfcommon.factory_login", new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch("requests.put", new=mock_request_success)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_manage_mgh_actions_with_first_describe_in_progress_import_ec2_recs_succeeded(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_first_describe_in_progress_import_ec2_recs_succeeded")
        mgh.test_lambda_mgh_common_util.ads_test_describe_export_tasks_mock_value = [{"exportStatus":"IN_PROGRESS"}]

        from lambda_mgh import lambda_handler

        lambda_handler(get_mock_mgh_event("Import EC2 Recommendations", get_mock_ec2_rec_task_arguments()), {})


    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_requests_get_schema_with_unsupported_required_attribute)
    def test_lambda_handler_manage_mgh_actions_invalid_app_schema_import_ads_discovery_data_failed(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_invalid_app_schema_import_ads_discovery_data_failed")

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})
        self.assertEqual("ERROR: Can not populate required application attributed: unsupported", str(e.exception))


    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch("requests.post")
    @mock.patch("requests.put")
    def test_lambda_handler_manage_mgh_actions_import_ads_discovery_data_succeeded(self, mocked_requests_put, mocked_requests_post):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_import_ads_discovery_data_succeeded")

        mocked_requests_put.return_value = mock_request_success()
        mocked_requests_post.return_value = mock_request_success()
        from lambda_mgh import lambda_handler

        lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})

        mocked_requests_put.assert_any_call(
            url=mock.ANY,
            headers=mock.ANY,
            timeout=mock.ANY,
            data='{"app_name": "app1", "aws_accountid": "111122223333", "aws_region": "us-west-2"}'
        )
        mocked_requests_put.assert_any_call(
            url=mock.ANY,
            headers=mock.ANY,
            timeout=mock.ANY,
            data='{"app_name": "app2", "aws_accountid": "111122223333", "aws_region": "us-west-2"}'
        )
        mocked_requests_post.assert_any_call(
            url=mock.ANY,
            headers=mock.ANY,
            timeout=mock.ANY,
            data='[{"app_name": "app3", "aws_accountid": "111122223333", "aws_region": "us-west-2"}]'
        )

        mocked_requests_put.assert_any_call(
            url=mock.ANY,
            headers=mock.ANY,
            timeout=mock.ANY,
            data='{"app_id": "1", "server_name": "d-server-1", "server_os_family": "linux", "server_os_version": "2.0.0.0", "server_fqdn": "server1.hostname.com", "r_type": "Rehost"}'
        )
        mocked_requests_post.assert_any_call(
            url=mock.ANY,
            headers=mock.ANY,
            timeout=mock.ANY,
            data='[{"app_id": "2", "server_name": "d-server-2", "server_os_family": "windows", "server_os_version": "53.0.0.1", "server_fqdn": "server2.hostname.com", "r_type": "Rehost"}]'
        )

        self.assertEqual(mocked_requests_put.call_count, 3)
        self.assertEqual(mocked_requests_post.call_count, 2)

    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch("requests.post", new=mock_request_success)
    @mock.patch("requests.put", new=mock_request_failure)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_app_put_failure_import_ads_discovery_data_failed(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_app_put_failure_import_ads_discovery_data_failed")

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})
        self.assertEqual("Bad response from API: {}", str(e.exception))


    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch("requests.post", new=mock_request_success)
    @mock.patch("requests.put", new=mock_request_success)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_with_server_has_multiple_apps_import_ads_discovery_data_error(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_with_server_has_multiple_apps_import_ads_discovery_data_error")
        mgh.test_lambda_mgh_common_util.ads_describe_config_override = {
            'configurations': [{'server.applications': '[{"name": "app1"}, {"name": "app2"}]', 'server.configurationId': 'd-server-1', 'server.hostName': 'server1.hostname.com', 'server.osName': 'Linux - Amazon Linux release 2', 'server.osVersion': '2.0.0.0'}]
        }

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})
        self.assertEqual("Server belongs to multiple applications. User must take action to correct.", str(e.exception))


    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch("requests.post", new=mock_request_item_errors)
    @mock.patch("requests.put", new=mock_request_success)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_app_post_errors_import_ads_discovery_data_failed(self):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_app_post_errors_import_ads_discovery_data_failed")

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})
        self.assertEqual("ERROR: The following errors occurred when attempting to create user objects: \"error\"", str(e.exception))


    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch("requests.post", new=mock_request_success)
    @mock.patch("requests.put")
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_server_put_failure_import_ads_discovery_data_failed(self, mock_put):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_server_put_failure_import_ads_discovery_data_failed")
        mock_put.side_effect = [mock_request_success(), mock_request_success(), mock_request_failure()]

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})
        self.assertEqual("Bad response from API: {}", str(e.exception))


    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_successful_get_requests)
    @mock.patch("requests.post")
    @mock.patch("requests.put", new=mock_request_success)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_manage_mgh_actions_server_post_errors_import_ads_discovery_data_failed(self, mock_post):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_server_post_errors_import_ads_discovery_data_failed")
        mock_post.side_effect = [mock_request_success(), mock_request_failure()]

        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})
        self.assertEqual("Bad response from API: {}", str(e.exception))


    @mock.patch("mfcommon.factory_login",
                new=mock_factory_login)
    @mock.patch("requests.get", new=mock_missing_app_request)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    @mock.patch("requests.post")
    @mock.patch("requests.put")
    def test_lambda_handler_manage_mgh_actions_app_not_found_import_ads_discovery_data_failed(self, mocked_requests_put, mocked_requests_post):
        logger.info("Testing test_lambda_mgh: "
                    "test_lambda_handler_manage_mgh_actions_app_not_found_import_ads_discovery_data_failed")

        mocked_requests_put.return_value = mock_request_success()
        mocked_requests_post.return_value = mock_request_success()
        from lambda_mgh import lambda_handler

        with self.assertRaises(Exception) as e:
            lambda_handler(get_mock_mgh_event("Import ADS Discovery Data", mock_import_ads_discovery_task_arguments()), {})
        self.assertEqual("ERROR: Application with name app1 not found", str(e.exception))
