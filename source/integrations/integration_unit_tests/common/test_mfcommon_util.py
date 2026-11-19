#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import json
import boto3
import sys
import requests
import paramiko
from pathlib import Path
from moto import mock_aws


# This class will be used by the mock function to replace requests.get
class MockResponseToRequest:
    def __init__(self, json_data, status_code, text):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text

    def json(self):
        return self.json_data


def init():
    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    file = Path(__file__).resolve()
    package_root_directory = file.parents[2]
    sys.path.append(str(package_root_directory))
    sys.path.append(str(package_root_directory) + '/common/')
    sys.path.append(str(package_root_directory) + '/../backend/lambda_unit_test/')

    source_directory = file.parents[3]
    for directory in os.listdir(str(source_directory) + '/backend/lambda_layers/'):
        sys.path.append(str(source_directory) + '/backend/lambda_layers/' + directory + '/python')

    print(f'sys.path: {list(sys.path)}')


init()
from cmf_logger import logger

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
builtin_open = open


def create_default_config_file():
    mf_config = {
        "LoginApi": "xxxxxx",
        "UserApi": "xxxxxx",
        "Region": "us-east-1",
        "UserPoolId": "xxxxxx"
    }
    json_data = json.dumps(mf_config)
    with open("../FactoryEndpoints.json", "w") as outfile:
        outfile.write(json_data)

    return mf_config


def load_default_config_file(file_name):
    with open(file_name) as json_file:
        cmf_config = json.load(json_file)

    return cmf_config


def delete_default_config_file():
    if os.path.exists("../FactoryEndpoints.json"):
        os.remove("../FactoryEndpoints.json")


@mock_aws
def set_up_secret_manager(mf_config, is_password_updated, service_account_email):
    secretsmanager_client = boto3.client(
        'secretsmanager', mf_config['Region'])
    secret_id = 'MFServiceAccount-' + mf_config['UserPoolId']
    test_password = 'P2$Sword'
    if is_password_updated:
        test_password = ''.join(reversed('P2$Sword'))
    if service_account_email:
        secret_string = "{\"username\": \"%s\", \"password\": \"%s\"}" % (service_account_email, test_password)
    else:
        secret_string = "{\"password\": \"%s\"}" % (test_password)
    secretsmanager_client.create_secret(
        Name=secret_id,
        Description=service_account_email,
        SecretString=secret_string
    )

    return secretsmanager_client, service_account_email, secret_id, secret_string


@mock_aws
def set_up_cognito_credential():
    from test_lambda_cognito_base import CognitoTestsBase
    ctb = CognitoTestsBase()
    ctb.setUp()
    ctb.create_user_pool()
    token, session = ctb.create_verified_user("test@example.com")
    # ctb.create_user_with_software_token_mfa("test2@example.com")
    ctb.create_user_with_sms_mfa("test3@example.com")

    return ctb, token, session


def mock_requests_put(*args, **kwargs):
    return MockResponseToRequest(
        "",
        200,
        ""
    )


def mock_requests_post(*args, **kwargs):
    return MockResponseToRequest(
        "",
        200,
        ""
    )


def mock_paramiko_get_private_key(*args, **kwargs):
    return "test_key"


def mock_paramiko_set_missing_host_key_policy(*args, **kwargs):
    return None


def mock_paramiko_ssh_connect(*args, **kwargs):
    return None


def mock_paramiko_exec_command(*args, **kwargs):
    return sys.stdin, sys.stdout, sys.stderr


def mock_read_lines(*args, **kwargs):
    return "test_line"


def mock_requests_with_connection_error(*args, **kwargs):
    raise requests.exceptions.ConnectionError


def mock_requests_with_failed_status_code(*args, **kwargs):
    return MockResponseToRequest(
        "",
        500,
        ""
    )


def mock_raise_paramiko_ssh_exception(*args, **kwargs):
    raise paramiko.SSHException


def mock_raise_io_exception(*args, **kwargs):
    raise IOError


def mock_raise_exception(*args, **kwargs):
    raise Exception


def mock_execute_cmd_via_ssh_with_ubuntu(*args, **kwargs):
    output = {"ubuntu": "test_server"}
    return output, ""


def mock_execute_cmd_via_ssh_with_fedora(*args, **kwargs):
    output = {"fedora": "test_server"}
    return output, ""


def mock_execute_cmd_via_ssh_with_suse(*args, **kwargs):
    output = {"suse": "test_server"}
    return output, ""


def mock_subprocess_run(*args, **kwargs):
    return None


def mock_file_open(*args, **kwargs):
    file_name = args[0]
    logger.debug(f'file to open : {file_name}')
    if file_name == 'FactoryEndpoints.json':
        return builtin_open('./FactoryEndpoints.json')
    else:
        return builtin_open(*args, **kwargs)


def mock_get_cmf_user_login_data(self):
    login_data = {
        "username": "test3@example.com",
        "password": "test_password",
        "mfacode": "mfa_test_code",
        "session": str(self['session'])
    }
    username = "test3@example.com"
    using_secret = True
    return login_data, username, using_secret
