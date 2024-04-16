import os
import sys
from unittest import TestCase, mock
from pathlib import Path
from botocore.exceptions import ClientError
from boto3.session import Session
from moto import mock_aws

def init():
    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    file = Path(__file__).resolve()
    package_root_directory = file.parents[2]

    sys.path.append(str(package_root_directory))
    sys.path.append(str(package_root_directory) + "/common/")

init()
import lambda_mgn_utils

@mock_aws
class LambdaMgnUtilsTestCase(TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def mock_client_error(*args, **kwargs):
        raise ClientError(operation_name="test.operation", error_response={
            "Error": {
                "Code": "test-code",
                "Message": "test message"
            }
        })

    def test_assume_role_passes(self):
        result = lambda_mgn_utils.assume_role("111111111111", 'us-east-1')
        self.assertIn("AccessKeyId", result)
        self.assertIn("SecretAccessKey", result)
        self.assertIn("SessionToken", result)

    @mock.patch('boto3.client')
    def test_assume_role_returns_error_on_sts_fail(self, mock_client):
        mock_client.return_value = mock.Mock
        mock_client.return_value.get_caller_identity = self.mock_client_error
        
        result = lambda_mgn_utils.assume_role("111111111111", 'us-east-1')

        self.assertIsInstance(result["ERROR"], ClientError)

    @mock.patch('boto3.client', new=mock_client_error)
    def test_assume_role_fails_when_client_fails(self):
        with self.assertRaises(ClientError):
            lambda_mgn_utils.assume_role("111111111111", 'us-east-1')

    def test_get_session_passes(self):
        creds = {}
        creds['AccessKeyId'] = "test_access_key_id"
        creds['SecretAccessKey'] = "test_access_key"
        creds['SessionToken'] = "test_session_token"

        response = lambda_mgn_utils.get_session(creds, "test-region")

        self.assertIsInstance(response, Session)

    @mock.patch("botocore.session.Session", new=mock_client_error)
    def test_get_session_returns_error_on_session_fail(self):
        creds = {}
        creds['AccessKeyId'] = "test_access_key_id"
        creds['SecretAccessKey'] = "test_access_key"
        creds['SessionToken'] = "test_session_token"

        result = lambda_mgn_utils.get_session(creds, "test-region")

        self.assertIsInstance(result["ERROR"], ClientError)

    def test_build_logging_message_passes_with_job_id(self):
        prefix = "test-"
        account_id = "111111111111"
        region = "us-east-1"
        job_id = "test-id"
        result = lambda_mgn_utils.build_logging_message(prefix, account_id, region, job_id)

        self.assertEqual(f"{prefix}{account_id}, Region: {region} - Job Id is: {job_id}", result)

    def test_build_logging_message_passes_without_job_id(self):
        prefix = "test-"
        account_id = "111111111111"
        region = "us-east-1"
        job_id = ""
        result = lambda_mgn_utils.build_logging_message(prefix, account_id, region, job_id)

        self.assertEqual(f"{prefix}{account_id}, Region: {region}", result)

    @mock.patch("os.getpid", return_value=123)
    def test_build_pid_message_passes_with_add_error(self, mock_getpid):
        add_error = True
        suffix = "- test"
        result = lambda_mgn_utils.build_pid_message(add_error, suffix)

        self.assertEqual(f"Pid: {str(os.getpid())} - ERROR: {suffix}", result)

    @mock.patch("os.getpid", return_value=123)
    def test_build_pid_message_passes_without_add_error(self, mock_getpid):
        add_error = False
        suffix = "- test"
        result = lambda_mgn_utils.build_pid_message(add_error, suffix)

        self.assertEqual(f"Pid: {str(os.getpid())}{suffix}", result)

    @mock.patch('lambda_mgn_utils.log')
    def test_handle_error_passes_and_logs_error(self, mock_log):

        error = "Error: error 1:error 2"
        error_prefix = "testprefix-"
        message_suffix = "- test suffix"
        result = lambda_mgn_utils.handle_error(error, error_prefix, message_suffix, True)

        self.assertEqual(
            [mock.call(error)],
            mock_log.error.call_args_list
        )
        self.assertEqual(f"{error_prefix} error 1error 2{message_suffix}", result)

    @mock.patch('lambda_mgn_utils.log')
    def test_handle_error_passes_and_logs_msg(self, mock_log):

        error = "error"
        error_prefix = "testprefix-"
        message_suffix = "- test suffix"
        msg = f"{error_prefix}error{message_suffix}"
        result = lambda_mgn_utils.handle_error(error, error_prefix, message_suffix, False)

        self.assertEqual(
            [mock.call(msg)],
            mock_log.error.call_args_list
        )
        self.assertEqual(msg, result)

    @mock.patch("os.getpid", return_value=123)
    def test_handle_error_with_pid_passes(self, mock_log):
        error_prefix = "ERROR: "
        error = "test-Error: error: more errors"
        message_suffix = "- test suffix"
        err = f"{error_prefix} error more errors{message_suffix}"

        result = lambda_mgn_utils.handle_error_with_pid(error, message_suffix)

        self.assertEqual(err, result)

    @mock.patch("os.getpid", return_value=123)
    def test_handle_error_with_pid_passes_without_colon(self, mock_log):
        error_prefix = "ERROR: "
        error = "test-error"
        message_suffix = "- test suffix"
        err = f"{error_prefix}test-error{message_suffix}"

        result = lambda_mgn_utils.handle_error_with_pid(error, message_suffix)

        self.assertEqual(err, result)

    def test_chunks(self):
        test_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        aggregated_results = []
        
        results = lambda_mgn_utils.chunks(test_list, 5)
        for result in results:
            aggregated_results.append(result)

        self.assertEqual([[1,6],[2,7],[3,8],[4,9],[5,10]], aggregated_results)

    def test_obfuscate_account_id_valid_account_id(self):
        account_id = "123456789012"
        expected = "xxxxxxxxx012"
        result = lambda_mgn_utils.obfuscate_account_id(account_id)
        self.assertEqual(expected, result)

    def test_obfuscate_account_id_empty_string(self):
        account_id = ""
        expected = ""
        result = lambda_mgn_utils.obfuscate_account_id(account_id)
        self.assertEqual(expected, result)

    def test_obfuscate_account_id_non_string(self):
        account_id = 12345
        expected = 12345
        result = lambda_mgn_utils.obfuscate_account_id(account_id)
        self.assertEqual(expected, result)