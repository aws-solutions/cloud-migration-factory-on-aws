#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import sys
import botocore.client
from pathlib import Path

MGN_TEST_SCENARIO = 'default'
MGN_TEST_GET_LICENSE_CONFIGURATION_SCENARIO = 'default'
MGN_TEST_CREATE_LAUNCH_TEMPLATE_VERSION_SCENARIO = 'default'
MGN_SERVER_ACTION_SCENARIO = 'default'
orig_boto_api_call = botocore.client.BaseClient._make_api_call

def init():
    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    file = Path(__file__).resolve()
    package_root_directory = file.parents[1]
    sys.path.append(str(package_root_directory) + '/../../backend/lambda_unit_test/')
    sys.path.append(str(package_root_directory) + '/../../backend/lambda_layers/lambda_layer_utils/python/')
    sys.path.append(str(file.parents[0]))
    integrations_directory = str(file.parents[2])
    sys.path.append(integrations_directory)
    sys.path.append(integrations_directory + '/mgn/lambdas/')
    from cmf_logger import logger
    logger.debug(f'sys.path: {list(sys.path)}')

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
    'cors': "test-cors",
    'AnonymousUsageData': 'Yes',
    'solutionUUID': 'test_solution_UUID',
    'solution_identifier': '{"solution_id":"SO101"}'
}

def mock_get_user_resource_creation_policy_deny(obj, event, schema):
    return {'action': 'deny', 'user': 'testuser@example.com'}

def mock_get_user_resource_creation_policy_allow(obj, event, schema):
    return {'action': 'allow', 'user': 'testuser@example.com'}

def mock_get_servers(target_aws_accounts, filtered_apps, waveid, servers):
    error_list = []
    account_servers = [
        {
            "aws_accountid": "111111111111",
            "aws_region": "us-east-1",
            "servers": [
                {
                    "launch_template_id": "lt-01238c059e3466abc",
                    "server_id": "3",
                    "app_id": "2",
                    "instanceType": "t3.medium",
                    "r_type": "Rehost",
                    "securitygroup_IDs": [
                        "sg-0485cd66e0f74adf3"
                    ],
                    "securitygroup_IDs_test": [
                        "sg-0485cd66e0f74adf3"
                    ],
                    "server_environment": "prod",
                    "server_fqdn": "ofbiz-web.onpremsim.env",
                    "server_name": "ofbiz-web.onpremsim.env",
                    "server_os_family": "linux",
                    "server_os_version": "Ubuntu",
                    "server_tier": "web",
                    "subnet_IDs": [
                        "subnet-02ee1e6b9543b81c9"
                    ],
                    "subnet_IDs_test": [
                        "subnet-02ee1e6b9543b81c9"
                    ],
                    "tags": [
                        {
                            "key": "CostCenter",
                            "value": "123"
                        },
                        {
                            "key": "BU",
                            "value": "IT"
                        },
                        {
                            "key": "Location",
                            "value": "US"
                        }
                    ],
                    "tenancy": "Shared",
                    "source_server_id": "test_server_id_12345"
                }
            ],
            "source_server_ids": [
                "test_server_id_12345"
            ]
        }
    ]
    return account_servers, error_list

def mock_update_ec2_launch_template(verified_servers, body):
    return {}
    
def mock_mgn_describe_source_servers():
    logger.info(f"MGN_TEST_SCENARIO: {MGN_TEST_SCENARIO}")
    response = {
        'ResponseMetadata': {
            'HTTPStatusCode': 200
        },
        'items': [
            {
                'isArchived': False,
                'launchedInstance': {
                    'ec2InstanceID': 'i-111111111111'
                },
                'sourceServerID': 'test_server_id_12345',
                'dataReplicationInfo': {
                    'dataReplicationState': 'Initiating',
                    'dataReplicationInitiation': {
                        'steps': [
                            {
                                'name': 'CREATE_SECURITY_GROUP',
                                'status': 'SUCCEEDED'
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
                    ],
                    "identificationHints": {
                        "hostname": "ofbiz-web.onpremsim.env",
                        "fqdn": "ofbiz-web.onpremsim.env"
                    }
                }
            }
        ]
    }
    if MGN_TEST_SCENARIO == 'mgn_matching_server_with_replication_state_disconnected':
        response['items'][0]['dataReplicationInfo']['dataReplicationState'] = 'disconnected'
    return response

def mock_aws_describe_launch_templates():
    response = {
        'LaunchTemplates': [
            {
                'DefaultVersionNumber': 1,
                'LatestVersionNumber': 1,
                'LaunchTemplateId': 'lt-01238c059e3466abc',
                'LaunchTemplateName': 'test_template_name',
            },
        ],
        'ResponseMetadata': {
            '...': '...',
        },
    }
    return response

def mock_aws_describe_launch_template_versions():
    response = {
        "LaunchTemplateVersions": [
            {
                "LaunchTemplateId": "lt-01238c059e3466abc",
                "LaunchTemplateName": "test_template_name",
                "VersionNumber": 1,
                "VersionDescription": "test_description",
                "CreateTime": "2023-12-05",
                "CreatedBy": "test_user",
                "DefaultVersion": True,
                "LaunchTemplateData": {
                    "KernelId": "test_kernelId",
                    "EbsOptimized": False,
                    "IamInstanceProfile": {
                        "Arn": "test_arn",
                        "Name": "test_name"
                    }
                }
            }
        ]
    }
    return response

def mock_aws_describe_network_interfaces():
    response = {
        "NetworkInterfaces": [
            {
                "NetworkInterfaceId": "test_network_interface_id",
                "SubnetId": "test_subnet_id_1",
                "VpcId": "test_vpc_id",
                "Status": "available"
            }
        ]
    }
    return response

def mock_aws_describe_subnets():
    response = {
        "Subnets": [
            {
                "State": "available",
                "SubnetId": "subnet-02ee1e6b9543b81c9",
                "VpcId": "test_vpc_id",
                "SubnetArn": "test_subnet_arn"
            }
        ]
    }
    return response

def mock_aws_describe_security_groups():
    response = {
        "SecurityGroups": [
            {
                "VpcId": "test_vpc_id",
                "GroupId": "test_group"
            }
        ]
    }
    return response

def mock_aws_get_instance_profile():
    response = {
        "InstanceProfile": {
            "Path": "test_path",
            "InstanceProfileName": "test_instance_profile_name",
            "InstanceProfileId": "test_instance_profile_id",
            "Arn": "test_arn",
            "Roles": [
                {
                    "Path": "test_path",
                    "RoleName": "test_role_name",
                    "RoleId": "test_role_id",
                    "Arn": "test_arn"
                }
            ]
        }
    }
    return response

def mock_mgn_update_launch_configuration():
    response = {
        "bootMode": "LEGACY_BIOS",
        "copyPrivateIp": False,
        "copyTags": False,
        "ec2LaunchTemplateID": "lt-01238c059e3466abc",
        "enableMapAutoTagging": False,
        "launchDisposition": "STARTED"
        }
    return response

def mock_license_manager_get_license_configuration():
    license_status = "AVAILABLE"
    if MGN_TEST_GET_LICENSE_CONFIGURATION_SCENARIO == \
        'license_not_available':
        license_status = "MISSING"
    response = {"Status": license_status}
    return response

def mock_aws_create_launch_template_version():
    status_code = 200
    if MGN_TEST_CREATE_LAUNCH_TEMPLATE_VERSION_SCENARIO == \
        'create_launch_template_version_failed':
        status_code = 400
    response = {
        "LaunchTemplateVersion": {
            "LaunchTemplateId": "lt-01238c059e3466abc",
            "LaunchTemplateName": "test_template_name",
            "VersionNumber": 1,
            "LaunchTemplateData": {
                "KernelId": "test_kernel_id",
                "EbsOptimized": False,
                "IamInstanceProfile": {
                    "Arn": "test_arn",
                    "Name": "test_name"
                }
            }
        },
        "ResponseMetadata": {
            "HTTPStatusCode": status_code
        }
    }
    return response

def mock_aws_modify_launch_template():
    response = {
        "LaunchTemplate": {
            "LaunchTemplateId": "lt-01238c059e3466abc",
            "LaunchTemplateName": "test_template_name",
            "DefaultVersionNumber": 1,
            "LatestVersionNumber": 1,
            "Tags": [
                {
                    "Key": "test_key_1",
                    "Value": "test_value_1"
                },
                {
                    "Key": "test_key_2",
                    "Value": "test_value_2"
                }
            ]
        }
    }
    return response

def mock_mgn_launch_terminate_server_instances():
    status_code = 202
    if MGN_SERVER_ACTION_SCENARIO == \
        'launch_server_failed':
        status_code = 400
    response = {
        "job": {
            "arn": "test_arn",
            "jobID": "test_job_id",
            "type": "LAUNCH"
        },
        "ResponseMetadata": {
            "HTTPStatusCode": status_code

        }
    }
    return response

def mock_aws_describe_hosts():
    response = {
        "Hosts": [
            {
                "AvailableCapacity": {
                    "AvailableInstanceCapacity": [
                        {
                            "AvailableCapacity": 123,
                            "InstanceType": "test_instance_family",
                            "TotalCapacity": 123
                        }
                    ]
                },
                "HostId": "test_host_id",
                "HostProperties": {
                    "InstanceType": "test_instance_type",
                    "InstanceFamily": "test_instance_family"
                }
            }
        ]
    }
    return response

def mock_rg_list_group_resources():
    response = {
        "Resources": [
            {
                "Identifier": {
                    "ResourceArn": "test_resource_arn",
                    "ResourceType": "test_resource_type"
                },
                "Status": {
                    "Name": "PENDING"
                }
            }
        ],
        "ResourceIdentifiers": [
            {
                "ResourceArn": "test_resource_arn",
                "ResourceType": "test_resource_type"
            }
        ]
    }
    return response

def mock_boto_api_call(obj, operation_name, kwarg):
    logger.debug(f'{obj}: operation_name = {operation_name}, kwarg = {kwarg}')
    if operation_name == 'DescribeSourceServers':
        return mock_mgn_describe_source_servers()
    elif operation_name == 'DescribeLaunchTemplates':
        return mock_aws_describe_launch_templates()
    elif operation_name == 'DescribeLaunchTemplateVersions':
        return mock_aws_describe_launch_template_versions()
    elif operation_name == 'DescribeNetworkInterfaces':
        return mock_aws_describe_network_interfaces()
    elif operation_name == 'DescribeSubnets':
        return mock_aws_describe_subnets()
    elif operation_name == 'DescribeSecurityGroups':
        return mock_aws_describe_security_groups()
    elif operation_name == 'GetInstanceProfile':
        return mock_aws_get_instance_profile()
    elif operation_name == 'UpdateLaunchConfiguration':
        return mock_mgn_update_launch_configuration()
    elif operation_name == 'GetLicenseConfiguration':
        return mock_license_manager_get_license_configuration()
    elif operation_name == 'CreateLaunchTemplateVersion':
        return mock_aws_create_launch_template_version()
    elif operation_name == 'ModifyLaunchTemplate':
        return mock_aws_modify_launch_template()
    elif operation_name in ('StartTest', 'StartCutover', 
                            'TerminateTargetInstances'):
        return mock_mgn_launch_terminate_server_instances()
    elif operation_name == 'DescribeHosts':
        return mock_aws_describe_hosts()
    elif operation_name == 'ListGroupResources':
        return mock_rg_list_group_resources()
    else:
        return orig_boto_api_call(obj, operation_name, kwarg)
