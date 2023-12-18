#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import boto3
import multiprocessing
from unittest import TestCase, mock
from moto import mock_sts, mock_iam, mock_ec2, mock_resourcegroups
import test_lambda_mgn_common_util
from test_lambda_mgn_common_util import default_mock_os_environ, \
mock_boto_api_call, mock_iam_get_instance_profile
from lambda_mgn_template import add_server_validation_error, \
add_error, verify_eni_sg_combination, \
validate_server_networking_settings, \
verify_subnets, verify_vpc_for_subnet_sg, \
verify_security_group, check_errors, \
check_server_os_family, \
verify_iam_instance_profile, \
create_launch_template, \
update_tenancy
from cmf_logger import logger


@mock_ec2
@mock_iam
@mock_sts
@mock_resourcegroups
@mock.patch.dict('os.environ', default_mock_os_environ)
class MGNLambdaTemplateTestCase(TestCase):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self):
        # Initialize test data
        logger.debug("Setup start")
        self.ec2_client = boto3.client('ec2')
        self.iam_client = boto3.client('iam')
        self.rg_client =  boto3.client('resource-groups')
        self.mgn_client = boto3.client('mgn')
        self.license_client = boto3.client('license-manager')
        self.server_type = 'Test'
        self.action = 'Validate Launch Template'
        self.launch_template_latest_ver = 1
        self.factory_server = {
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
            "network_interface_id": "test_network_interface_id",
            "securitygroup_id": "test_securitygroup_id",
            "iamRole": "test_iam_role",
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
            "source_server_id": "test-server_id"
        }
        self.verify_subnet = {
            "Subnets": [
                {
                    "State": "available",
                    "SubnetId": "subnet-02ee1e6b9543b81c9",
                    "VpcId": "test_vpc_id",
                    "SubnetArn": "test_subnet_arn"
                }
            ]
        }
        self.verify_sgs = {
            "SecurityGroups": [
                {
                    "VpcId": "test_vpc_id",
                    "GroupId": "test_group"
                }
            ]
        }
        self.launch_template_data_latest = {
            "KernelId": "test_kernelId",
            "EbsOptimized": False,
            "IamInstanceProfile": {
                "Arn": "test_arn",
                "Name": "test_name"
            }
        }
        self.new_launch_template = {
            "KernelId": "test_kernelId",
            "EbsOptimized": False,
            "IamInstanceProfile": {
                "Arn": "test_arn",
                "Name": "test_name"
            },
            "BlockDeviceMappings":[{
                "Ebs":{
                   "VolumeType": "test_volume_type",
                   "Iops": 2000,
                   "Throughput": 250,
                   "Encrypted": True,
                   "KmsKeyId": ""
                }
            }]
        }
        self.instance_profile = mock_iam_get_instance_profile()
        logger.debug("Setup complete")

    def tearDown(self):
        pass
    
    def add_disk_data(self):
        self.factory_server["ebs_volume_type"] = "test_ebs_volume_type"
        self.factory_server["ebs_iops"] = 2500
        self.factory_server["ebs_throughput"] = 300
        self.factory_server["ebs_encrypted"] = False
        self.factory_server["ebs_kms_key_id"] = "test_ebs_kms_key_id"

    def add_metadata_options(self):
        self.factory_server["instance_metadata_options_tags"] = \
            "test_instance_metadata_options_tags"
        self.factory_server["instance_metadata_options_http_endpoint"] = \
            "test_instance_metadata_options_http_endpoint"
        self.factory_server["instance_metadata_options_http_v6"] = \
            "test_instance_metadata_options_http_v6"
        self.factory_server["instance_metadata_options_http_hop_limit"] = 5
        self.factory_server["instance_metadata_options_http_tokens"] = \
            "test_instance_metadata_options_http_tokens"
        
    def add_tag_specifications(self):
        self.new_launch_template["TagSpecifications"] = [
            {
                "ResourceType": "instance",
                "Tags": [
                    {
                        "Key": "test_key_1",
                        "Value": "test_value"
                    },
                    {
                        "Key": "test_key_2",
                        "Value": "test_value"
                    }
                ]
            }
        ]

    def add_network_interfaces(self):
        self.new_launch_template["NetworkInterfaces"] = [
        {
            "DeviceIndex": 0,
            "DeleteOnTermination": True,
            "Groups": [
                "sg-903004f88example"
            ],
            "PrivateIpAddresses": []
        }
    ]

    def test_add_server_validation_error_with_colon_no_server(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_server_validation_error_with_colon_no_server")

        return_dict = {}
        error_msg = "test:error"
        response = add_server_validation_error(self.factory_server, return_dict, error_msg)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = {'ofbiz-web.onpremsim.env': ['ERROR: error']}
        self.assertEqual(return_dict, expected_return_dict)

    def test_add_server_validation_error_with_colon_server(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_server_validation_error_with_colon_server")

        return_dict = {"ofbiz-web.onpremsim.env": ["existing error message"]}
        error_msg = "test:error"
        response = add_server_validation_error(
            self.factory_server, return_dict, error_msg)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = {'ofbiz-web.onpremsim.env': ['existing error message', 'ERROR: error']}
        self.assertEqual(return_dict, expected_return_dict)

    def test_add_server_validation_error_no_colon_no_server(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_server_validation_error_no_colon_no_server")

        return_dict = {}
        error_msg = "test error"
        response = add_server_validation_error(
            self.factory_server, return_dict, error_msg)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = {'ofbiz-web.onpremsim.env': ['ERROR: test error']}
        self.assertEqual(return_dict, expected_return_dict)

    def test_add_server_validation_error_no_colon_with_server(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_server_validation_error_no_colon_with_server")

        return_dict = {"ofbiz-web.onpremsim.env": ["existing error message"]}
        error_msg = "test error"
        response = add_server_validation_error(
            self.factory_server, return_dict, error_msg)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = {'ofbiz-web.onpremsim.env': ['existing error message', 'ERROR: test error']}
        self.assertEqual(return_dict, expected_return_dict)

    def test_add_server_validation_error_no_colon_with_server_additional_context(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_server_validation_error_no_colon_with_server_additional_context")

        return_dict = {"ofbiz-web.onpremsim.env": ["existing error message"]}
        error_msg = "test error"
        additional_context = "test additional context"
        response = add_server_validation_error(
            self.factory_server, return_dict, error_msg, additional_context)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = {'ofbiz-web.onpremsim.env': ['existing error message', 'ERROR: test additional context: test error']}
        self.assertEqual(return_dict, expected_return_dict)

    def test_add_error_with_colon_error_type(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_error_with_colon_error_type")

        return_dict = {"test_error_type": ["test_error_1"]}
        error_message = "test:error"
        error_type = "test_error_type"
        response = add_error(return_dict, error_message, error_type)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = ['test_error_1', 'ERROR: error']
        self.assertEqual(return_dict[error_type], expected_return_dict)

    def test_add_error_with_colon_no_error_type(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_error_with_colon_no_error_type")

        return_dict = {}
        error_message = "test:error"
        error_type = "test_error_type_1"
        response = add_error(return_dict, error_message, error_type)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = ['ERROR: test:error']
        self.assertEqual(return_dict[error_type], expected_return_dict)

    def test_add_error_no_colon_with_error_type(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_error_no_colon_with_error_type")

        return_dict = {"test_error_type": ["test_error_1"]}
        error_message = "test error"
        error_type = "test_error_type"
        response = add_error(return_dict, error_message, error_type)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = ['test_error_1', 'ERROR: test_error_type - test error']
        self.assertEqual(return_dict[error_type], expected_return_dict)

    def test_add_error_no_colon_no_error_type(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_add_error_no_colon_no_error_type")

        return_dict = {}
        error_message = "test error"
        error_type = "test_error_type_1"
        response = add_error(return_dict, error_message, error_type)
        logger.debug(f"Response: {response}")
        expected_response = None
        self.assertEqual(response, expected_response)
        expected_return_dict = ['ERROR: test_error_type_1 - test error']
        self.assertEqual(return_dict[error_type], expected_return_dict)

    def test_verify_eni_sg_combination_invalid(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_eni_sg_combination_invalid")

        network_interface_attr_name = "network_interface_id"
        sg_attr_name = "securitygroup_IDs"
        subnet_attr_name = "subnet_IDs"
        return_dict = {}
        is_valid, server_has_error = verify_eni_sg_combination(
            self.factory_server, network_interface_attr_name, 
            sg_attr_name, subnet_attr_name, self.server_type, return_dict)
        logger.debug(f"is_valid: {is_valid}, server_has_error: {server_has_error}")
        self.assertEqual(is_valid, False)
        self.assertEqual(server_has_error, True)

    def test_verify_eni_sg_combination_valid(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_eni_sg_combination_valid")

        network_interface_attr_name = "network_interface_id_1"
        sg_attr_name = "securitygroup_IDs"
        subnet_attr_name = "subnet_IDs_1"
        return_dict = {}
        is_valid, server_has_error = verify_eni_sg_combination(
            self.factory_server, network_interface_attr_name, 
            sg_attr_name, subnet_attr_name, self.server_type, return_dict)
        logger.debug(f"is_valid: {is_valid}, server_has_error: {server_has_error}")
        self.assertEqual(is_valid, True)
        self.assertEqual(server_has_error, False)

    @mock_sts
    @mock_iam
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_validate_server_networking_settings_existed(self):
        logger.info("Testing test_lambda_mgn_template: "
            "test_validate_server_networking_settings_existed")

        network_interface_attr_name = "network_interface_id"
        sg_attr_name = "securitygroup_IDs_1"
        subnet_attr_name = "subnet_IDs_1"
        return_dict = {}
        response = validate_server_networking_settings(
            self.ec2_client, self.factory_server, network_interface_attr_name, sg_attr_name,
            subnet_attr_name, self.server_type, return_dict)
        logger.debug(f"Response: {response}")
        expected_response = True
        self.assertEqual(response, expected_response)

    @mock_sts
    @mock_iam
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_validate_server_networking_settings_not_existed(self):
        logger.info("Testing test_lambda_mgn_template: "
            "test_validate_server_networking_settings_not_existed")

        network_interface_attr_name = "network_interface_id_1"
        sg_attr_name = "securitygroup_IDs"
        subnet_attr_name = "subnet_IDs_1"
        return_dict = {}
        response = validate_server_networking_settings(
            self.ec2_client, self.factory_server, network_interface_attr_name, sg_attr_name,
            subnet_attr_name, self.server_type, return_dict)
        logger.debug(f"Response: {response}")
        expected_response = False
        self.assertEqual(response, expected_response)

    def test_validate_server_networking_settings_with_exception(self):
        logger.info("Testing test_lambda_mgn_template: "
            "test_validate_server_networking_settings_with_exception")

        network_interface_attr_name = "network_interface_id"
        sg_attr_name = "securitygroup_IDs_1"
        subnet_attr_name = "subnet_IDs_1"
        return_dict = {}
        response = validate_server_networking_settings(
            self.ec2_client, self.factory_server, network_interface_attr_name, sg_attr_name,
            subnet_attr_name, self.server_type, return_dict)
        logger.debug(f"Response: {response}")
        expected_response = False
        self.assertEqual(response, expected_response)

    @mock_sts
    @mock_iam
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_verify_subnets(self):
        logger.info("Testing test_lambda_mgn_template: test_verify_subnets")

        subnet_attr_name = "subnet_IDs"
        return_dict = {}
        server_has_error = False
        verify_subnet, subnet_vpc, server_has_error = verify_subnets(
            subnet_attr_name, self.factory_server, self.ec2_client, 
            return_dict, server_has_error, self.server_type)
        logger.debug(f"verify_subnet: {verify_subnet}, subnet_vpc: {subnet_vpc}, "
                    f"server_has_error: {server_has_error}")
        self.assertEqual(subnet_vpc, "test_vpc_id")
        self.assertEqual(server_has_error, False)

    @mock_sts
    @mock_iam
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_verify_subnets_with_empty_subnets_list(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_subnets_with_empty_subnets_list")

        subnet_attr_name = "subnet_IDs"
        return_dict = {}
        server_has_error = False
        self.factory_server["subnet_IDs"] = []
        verify_subnet, subnet_vpc, server_has_error = verify_subnets(
            subnet_attr_name, self.factory_server, self.ec2_client, 
            return_dict, server_has_error, self.server_type)
        logger.debug(f"verify_subnet: {verify_subnet}, subnet_vpc: {subnet_vpc}, "
                    f"server_has_error: {server_has_error}")
        self.assertEqual(subnet_vpc, "")
        self.assertEqual(server_has_error, True)

        # Reset to default configuration
        self.factory_server["subnet_IDs"] = ["subnet-02ee1e6b9543b81c9"]

    def test_verify_subnets_with_exception(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_subnets_with_exception")

        subnet_attr_name = "subnet_IDs"
        return_dict = {}
        server_has_error = False
        verify_subnet, subnet_vpc, server_has_error = verify_subnets(
            subnet_attr_name, self.factory_server, self.ec2_client, 
            return_dict, server_has_error, self.server_type)
        logger.debug(f"verify_subnet: {verify_subnet}, subnet_vpc: {subnet_vpc}, "
                    f"server_has_error: {server_has_error}")
        self.assertEqual(subnet_vpc, "")
        self.assertEqual(server_has_error, True)
    
    def test_verify_vpc_for_subnet_sg(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_vpc_for_subnet_sg")

        subnet_vpc = 'test_vpc_id'
        return_dict = {}
        type_sg = ''
        server_has_error = False
        response = verify_vpc_for_subnet_sg(
            self.verify_sgs, subnet_vpc, self.verify_subnet,
            self.factory_server, return_dict, type_sg, 
            server_has_error)
        logger.debug(f"Response: {response}")
        self.assertEqual(response, False)

    def test_verify_vpc_for_subnet_sg_without_sg_attribute(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_vpc_for_subnet_sg_without_sg_attribute")

        subnet_vpc = 'test_vpc_id'
        return_dict = {}
        type_sg = ''
        server_has_error = False
        response = verify_vpc_for_subnet_sg(
            {}, subnet_vpc, self.verify_subnet,
            self.factory_server, return_dict, type_sg, 
            server_has_error)
        logger.debug(f"Response: {response}")
        self.assertEqual(response, False)

    def test_verify_security_group_not_existed(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_security_group_not_existed")

        subnet_vpc = 'test_vpc_id'
        sg_attr_name = 'securitygroup_id_1'
        return_dict = {}
        server_has_error = False
        response = verify_security_group(
            self.factory_server, sg_attr_name, self.ec2_client, 
            return_dict, subnet_vpc, self.verify_subnet,
            server_has_error, self.server_type)
        logger.debug(f"Response: {response}")
        self.assertEqual(response, True)

    def test_verify_security_group_with_empty_sg(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_security_group_with_empty_sg")

        subnet_vpc = 'test_vpc_id'
        sg_attr_name = 'securitygroup_id'
        return_dict = {}
        server_has_error = False
        self.factory_server["securitygroup_id"] = ""
        response = verify_security_group(
            self.factory_server, sg_attr_name, self.ec2_client, 
            return_dict, subnet_vpc, self.verify_subnet,
            server_has_error, self.server_type)
        logger.debug(f"Response: {response}")
        self.assertEqual(response, True)

        # Reset to default configuration
        self.factory_server["securitygroup_id"] = "test_securitygroup_id"

    def test_verify_security_group_with_exception(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_security_group_with_exception")

        subnet_vpc = 'test_vpc_id'
        sg_attr_name = 'securitygroup_id'
        return_dict = {}
        server_has_error = False
        response = verify_security_group(
            self.factory_server, sg_attr_name, self.ec2_client, 
            return_dict, subnet_vpc, self.verify_subnet,
            server_has_error, self.server_type)
        logger.debug(f"Response: {response}")
        self.assertEqual(response, True)

    def test_check_errors_with_error(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_check_errors_with_error")

        final_status = 1
        total_servers_count = 1
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        return_dict["ofbiz-web.onpremsim.env"] = "existing error message"
        response = check_errors(return_dict, self.action, final_status, 
                                total_servers_count)
        logger.debug(f"Response: {response}")
        expected_response = '[["ofbiz-web.onpremsim.env", "existing error message"]]'
        self.assertEqual(response, expected_response)

    def test_check_errors_without_error(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_check_errors_without_error")

        final_status = 1
        total_servers_count = 1
        return_dict = {}
        response = check_errors(return_dict, self.action, final_status, 
                                total_servers_count)
        logger.debug(f"Response: {response}")
        expected_response = "SUCCESS: Launch templates validated for all servers in this Wave"
        self.assertEqual(response, expected_response)

    def test_check_errors_without_error_mismatching_sever_count(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_check_errors_without_error_mismatching_sever_count")

        final_status = 1
        total_servers_count = 2
        return_dict = {}
        response = check_errors(return_dict, self.action, final_status, 
                                total_servers_count)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Launch templates validation failed"
        self.assertEqual(response, expected_response)

    def test_check_server_os_family_existed_valid_server(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_check_server_os_family_existed_valid_server")

        return_dict = {}
        server_has_error = False
        response = check_server_os_family(
            self.factory_server, server_has_error, return_dict)
        logger.debug(f"Response: {response}")
        expected_response = False
        self.assertEqual(response, expected_response)

    def test_check_server_os_family_existed_other_server_type(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_check_server_os_family_existed_other_server_type")

        return_dict = {}
        server_has_error = False
        initial_sever_type = self.factory_server['server_os_family']
        self.factory_server['server_os_family'] = "other"
        response = check_server_os_family(
            self.factory_server, server_has_error, return_dict)
        logger.debug(f"Response: {response}")
        expected_response = True
        self.assertEqual(response, expected_response)

        # Reset to default value
        self.factory_server['server_os_family'] = initial_sever_type

    def test_check_server_os_family_not_existed(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_check_server_os_family_not_existed")

        return_dict = {}
        server_has_error = False
        initial_sever_type = self.factory_server['server_os_family']
        del(self.factory_server['server_os_family'])
        response = check_server_os_family(
            self.factory_server, server_has_error, return_dict)
        logger.debug(f"Response: {response}")
        expected_response = True
        self.assertEqual(response, expected_response)

        # Reset to default value
        self.factory_server['server_os_family'] = initial_sever_type

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_verify_iam_instance_profile_with_create_template_exception(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_iam_instance_profile_with_create_template_exception")

        return_dict = {}
        server_has_error = False
        validated_count = 0
        response = verify_iam_instance_profile(
            self.factory_server, self.iam_client, server_has_error,
            return_dict, validated_count, self.action,
            self.new_launch_template, self.launch_template_data_latest,
            self.mgn_client, self.ec2_client, self.launch_template_latest_ver,
            self.rg_client, self.license_client)
        logger.debug(f"Response: {response}")
        expected_response = 0
        self.assertEqual(response, expected_response)

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_verify_iam_instance_profile_with_server_error(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_verify_iam_instance_profile_with_server_error")

        return_dict = {}
        server_has_error = True
        validated_count = 0
        response = verify_iam_instance_profile(
            self.factory_server, self.iam_client, server_has_error,
            return_dict, validated_count, self.action,
            self.new_launch_template, self.launch_template_data_latest,
            self.mgn_client, self.ec2_client, self.launch_template_latest_ver,
            self.rg_client, self.license_client)
        logger.debug(f"Response: {response}")
        expected_response = 0
        self.assertEqual(response, expected_response)

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_create_launch_template_missing_tag_specifications(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_create_launch_template_missing_tag_specifications")

        self.initial_factory_server = self.factory_server
        self.add_disk_data()
        self.add_metadata_options()

        response = create_launch_template(
            self.factory_server, self.action, self.new_launch_template, 
            self.launch_template_data_latest, self.mgn_client, self.ec2_client, 
            self.instance_profile, self.launch_template_latest_ver,
            self.rg_client, self.license_client)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: 'TagSpecifications'"
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_create_launch_template_eni_sg_validation_fail(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_create_launch_template_eni_sg_validation_fail")

        self.initial_factory_server = self.factory_server
        self.add_disk_data()
        self.add_metadata_options()

        self.initial_new_launch_template = self.new_launch_template
        self.add_tag_specifications()
        self.add_network_interfaces()

        response = create_launch_template(
            self.factory_server, self.action, self.new_launch_template, 
            self.launch_template_data_latest, self.mgn_client, self.ec2_client, 
            self.instance_profile, self.launch_template_latest_ver,
            self.rg_client, self.license_client)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Validation failed - Test Launch Template data for server: ofbiz-web.onpremsim.env"
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server
        self.new_launch_template = self.initial_new_launch_template
 
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_create_launch_template_data_validation_fail(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_create_launch_template_data_validation_fail")
        test_lambda_mgn_common_util.MGN_TEST_GET_LICENSE_CONFIGURATION_SCENARIO = \
            'license_not_available'
        test_lambda_mgn_common_util.MGN_TEST_CREATE_LAUNCH_TEMPLATE_VERSION_SCENARIO = \
            'create_launch_template_version_failed'

        self.initial_factory_server = self.factory_server
        self.add_disk_data()
        self.add_metadata_options()

        self.initial_new_launch_template = self.new_launch_template
        self.add_tag_specifications()
        self.add_network_interfaces()

        response = create_launch_template(
            self.factory_server, self.action, self.new_launch_template, 
            self.launch_template_data_latest, self.mgn_client, self.ec2_client, 
            self.instance_profile, self.launch_template_latest_ver,
            self.rg_client, self.license_client)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Validation failed - Test Launch Template data for server: ofbiz-web.onpremsim.env"
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server
        self.new_launch_template = self.initial_new_launch_template

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_create_launch_template_launch_cutover_instances_action_fail(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_create_launch_template_launch_cutover_instances_action_fail")
        
        self.initial_action= self.action
        self.action = "Launch Cutover Instances"

        self.initial_factory_server = self.factory_server
        self.add_disk_data()
        self.add_metadata_options()
        self.factory_server["subnet_IDs"][0] = ""

        self.initial_new_launch_template = self.new_launch_template
        self.add_tag_specifications()
        self.add_network_interfaces()

        response = create_launch_template(
            self.factory_server, self.action, self.new_launch_template, 
            self.launch_template_data_latest, self.mgn_client, self.ec2_client, 
            self.instance_profile, self.launch_template_latest_ver,
            self.rg_client, self.license_client)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Update Failed - Cutover Launch Template for server: ofbiz-web.onpremsim.env"
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server
        self.new_launch_template = self.initial_new_launch_template
        self.action = self.initial_action

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_create_launch_template_launch_test_instances_action_fail(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_create_launch_template_launch_test_instances_action_fail")
        
        self.initial_action= self.action
        self.action = "Launch Test Instances"
 
        self.initial_factory_server = self.factory_server
        self.add_disk_data()
        self.add_metadata_options()
 
        self.initial_new_launch_template = self.new_launch_template
        self.add_tag_specifications()
        self.add_network_interfaces()

        response = create_launch_template(
            self.factory_server, self.action, self.new_launch_template, 
            self.launch_template_data_latest, self.mgn_client, self.ec2_client, 
            self.instance_profile, self.launch_template_latest_ver,
            self.rg_client, self.license_client)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Update Failed - Test Launch Template for server: ofbiz-web.onpremsim.env"
        self.assertIn(expected_response, response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server
        self.new_launch_template = self.initial_new_launch_template
        self.action = self.initial_action

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_update_tenancy_dedicated(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_update_tenancy_dedicated")
 
        self.initial_factory_server = self.factory_server
        self.factory_server["tenancy"] = "dedicated"

        pid_message_prefix = "test message prefix"
        response = update_tenancy(self.factory_server, self.ec2_client, 
                                  self.mgn_client, self.rg_client, pid_message_prefix)
        logger.debug(f"Response: {response}")
        expected_response = {'Tenancy': 'dedicated'}
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_update_tenancy_dedicated_host_mismatch_instance_family(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_update_tenancy_dedicated_host_mismatch_instance_family")
 
        self.initial_factory_server = self.factory_server
        self.factory_server["tenancy"] = "dedicated host"
        self.factory_server["dedicated_host_id"] = "test_dedicated_host_id"
        self.factory_server["instanceType"] = "test_instance_type"
        self.factory_server["dedicated_host_required_capacity"] = \
            "test_dedicated_host_required_capacity"

        pid_message_prefix = "test message prefix"
        response = update_tenancy(self.factory_server, self.ec2_client, 
                                  self.mgn_client, self.rg_client, pid_message_prefix)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Host Supported Instance Family does not match required"
        self.assertIn( expected_response, response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_update_tenancy_dedicated_host(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_update_tenancy_dedicated_host")
 
        self.initial_factory_server = self.factory_server
        self.factory_server["tenancy"] = "dedicated host"
        self.factory_server["dedicated_host_id"] = "test_dedicated_host_id"
        self.factory_server["instanceType"] = "test_instance_family"
        self.factory_server["dedicated_host_required_capacity"] = 100

        pid_message_prefix = "test message prefix"
        response = update_tenancy(self.factory_server, self.ec2_client, 
                                  self.mgn_client, self.rg_client, pid_message_prefix)
        logger.debug(f"Response: {response}")
        expected_response = {'Tenancy': 'host', 'HostId': 'test_dedicated_host_id'}
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_update_tenancy_dedicated_host_insufficient_capacity(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_update_tenancy_dedicated_host_insufficient_capacity")
 
        self.initial_factory_server = self.factory_server
        self.factory_server["tenancy"] = "dedicated host"
        self.factory_server["dedicated_host_id"] = "test_dedicated_host_id"
        self.factory_server["instanceType"] = "test_instance_family"
        self.factory_server["dedicated_host_required_capacity"] = 200

        pid_message_prefix = "test message prefix"
        response = update_tenancy(self.factory_server, self.ec2_client, 
                                  self.mgn_client, self.rg_client, pid_message_prefix)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Host Id: test_dedicated_host_id does not have available capacity of instance type test_instance_family"
        self.assertIn(expected_response, response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server
 
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_update_tenancy_dedicated_host_resource_group(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_update_tenancy_dedicated_host_resource_group")
 
        self.initial_factory_server = self.factory_server
        self.factory_server["tenancy"] = "dedicated host"
        self.factory_server["host_resource_group_arn"] = "test_host_resource_group_arn"

        pid_message_prefix = "test message prefix"
        response = update_tenancy(self.factory_server, self.ec2_client, 
                                  self.mgn_client, self.rg_client, pid_message_prefix)
        logger.debug(f"Response: {response}")
        expected_response = {'Tenancy': 'host', 'HostResourceGroupArn': 'test_host_resource_group_arn'}
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server

    def test_update_tenancy_dedicated_host_missing_valid_tenancy(self):
        logger.info("Testing test_lambda_mgn_template: "
                    "test_update_tenancy_dedicated_host_missing_valid_tenancy")
 
        self.initial_factory_server = self.factory_server
        self.factory_server["tenancy"] = "dedicated host"
        self.factory_server["license_configuration_arn"] = ""

        pid_message_prefix = "test message prefix"
        response = update_tenancy(self.factory_server, self.ec2_client, 
                                  self.mgn_client, self.rg_client, pid_message_prefix)
        logger.debug(f"Response: {response}")
        expected_response = "ERROR: Dedicated host ID, Host Resource Group ARN or License Configuration ARN is required if specifying tenancy as dedicated host."
        self.assertEqual(response, expected_response)

        # Reset to initial configuration
        self.factory_server = self.initial_factory_server