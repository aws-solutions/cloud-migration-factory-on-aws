#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import copy
import botocore.client
import tempfile

# This is to get around the relative path import issue.
# Absolute paths are being used in this file after setting the root directory
import os
import sys
from pathlib import Path

file = Path(__file__).resolve()
sys.path.append(str(file.parents[0]))
integrations_directory = file.parents[3]
sys.path.append(str(integrations_directory) + '/common')
for directory in os.listdir(str(integrations_directory) + '/automation_packages/ADS/'):
    sys.path.append(str(integrations_directory) + '/automation_packages/ADS/' + directory)
print(f'sys.path: {list(sys.path)}')
from common.test_mfcommon_util import logger
logger.debug(f'sys.path: {list(sys.path)}')

orig_boto_api_call = botocore.client.BaseClient._make_api_call
builtin_open = open
MGN_TEST_SCENARIO = ''
VALID_TOKEN = 'valid_token'
servers_list = [
    {
        'aws_accountid': '111111111111',
        'aws_region': 'us-east-1',
        'servers': [
            {
                'server_id': '1',
                'server_name': 'server1',
                'server_fqdn': 'server1.local',
            },
        ]
    }
]
servers_list_no_fdqn = [
    {
        'aws_accountid': '111111111111',
        'aws_region': 'us-east-1',
        'servers': [
            {
                'server_id': '2',
                'server_name': 'server2',
                'NO_server_fqdn': 'server1.local',
            }
        ]
    }
]
servers_list_with_instance_id = [
    {
        'aws_accountid': '111111111111',
        'aws_region': 'us-east-1',
        'servers': [
            {
                'server_id': '1',
                'server_name': 'server1',
                'server_fqdn': 'server1.local',
                'target_ec2InstanceID': 'i-111111111111'
            },
        ]
    }
]


default_mock_os_environ = {
    'AWS_ACCESS_KEY_ID': 'testing',
    'AWS_SECRET_ACCESS_KEY': 'testing',
    'AWS_SECURITY_TOKEN': 'testing',
    'AWS_SESSION_TOKEN': 'testing',
    'AWS_DEFAULT_REGION': 'us-east-1',
    'region': 'us-east-1',
    'application': 'cmf',
    'environment': 'unittest',
}


def mock_file_open(*args, **kwargs):
    logger.debug(f'mock_file_open : {args}, {kwargs}')
    file_name = args[0]
    logger.debug(f'file to open : {file_name}')
    if file_name == 'FactoryEndpoints.json':
        return builtin_open('./FactoryEndpoints.json')
    elif file_name == 'Wave1-IPs.csv':
        return builtin_open(tempfile.mktemp(), "w", newline='')
    else:
        return builtin_open(*args, **kwargs)


class StatusCodeUpdate:
    """
    dummy class used to create a response for the method update_server_replication_status
    """
    def __init__(self, status_code):
        self.status_code = status_code


def mock_factory_login(silent=False, mf_config_override=None):
    return "valid_token"


def mock_sleep(ms):
    logger.debug(f'mock_sleep({ms})')


def mock_get_factory_servers(*args):
    logger.debug(f'mock_get_factory_servers({args})')
    return copy.deepcopy(servers_list)
