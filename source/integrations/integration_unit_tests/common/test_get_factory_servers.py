import json
from unittest import TestCase, mock
from botocore.exceptions import ClientError

from common.test_mfcommon_util import default_mock_os_environ, mock_file_open


class ApiResponse:
    def __init__(self, json_value):
        self.text = json.dumps(json_value)


@mock.patch.dict("os.environ", default_mock_os_environ)
@mock.patch("builtins.open", new=mock_file_open)
class GetFactoryServersTestCase(TestCase):
    def setUp(self):
        self.token = "test_token"
        self.server1 = {
            "server_id": "server1",
            "server_name": "server1",
            "app_ids": ["app1"],
            "aws_accountid": "111111111111",
            "aws_region": "us-east-1",
            "r_type": "Rehost",
            "server_os_family": "linux",
            "server_fqdn": "server1.onpremsim.env",
            "wave_id": "wave1",
        }
        self.server2 = {
            "server_id": "server2",
            "server_name": "server2",
            "app_ids": ["app1", "app2"],
            "aws_accountid": "111111111111",
            "aws_region": "us-west-2",
            "r_type": "Rehost",
            "server_os_family": "windows",
            "server_fqdn": "server2.workspace.net",
            "wave_id": "wave1",
        }

        self.server3 = {
            "server_id": "server3",
            "server_name": "server3",
            "app_ids": ["app2", "app3"],
            "aws_accountid": "222222222222",
            "aws_region": "us-west-2",
            "r_type": "Rehost",
            "server_os_family": "linux",
            "server_fqdn": "server3.onpremsim.env",
            "wave_id": "wave1",
        }
        self.server4 = {
            "server_id": "server4",
            "server_name": "server4",
            "app_ids": ["app2", "app4"],
            "aws_accountid": "111111111111",
            "aws_region": "us-east-1",
            "r_type": "Rehost",
            "server_os_family": "windows",
            "server_fqdn": "server4.workspace.net",
            "wave_id": "wave2",
        }

        self.server5 = {
            "server_id": "server5",
            "server_name": "server5",
            "app_ids": ["app4"],
            "aws_accountid": "111111111111",
            "aws_region": "us-east-1",
            "r_type": "Replatform",
            "server_os_family": "windows",
            "server_fqdn": "server5.workspace.net",
            "wave_id": "wave2",
        }
        self.server6 = {
            "server_id": "server6",
            "server_name": "server6",
            "app_ids": ["app4"],
            "aws_accountid": "111111111111",
            "aws_region": "us-east-1",
            "r_type": "Rehost",
            "server_os_family": "linux",
            "server_fqdn": "server6.onpremsim.env",
            "wave_id": "wave2",
        }
        self.server7 = {
            "server_id": "server7",
            "server_name": "server7",
            "app_ids": ["app4"],
            "aws_accountid": "111111111111",
            "aws_region": "us-east-1",
            "r_type": "Rehost",
            "server_os_family": "linux",
            "server_fqdn": "server7.onpremsim.env",
        }
        self.server8 = {
            "server_id": "server8",
            "server_name": "server8",
            "app_ids": ["app1"],
            "r_type": "Rehost",
            "server_os_family": "linux",
            "server_fqdn": "server8.onpremsim.env",
            "wave_id": "wave1",
        }

        self.servers = [
            self.server1,
            self.server2,
            self.server3,
            self.server4,
            self.server5,
            self.server6,
            self.server7,
            self.server8,
        ]

    def tearDown(self):
        pass

    def _setup_default_mock_api(self, mock_get_data_from_api):
        mock_get_data_from_api.side_effect = [ApiResponse(self.servers)]

    # group_servers_by_account
    @mock.patch("builtins.print")
    def test_group_servers_by_account_invalid_account_id(self, mock_print):
        import mfcommon

        self.server1["aws_accountid"] = "1234567890"

        _, _, _, errors = mfcommon.group_servers_by_account(
            servers=[self.server1], os_split=True, waveid="wave1", log_error=mock_print
        )

        msg = "ERROR: Incorrect AWS Account Id for server: server1. Must be 12 digits."
        mock_print.assert_any_call(msg)
        self.assertIn(msg, errors)

    @mock.patch("builtins.print")
    def test_group_servers_by_account_no_os_family(self, mock_print):
        import mfcommon

        del self.server1["server_os_family"]

        _, _, _, errors = mfcommon.group_servers_by_account(
            servers=[self.server1], os_split=True, waveid="wave1", log_error=mock_print
        )

        msg = "ERROR: server_os_family does not exist for: server1"
        mock_print.assert_any_call(msg)
        self.assertIn(msg, errors)

    @mock.patch("builtins.print")
    def test_group_servers_by_account_invalid_os_family(self, mock_print):
        import mfcommon

        self.server1["server_os_family"] = "unix"

        _, _, _, errors = mfcommon.group_servers_by_account(
            servers=[self.server1], os_split=True, waveid="wave1", log_error=mock_print
        )

        msg = "ERROR: Invalid server_os_family for: server1, please select either Windows or Linux"
        mock_print.assert_any_call(msg)
        self.assertIn(msg, errors)

    @mock.patch("builtins.print")
    def test_group_servers_by_account_no_fqdn(self, mock_print):
        import mfcommon

        del self.server1["server_fqdn"]

        _, _, _, errors = mfcommon.group_servers_by_account(
            servers=[self.server1], os_split=True, waveid="wave1", log_error=mock_print
        )

        msg = "ERROR: server_fqdn for server: server1 doesn't exist"
        mock_print.assert_any_call(msg)
        self.assertIn(msg, errors)

    @mock.patch("builtins.print")
    def test_group_servers_by_account_empty(self, mock_print):
        import mfcommon

        _, _, _, errors = mfcommon.group_servers_by_account(
            servers=[self.server8], os_split=True, waveid="wave1", log_error=mock_print
        )

        msg = "ERROR: server list for wave_id wave1 is empty"
        mock_print.assert_any_call(msg)
        self.assertIn(msg, errors)

    # get_factory_servers
    @mock.patch("mfcommon.get_data_from_api")
    @mock.patch("sys.exit")
    @mock.patch("builtins.print")
    def test_get_factory_servers_client_error(self, mock_print, mock_exit, mock_get_data_from_api):
        import mfcommon

        error = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, operation_name="GetData"
        )
        mock_get_data_from_api.side_effect = error

        mfcommon.get_factory_servers(waveid="wave1", token=self.token)

        mock_print.assert_called_once_with("ERROR:  Access denied")
        mock_exit.assert_called_once()

    @mock.patch("mfcommon.get_data_from_api")
    def test_get_factory_servers_by_wave1_success(self, mock_get_data_from_api):
        import mfcommon

        self._setup_default_mock_api(mock_get_data_from_api)
        aws_accounts, linux_exist, windows_exist = mfcommon.get_factory_servers(waveid="wave1", token=self.token)

        self.assertEqual(
            aws_accounts,
            [
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-east-1",
                    "servers_windows": [],
                    "servers_linux": [self.server1],
                },
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-west-2",
                    "servers_windows": [self.server2],
                    "servers_linux": [],
                },
                {
                    "aws_accountid": "222222222222",
                    "aws_region": "us-west-2",
                    "servers_windows": [],
                    "servers_linux": [self.server3],
                },
            ],
        )

        self.assertEqual(linux_exist, True)
        self.assertEqual(windows_exist, True)

    @mock.patch("mfcommon.get_data_from_api")
    def test_get_factory_servers_by_wave2_success(self, mock_get_data_from_api):
        import mfcommon

        self._setup_default_mock_api(mock_get_data_from_api)
        aws_accounts, linux_exist, windows_exist = mfcommon.get_factory_servers(waveid="wave2", token=self.token)

        self.assertEqual(
            aws_accounts,
            [
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-east-1",
                    "servers_windows": [
                        self.server4,
                        self.server5,
                    ],
                    "servers_linux": [
                        self.server6,
                    ],
                }
            ],
        )

        self.assertEqual(linux_exist, True)
        self.assertEqual(windows_exist, True)

    @mock.patch("mfcommon.get_data_from_api")
    def test_get_factory_servers_by_app_success(self, mock_get_data_from_api):
        import mfcommon

        self._setup_default_mock_api(mock_get_data_from_api)
        aws_accounts, linux_exist, windows_exist = mfcommon.get_factory_servers(
            waveid="wave1", token=self.token, app_ids=["app1"]
        )

        self.assertEqual(
            aws_accounts,
            [
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-east-1",
                    "servers_windows": [],
                    "servers_linux": [self.server1],
                },
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-west-2",
                    "servers_windows": [self.server2],
                    "servers_linux": [],
                },
            ],
        )

        self.assertEqual(linux_exist, True)
        self.assertEqual(windows_exist, True)

    @mock.patch("mfcommon.get_data_from_api")
    def test_get_factory_servers_by_server_success(self, mock_get_data_from_api):
        import mfcommon

        self._setup_default_mock_api(mock_get_data_from_api)
        aws_accounts, linux_exist, windows_exist = mfcommon.get_factory_servers(
            waveid="wave1", token=self.token, server_ids=["server1", "server3"]
        )

        self.assertEqual(
            aws_accounts,
            [
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-east-1",
                    "servers_windows": [],
                    "servers_linux": [self.server1],
                },
                {
                    "aws_accountid": "222222222222",
                    "aws_region": "us-west-2",
                    "servers_windows": [],
                    "servers_linux": [self.server3],
                },
            ],
        )

        self.assertEqual(linux_exist, True)
        self.assertEqual(windows_exist, False)

    @mock.patch("mfcommon.get_data_from_api")
    def test_get_factory_servers_by_rtype_success(self, mock_get_data_from_api):
        import mfcommon

        self._setup_default_mock_api(mock_get_data_from_api)
        aws_accounts, linux_exist, windows_exist = mfcommon.get_factory_servers(
            waveid="wave2", token=self.token, rtype="Rehost"
        )

        self.assertEqual(
            aws_accounts,
            [
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-east-1",
                    "servers_windows": [self.server4],
                    "servers_linux": [self.server6],
                }
            ],
        )

        self.assertEqual(linux_exist, True)
        self.assertEqual(windows_exist, True)

    @mock.patch("mfcommon.get_data_from_api")
    def test_get_factory_servers_no_os_split_success(self, mock_get_data_from_api):
        import mfcommon

        self._setup_default_mock_api(mock_get_data_from_api)
        aws_accounts = mfcommon.get_factory_servers(waveid="wave2", token=self.token, os_split=False)

        self.assertEqual(
            aws_accounts,
            [
                {
                    "aws_accountid": "111111111111",
                    "aws_region": "us-east-1",
                    "servers": [
                        self.server4,
                        self.server5,
                        self.server6,
                    ],
                }
            ],
        )
