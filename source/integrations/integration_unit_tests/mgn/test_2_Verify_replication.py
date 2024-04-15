#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import importlib
import unittest
from unittest.mock import patch
from moto import mock_aws
from freezegun import freeze_time

import mgn.test_mgn_common as test_mgn_common
from mgn.test_mgn_common import mock_file_open, default_mock_os_environ, logger, servers_list, mock_boto_api_call, \
    StatusCodeUpdate, mock_factory_login, mock_sleep, mock_get_factory_servers, VALID_TOKEN, servers_list_no_fdqn


@mock_aws
@patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
@patch.dict('os.environ', default_mock_os_environ)
@patch('mfcommon.factory_login', new=mock_factory_login)
@patch('mfcommon.get_factory_servers', new=mock_get_factory_servers)
@patch('time.sleep', new=mock_sleep)
@patch('mfcommon.update_server_replication_status', return_value=None)
class VerifyReplicationTestCase(unittest.TestCase):

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_no_matching_server(self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        verify_replication.timeout = 1
        fail_count = verify_replication.verify_replication(servers_list)
        self.assertEqual(0, fail_count)
        self.assertEqual(0, mock_update_server_replication_status.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_no_server_fdqn(self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        verify_replication.timeout = 1
        fail_count = verify_replication.verify_replication(servers_list_no_fdqn)
        self.assertEqual(0, fail_count)
        self.assertEqual(0, mock_update_server_replication_status.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_no_replication_info(self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_no_replication_info'
        # set the timeout to 1 second, otherwise loops for 1 hour
        verify_replication.timeout = 1
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Replication info not Available')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_archived(self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_archived'
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, 0)
        self.assertEqual(0, mock_update_server_replication_status.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_info_stalled(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_with_replication_info_stalled'
        # set the timeout to 1 second, otherwise loops for 1 hour
        verify_replication.timeout = 1

        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Stalled')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_info_initiating(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_with_replication_info_initiating'
        # set the timeout to 1 second, otherwise loops for 1 hour
        verify_replication.timeout = 1

        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(
            VALID_TOKEN, '1', 'Initiating - CREATE_SECURITY_GROUP')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_info_continuous(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_with_replication_info_continuous'
        # set the timeout to 1 second, otherwise loops for 1 hour
        verify_replication.timeout = 1

        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, 0)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Healthy')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_info_disconnected(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_with_replication_info_disconnected'
        # set the timeout to 1 second, otherwise loops for 1 hour
        verify_replication.timeout = 1

        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(
            VALID_TOKEN, '1', 'Disconnected - Please reinstall agent')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_state_rescan(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_with_replication_state_rescan'
        # set the timeout to 1 second, otherwise loops for 1 hour
        verify_replication.timeout = 1

        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Rescanning, ETA not available')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_initial_sync(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_matching_server_with_replication_state_initial_sync'
        # set the timeout to 1 second, otherwise loops for 1 hour
        verify_replication.timeout = 1

        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Initial sync, ETA not available')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_state_rescan_with_last_step_CREATE_SECURITY_GROUP(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_rescan_with_last_step_CREATE_SECURITY_GROUP'
        verify_replication.timeout = 1
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'CREATE_SECURITY_GROUP')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_initial_sync_with_last_step_CREATE_SECURITY_GROUP(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_initial_sync_with_last_step_CREATE_SECURITY_GROUP'
        verify_replication.timeout = 1
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'CREATE_SECURITY_GROUP')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER'
        verify_replication.timeout = 1
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Rescanning, ETA not available')

    @patch('builtins.open', new=mock_file_open)
    def test_verify_replication_matching_server_with_replication_initial_sync_with_last_step_START_DATA_TRANSFER(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_initial_sync_with_last_step_START_DATA_TRANSFER'
        verify_replication.timeout = 1
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Initial sync, ETA not available')

    @patch('builtins.open', new=mock_file_open)
    @freeze_time('2023-11-22 13:58')
    def test_verify_replication_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER_eta_minutes(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER_eta'
        verify_replication.timeout = -1
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Rescanning, ETA 20 Minutes')

    @patch('builtins.open', new=mock_file_open)
    @freeze_time('2023-11-22 12:48')
    def test_verify_replication_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER_eta_hours(
            self, mock_update_server_replication_status):
        verify_replication = importlib.import_module('2-Verify-replication')
        test_mgn_common.MGN_TEST_SCENARIO = \
            'mgn_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER_eta'
        verify_replication.timeout = -1
        mock_update_server_replication_status.return_value = StatusCodeUpdate(200)
        response = verify_replication.verify_replication(servers_list)
        self.assertEqual(response, -1)
        mock_update_server_replication_status.assert_called_with(VALID_TOKEN, '1', 'Rescanning, ETA 1 Hours')

    @patch('builtins.open', new=mock_file_open)
    def test_main(self, mock_update_server_replication_status):
        # no need to cover all cases, only make sure that main works
        # because all those cases are tested above by testing the function verify_replication
        verify_replication = importlib.import_module('2-Verify-replication')
        verify_replication.timeout = 1
        result = verify_replication.main(["--Waveid", "1"])
        self.assertEqual(0, mock_update_server_replication_status.call_count)
        self.assertEqual(0, result)
