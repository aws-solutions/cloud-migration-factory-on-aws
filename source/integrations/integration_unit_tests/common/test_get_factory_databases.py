#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
from unittest import TestCase, mock
from botocore.exceptions import ClientError

from common.test_mfcommon_util import default_mock_os_environ, mock_file_open, logger

# Filter out internal fields starting with _
def filter_internal(data):
    if isinstance(data, dict):
        return {k: filter_internal(v) for k, v in data.items() if not k.startswith('_')}
    elif isinstance(data, list):
        return [filter_internal(item) for item in data]
    return data

class ApiResponse:
    def __init__(self, json_value):
        self.text = json.dumps(json_value)


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock.patch('builtins.open', new=mock_file_open)
class CMFGetFactoryDatabasesTestCase(TestCase):

    @mock.patch('mfcommon.get_data_from_api')
    def test_get_factory_databases_success(self, mock_get_data_from_api):
        import mfcommon
        mock_get_data_from_api.side_effect = [
            ApiResponse([
                {
                    'database_name': 'db1',
                    'app_ids': ['app1', 'app2'],
                    'wave_id': 'wave1'
                },
                {
                    'database_name': 'db2',
                    'app_ids': ['app1', 'app2'],
                    'wave_id': 'wave1'
                },
                {
                    'database_name': 'db3',
                    'app_ids': ['app1'],
                    'wave_id': 'wave1'
                },
                {
                    'database_name': 'db4',
                    'app_ids': ['app3']
                }
            ]),
            ApiResponse([
                {
                    'app_id': 'app1',
                    'app_name': 'app one',
                    'wave_ids': ['wave1'],
                    'aws_accountid': '111111111111',
                    'aws_region': 'us-east-1'
                },
                {
                    'app_id': 'app2',
                    'app_name': 'app two',
                    'wave_ids': ['wave1', 'wave2'],
                    'aws_accountid': '222222222222',
                    'aws_region': 'us-east-1'
                },
                {
                    'app_id': 'app3',
                    'app_name': 'app three'
                },
            ])
        ]
        result = mfcommon.get_factory_databases('wave1', 'test_token')
        
        expected_result = [
            {
                'aws_accountid': '111111111111',
                'aws_region': 'us-east-1',
                'databases': [
                    {'app_ids': ['app1', 'app2'], 'database_name': 'db1', 'wave_id': 'wave1'},
                    {'app_ids': ['app1', 'app2'], 'database_name': 'db2', 'wave_id': 'wave1'},
                    {'app_ids': ['app1'], 'database_name': 'db3', 'wave_id': 'wave1'},
                ],
            },
            {
                'aws_accountid': '222222222222',
                'aws_region': 'us-east-1',
                'databases': [
                    {'app_ids': ['app1', 'app2'], 'database_name': 'db1', 'wave_id': 'wave1'},
                    {'app_ids': ['app1', 'app2'], 'database_name': 'db2', 'wave_id': 'wave1'},
                ],
            },
        ]
        self.assertEqual(expected_result, filter_internal(result))

    @mock.patch('mfcommon.get_data_from_api')
    def test_get_factory_databases_not_existing_waveid(self, mock_get_data_from_api):
        import mfcommon
        mock_get_data_from_api.side_effect = [
            ApiResponse([
            ]),
            ApiResponse([
                {
                    'app_id': 'app1',
                    'app_name': 'app one',
                    'wave_ids': ['wave1'],
                    'aws_accountid': '111111111111',
                    'aws_region': 'us-east-1'
                }
            ])
        ]
        with self.assertRaises(SystemExit):
            mfcommon.get_factory_databases('wave1_NON_EXISTENT', 'test_token')

    @mock.patch('mfcommon.get_data_from_api')
    def test_get_factory_databases_empty_apps(self, mock_get_data_from_api):
        import mfcommon
        mock_get_data_from_api.side_effect = [
            ApiResponse([
            ]),
            ApiResponse([
            ])
        ]
        with self.assertRaises(SystemExit):
            mfcommon.get_factory_databases('wave1', 'test_token')

    @mock.patch('mfcommon.get_data_from_api')
    def test_get_factory_databases_invalid_account_id(self, mock_get_data_from_api):
        import mfcommon
        mock_get_data_from_api.side_effect = [
            ApiResponse([
            ]),
            ApiResponse([
                {
                    'app_id': 'app1',
                    'app_name': 'app one',
                    'wave_ids': ['wave1'],
                    'aws_accountid': '1',
                    'aws_region': 'us-east-1'
                }
            ])
        ]
        with self.assertRaises(SystemExit):
            mfcommon.get_factory_databases('wave1', 'test_token')

    @mock.patch('mfcommon.get_data_from_api')
    def test_get_factory_databases_db_not_matching(self, mock_get_data_from_api):
        import mfcommon
        mock_get_data_from_api.side_effect = [
            ApiResponse([
                {
                    'database_name': 'db1',
                    'app_ids': ['app1_DIFFERENT'],
                    'wave_id': 'wave1'
                }
            ]),
            ApiResponse([
                {
                    'app_id': 'app1',
                    'app_name': 'app one',
                    'wave_ids': ['wave1'],
                    'aws_accountid': '111111111111',
                    'aws_region': 'us-east-1'
                }
            ])
        ]
        result = mfcommon.get_factory_databases('wave1', 'test_token')
        expected_result = [
            {
                'aws_accountid': '111111111111',
                'aws_region': 'us-east-1',
                'databases': []
            }
        ]
        self.assertEqual(expected_result, filter_internal(result))

    @mock.patch('mfcommon.get_data_from_api')
    def test_get_factory_databases_api_error(self, mock_get_data_from_api):
        import mfcommon
        mock_get_data_from_api.side_effect = ClientError({
            'Error': {
                'Code': 'code_test',
                'Message': 'Simulated Error'
            }
        }, 'test_operation')
        with self.assertRaises(SystemExit):
            mfcommon.get_factory_databases('wave1', 'test_token')

    @mock.patch('mfcommon.get_data_from_api')
    def test_get_factory_databases_filtered(self, mock_get_data_from_api):
        import mfcommon
        mock_get_data_from_api.side_effect = [
            ApiResponse([
                {
                    'database_id': 'db1',
                    'database_name': 'db1',
                    'app_ids': ['app1'],
                    'wave_id': 'wave1'
                },
                {
                    'database_id': 'db2',
                    'database_name': 'db2',
                    'app_ids': ['app2'],
                    'wave_id': 'wave1'
                }
            ]),
            ApiResponse([
                {
                    'app_id': 'app2',
                    'app_name': 'app two',
                    'wave_ids': ['wave1'],
                    'aws_accountid': '111111111111',
                    'aws_region': 'us-east-1'
                },
                {
                    'app_id': 'app1',
                    'app_name': 'app one',
                    'wave_ids': ['wave1'],
                    'aws_accountid': '111111111111',
                    'aws_region': 'us-east-1'
                }
            ])
        ]
        result = mfcommon.get_factory_databases('wave1', 'test_token', ['app1'], ['db1'])
        
        expected_result = [
            {
                'aws_accountid': '111111111111',
                'aws_region': 'us-east-1',
                'databases': [
                    {'app_ids': ['app1'], 
                     'database_id': 'db1', 
                     'database_name': 'db1', 
                     'wave_id': 'wave1'
                     }
                ],
            }
        ]
        self.assertEqual(expected_result, filter_internal(result))
