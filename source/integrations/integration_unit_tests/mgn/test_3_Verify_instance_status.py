#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import copy
import importlib
import unittest
from unittest.mock import patch
from moto import mock_aws

import mgn.test_mgn_common as test_mgn_common
from mgn.test_mgn_common import mock_file_open, default_mock_os_environ, logger, servers_list, mock_boto_api_call, \
    StatusCodeUpdate, mock_factory_login, mock_sleep, mock_get_factory_servers, VALID_TOKEN, servers_list_no_fdqn


@mock_aws
@patch('time.sleep', new=mock_sleep)
@patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
@patch('builtins.open', new=mock_file_open)
@patch('mfcommon.factory_login', new=mock_factory_login)
@patch('mfcommon.get_factory_servers', new=mock_get_factory_servers)
@patch.dict('os.environ', default_mock_os_environ)
@patch('mfcommon.update_server_migration_status')
class VerifyInstanceStatusTestCase(unittest.TestCase):

    @patch('builtins.open', new=mock_file_open)
    def test_server_not_in_mgn(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        verify_instance.TIME_OUT = 0
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(VALID_TOKEN, '1', '2/2 status checks : Server not in MGN')

    @patch('builtins.open', new=mock_file_open)
    def test_server_no_server_fdqn(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        verify_instance.TIME_OUT = 0
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        with self.assertRaises(SystemExit):
            verify_instance.verify_instance_status(copy.deepcopy(servers_list_no_fdqn))
        self.assertEqual(0, mock_update_server_migration_status.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_no_instance_id(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_instance_id'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Target instance not exist')

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_not_existing_instance_id(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_not_existing_instance_id'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        self.assertEqual(1, mock_update_server_migration_status.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Passed')

    def assert_test_mgn_with_running_ok_api_error(self, status_code, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(status_code)
        with self.assertRaises(SystemExit):
            verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Passed')

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_api_error_401(self, mock_update_server_migration_status):
        self.assert_test_mgn_with_running_ok_api_error(401, mock_update_server_migration_status)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_api_error_400(self, mock_update_server_migration_status):
        self.assert_test_mgn_with_running_ok_api_error(500, mock_update_server_migration_status)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_stopped_ok(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_stopped_ok'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Failed')

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_impaired(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_impaired'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Failed')

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_failed(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_failed'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Failed')

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_instance_id_not_matching(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_instance_id_not_matching'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.verify_instance_status(copy.deepcopy(servers_list))
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Target instance not exist')

    @patch('builtins.open', new=mock_file_open)
    def test_main(self, mock_update_server_migration_status):
        verify_instance = importlib.import_module('3-Verify-instance-status')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        verify_instance.TIME_OUT = 0
        mock_update_server_migration_status.return_value = StatusCodeUpdate(200)
        verify_instance.main(["--Waveid", "1"])
        mock_update_server_migration_status.assert_called_with(
            VALID_TOKEN, '1', '2/2 status checks : Passed')

