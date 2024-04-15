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
integrations_directory = file.parents[2]
sys.path.append(str(integrations_directory) + '/common')
for directory in os.listdir(str(integrations_directory) + '/mgn/MGN-automation-scripts/'):
    sys.path.append(str(integrations_directory) + '/mgn/MGN-automation-scripts/' + directory)
source_directory = file.parents[3]
for directory in os.listdir(str(source_directory) + '/backend/lambda_layers/'):
    sys.path.append(str(source_directory) + '/backend/lambda_layers/' + directory + '/python')
from cmf_logger import logger
logger.debug(f'sys.path: {list(sys.path)}')

orig_boto_api_call = botocore.client.BaseClient._make_api_call
builtin_open = open
MGN_TEST_SCENARIO = ''
CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = ''
CUT_OVER_MODIFY_INSTANCE_ATTR_SCENARIO = ''
CUT_OVER_EXECUTE_CMD_SCENARIO = ''
VALID_TOKEN = 'valid_token'
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
servers_list = [
    {
        'aws_accountid': '111111111111',
        'aws_region': 'us-east-1',
        'servers': [
            {
                'server_id': '1',
                'server_name': 'server1',
                'server_fqdn': 'server1.local',
                'server_os_family': 'windows',
            },
        ]
    }
]
servers_list_linux = [
    {
        'aws_accountid': '111111111111',
        'aws_region': 'us-east-1',
        'servers': [
            {
                'server_id': '1',
                'server_name': 'server1',
                'server_fqdn': 'server1.local',
                'server_os_family': 'linux',
            },
        ]
    }
]
servers_list_linux_private_ip = [
    {
        'aws_accountid': '111111111111',
        'aws_region': 'us-east-1',
        'servers': [
            {
                'server_id': '1',
                'server_name': 'server1',
                'server_fqdn': 'server1.local',
                'server_os_family': 'linux',
                'private_ip': '192.168.0.5',
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


def get_response_with_replication_state(
        data_replication_state, last_step_status='SUCCEEDED', last_state_name='CREATE_SECURITY_GROUP', eta=None):
    """
    constructs the response to DescribeSourceServers with replication state included
    """
    resp = {
        'ResponseMetadata': {
            'HTTPStatusCode': 200
        },
        'items': [
            {
                'isArchived': False,
                'dataReplicationInfo': {
                    'dataReplicationState': data_replication_state,
                    'dataReplicationInitiation': {
                        'steps': [
                            {
                                'name': last_state_name,
                                'status': last_step_status
                            }
                        ]
                    },
                },
                'sourceProperties': {
                    'networkInterfaces': [
                        {
                            'ips': [
                                "server1.local"
                            ],
                            'isPrimary': True
                        }
                    ]
                }
            }
        ]
    }
    if eta is not None:
        resp['items'][0]['dataReplicationInfo']['etaDateTime'] = eta
    return resp


def mock_aws_describe_instances():
    if MGN_TEST_SCENARIO == 'describe_instance_no_name':
        return {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-111111111111',
                            'Tags': [
                                {
                                    'Key': 'Name',
                                    'Value': ''
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'describe_instance_with_name' or MGN_TEST_SCENARIO == 'mgn_with_running_ok':
        return {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-111111111111',
                            'Tags': [
                                {
                                    'Key': 'Name',
                                    'Value': 'Name1'
                                }
                            ],
                            'NetworkInterfaces': [
                                {
                                    'PrivateIpAddresses': [
                                        {
                                            'PrivateDnsName': 'server1.local',
                                            'PrivateIpAddress': '192.168.0.5'
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'describe_instance_no_private_ip':
        return {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-111111111111',
                            'Tags': [
                                {
                                    'Key': 'Name',
                                    'Value': 'Name1'
                                }
                            ],
                            'NetworkInterfaces': [
                            ]
                        }
                    ]
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'describe_instance_private_ip_no_name':
        return {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-111111111111',
                            'Tags': [
                                {
                                    'Key': 'Name',
                                    'Value': ''
                                }
                            ],
                            'NetworkInterfaces': [
                                {
                                    'PrivateIpAddresses': [
                                        {
                                            'PrivateDnsName': 'server1.local',
                                            'PrivateIpAddress': '192.168.0.5'
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }


def mock_aws_describe_instance_status(obj, operation_name, kwarg):
    if MGN_TEST_SCENARIO == 'mgn_with_not_existing_instance_id':
        return orig_boto_api_call(obj, operation_name, kwarg)
    if MGN_TEST_SCENARIO == 'mgn_with_running_ok' or \
            MGN_TEST_SCENARIO == 'mgn_instance_id_not_matching':
        return {
            'InstanceStatuses': [
                {
                    'InstanceId': 'i-111111111111',
                    'InstanceState': {
                        'Name': 'running'
                    },
                    'InstanceStatus': {
                        'Status': 'OK'
                    },
                    'SystemStatus': {
                        'Status': 'OK'
                    }
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_with_stopped_ok':
        return {
            'InstanceStatuses': [
                {
                    'InstanceId': 'i-111111111111',
                    'InstanceState': {
                        'Name': 'stopped'
                    },
                    'InstanceStatus': {
                        'Status': 'OK'
                    },
                    'SystemStatus': {
                        'Status': 'OK'
                    }
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_with_running_impaired':
        return {
            'InstanceStatuses': [
                {
                    'InstanceId': 'i-111111111111',
                    'InstanceState': {
                        'Name': 'running'
                    },
                    'InstanceStatus': {
                        'Status': 'impaired'
                    },
                    'SystemStatus': {
                        'Status': 'OK'
                    }
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_with_running_failed':
        return {
            'InstanceStatuses': [
                {
                    'InstanceId': 'i-111111111111',
                    'InstanceState': {
                        'Name': 'running'
                    },
                    'InstanceStatus': {
                        'Status': 'failed'
                    },
                    'SystemStatus': {
                        'Status': 'OK'
                    }
                }
            ]
        }


def mock_mgn_describe_source_servers():
    if MGN_TEST_SCENARIO == 'mgn_no_matching_server':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            },
            'items': [
                {
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_no_replication_info':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            },
            'items': [
                {
                    'isArchived': False,
                    'sourceProperties': {
                        'networkInterfaces': [
                            {
                                'ips': [
                                    "server1.local"
                                ],
                                'isPrimary': True
                            }
                        ]
                    }
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_archived':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            },
            'items': [
                {
                    'isArchived': True,
                    'sourceProperties': {
                        'networkInterfaces': [
                            {
                                'ips': [
                                    "server1.local"
                                ],
                                'isPrimary': True
                            }
                        ]
                    }
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_info_stalled':
        return get_response_with_replication_state('STALLED')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_info_initiating':
        return get_response_with_replication_state('Initiating')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_info_continuous':
        return get_response_with_replication_state('continuous')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_info_disconnected':
        return get_response_with_replication_state('disconnected')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_rescan':
        return get_response_with_replication_state('RESCAN', 'In progress')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_initial_sync':
        return get_response_with_replication_state('INITIAL_SYNC', 'In progress')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_rescan_with_last_step_CREATE_SECURITY_GROUP':
        return get_response_with_replication_state('RESCAN', 'SUCCEEDED')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_initial_sync_with_last_step_CREATE_SECURITY_GROUP':
        return get_response_with_replication_state('INITIAL_SYNC', 'SUCCEEDED')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER':
        return get_response_with_replication_state('RESCAN', 'SUCCEEDED', 'START_DATA_TRANSFER')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_initial_sync_with_last_step_START_DATA_TRANSFER':
        return get_response_with_replication_state('INITIAL_SYNC', 'SUCCEEDED', 'START_DATA_TRANSFER')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_rescan_with_last_step_START_DATA_TRANSFER_eta':
        return get_response_with_replication_state('RESCAN', 'SUCCEEDED', 'START_DATA_TRANSFER', '2023-11-22T14:18:00+00:00')
    elif MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_initial_sync_with_last_step_START_DATA_TRANSFER_eta':
        return get_response_with_replication_state('INITIAL_SYNC', 'SUCCEEDED', 'START_DATA_TRANSFER', '2023-11-22T14:18:00+00:00')
    elif MGN_TEST_SCENARIO == 'mgn_no_instance_id':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            },
            'items': [
                {
                    'isArchived': False,
                    'sourceProperties': {
                        'networkInterfaces': [
                            {
                                'ips': [
                                    "server1.local"
                                ],
                                'isPrimary': True
                            }
                        ]
                    }
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_with_not_existing_instance_id' or \
            MGN_TEST_SCENARIO == 'mgn_with_running_ok' or \
            MGN_TEST_SCENARIO == 'mgn_with_stopped_ok' or \
            MGN_TEST_SCENARIO == 'mgn_with_running_impaired' or \
            MGN_TEST_SCENARIO == 'mgn_with_running_failed' or \
            MGN_TEST_SCENARIO == 'describe_instance_private_ip_no_name':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            },
            'items': [
                {
                    'isArchived': False,
                    'launchedInstance': {
                        'ec2InstanceID': 'i-111111111111'
                    },
                    'sourceProperties': {
                        'networkInterfaces': [
                            {
                                'ips': [
                                    "server1.local"
                                ],
                                'isPrimary': True
                            }
                        ]
                    }
                }
            ]
        }
    elif MGN_TEST_SCENARIO == 'mgn_instance_id_not_matching':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            },
            'items': [
                {
                    'isArchived': False,
                    'launchedInstance': {
                        'ec2InstanceID_NOT': 'i-111111111111'
                    },
                    'sourceProperties': {
                        'networkInterfaces': [
                            {
                                'ips': [
                                    "server1.local"
                                ],
                                'isPrimary': True
                            }
                        ]
                    }
                }
            ]
        }
    else:
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            },
            'items': [
                {
                }
            ]
        }


def mock_aws_describe_instance_attribute():
    # if attribute === disableApiTermination
    if CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO == 'ec2_attr_disable_api_termination_true':
        return {
            'DisableApiTermination': {
                'Value': True
            }
        }
    elif CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO == 'ec2_attr_disable_api_termination_false':
        return {
            'DisableApiTermination': {
                'Value': False
            }
        }


def mock_aws_modify_instance_attribute():
    if CUT_OVER_MODIFY_INSTANCE_ATTR_SCENARIO == 'ec2_attr_disable_api_termination_200':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            }
        }
    elif CUT_OVER_MODIFY_INSTANCE_ATTR_SCENARIO == 'ec2_attr_disable_api_termination_500':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 500
            }
        }
    elif CUT_OVER_MODIFY_INSTANCE_ATTR_SCENARIO == 'ec2_attr_disable_api_termination_exception':
        raise Exception('Simulated Exception')


def mock_aws_get_console_screenshot():
    return {
        'ImageData': 'test'
    }


def mock_rekognition_detect_text():
    if CUT_OVER_EXECUTE_CMD_SCENARIO == 'boot_status_check_pass':
        return {
            'TextDetections': [
                {
                    'Type': 'LINE',
                    'DetectedText': 'Press Alt Delete'
                }
            ]
        }
    elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'boot_status_check_fail':
        return {
            'TextDetections': [
                {
                    'Type': 'LINE',
                    'DetectedText': 'loginNOW'
                }
            ]
        }


def mock_aws_put_object():
    return None


def mock_boto_api_call(obj, operation_name, kwarg):
    logger.debug(f'{obj}: operation_name = {operation_name}, kwarg = {kwarg}')

    if operation_name == 'DescribeSourceServers':
        return mock_mgn_describe_source_servers()
    elif operation_name == 'DescribeInstanceStatus':
        return mock_aws_describe_instance_status(obj, operation_name, kwarg)
    elif operation_name == 'DescribeInstances':
        return mock_aws_describe_instances()
    elif operation_name == 'DescribeInstanceAttribute':
        return mock_aws_describe_instance_attribute()
    elif operation_name == 'ModifyInstanceAttribute':
        return mock_aws_modify_instance_attribute()
    elif operation_name == 'GetConsoleScreenshot':
        return mock_aws_get_console_screenshot()
    elif operation_name == 'DetectText':
        return mock_rekognition_detect_text()
    elif operation_name == 'PutObject':
        return mock_aws_put_object()
    else:
        return orig_boto_api_call(obj, operation_name, kwarg)


def mock_file_open(*args, **kwargs):
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


def mock_factory_login():
    return "valid_token"


def mock_sleep(ms):
    logger.debug(f'mock_sleep({ms})')
    pass


def mock_get_factory_servers(wave_id, token, os_split=True, rtype=None):
    logger.debug(f'mock_get_factory_servers({wave_id}, {token}, {os_split}, {rtype})')
    if os_split:
        return [
            {
                'servers_windows': copy.deepcopy(servers_list)[0]['servers'],
                'servers_linux': copy.deepcopy(servers_list_linux)[0]['servers']
            }
        ], True, True
    else:
        return copy.deepcopy(servers_list)


def mock_get_server_credentials(local_username, local_password, server, secret_override=None, no_user_prompts=False):
    logger.debug(f'mock_get_server_credentials({local_username}, '
                 f'{local_password}, {server}, {secret_override}, {no_user_prompts})')
    return {
        'username': 'test_user',
        'password': 'test_password',
        'private_key': 'test_private_key'
    }


def mock_add_windows_servers_to_trusted_hosts(cmf_servers):
    logger.debug(f'mock_add_windows_servers_to_trusted_hosts({cmf_servers})')
    pass


def mock_execute_cmd(host, username, key, cmd: str, using_key):
    logger.debug(f'mock_execute_cmd({host}, {username}, {key}, {cmd}, {using_key})')
    if cmd == 'hostname':
        return 'server1', ''
    elif cmd.startswith('hostname -I | awk'):
        return '192.168.0.5', ''
    elif cmd == 'ps -ef':
        if CUT_OVER_EXECUTE_CMD_SCENARIO == 'vmtoolsd_running':
            return 'vmtoolsd installed', ''
        elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'vmtoolsd_not_running':
            return 'vm tools d not installed', ''
        elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'my_command_running':
            return 'my_command installed', ''
        elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'my_command_not_running':
            return 'my command not installed', ''
        return 'amazon-ssm-agent and others', ''
    elif cmd == 'aws --version':
        if CUT_OVER_EXECUTE_CMD_SCENARIO == 'aws_cli_running':
            return 'aws-cli installed', ''
        elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'aws_cli_probably_running':
            return 'aws cli probably installed', 'aws-cli/ Python/ botocore/'
        elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'aws_cli_not_running':
            return '', ''
    elif cmd.startswith('grep') and cmd.endswith('/etc/hosts'):
        if CUT_OVER_EXECUTE_CMD_SCENARIO == 'host_file_entry_check_pass':
            return '192.168.0.5', ''
        elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'host_file_entry_check_fail':
            return '192.168.5.5', ''
    elif cmd.startswith('grep -E') and cmd.endswith('/etc/resolv.conf'):
        return '192.168.0.5', ''
    elif cmd == 'grep linuxsyslogaws /etc/rsyslog.conf':
        if CUT_OVER_EXECUTE_CMD_SCENARIO == 'syslog_entry_check_pass':
            return 'linuxsyslogaws', ''
        elif CUT_OVER_EXECUTE_CMD_SCENARIO == 'syslog_entry_check_fail':
            return 'no linux sys log aws', ''
    else:
        return 'ok', ''


def mock_create_csv_report(report_name, agent_installed_server_details, wave_id):
    logger.debug(f'mock_crate_csv_report({report_name}, {agent_installed_server_details}, {wave_id})')
    full_path = os.path.join(tempfile.mkdtemp(), 'test_report.csv')
    builtin_open(full_path, "w", newline='')
    return full_path
