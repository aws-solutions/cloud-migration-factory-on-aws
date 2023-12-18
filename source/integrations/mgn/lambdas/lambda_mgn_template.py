#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from __future__ import print_function
import os
import multiprocessing
import logging
import json
import lambda_mgn_utils

log = logging.getLogger()
log.setLevel(logging.INFO)

DEDICATED_HOST_STRING = "dedicated host"


def add_server_validation_error(factoryserver, return_dict,
                                error, additional_context=None):
    if additional_context:
        # Append : to message.
        additional_context += ": "
    else:
        # init to null string.
        additional_context = ""

    pid_message = lambda_mgn_utils.build_pid_message(
        True, f"{factoryserver['server_name']}: {additional_context}")

    if ":" in str(error):
        err = ''
        msgs = str(error).split(":")[1:]
        for msg in msgs:
            err = err + msg
        log.error(f"{pid_message}{err}")
        if factoryserver['server_name'] in return_dict:
            # Server has errors already, append additional error.
            mgs_update = return_dict[factoryserver['server_name']]
            mgs_update.append("ERROR: " + additional_context + err)
            return_dict[factoryserver['server_name']] = mgs_update
        else:
            # First error for the server, initialize array of errors for server.
            errors = ["ERROR: " + additional_context + err]
            return_dict[factoryserver['server_name']] = errors
    else:
        log.error(f"{pid_message}{str(error)}")
        if factoryserver['server_name'] in return_dict:
            # Server has errors already, append additional error.
            mgs_update = return_dict[factoryserver['server_name']]
            mgs_update.append("ERROR: " + additional_context + str(error))
            return_dict[factoryserver['server_name']] = mgs_update
        else:
            # First error for the server, initialize array of errors for server.
            errors = ["ERROR: " + additional_context + str(error)]
            return_dict[factoryserver['server_name']] = errors


def add_error(return_dict, error, error_type='non-specific'):
    pid_message = lambda_mgn_utils.build_pid_message(True, "")
    if ":" in str(error):
        err = ''
        msgs = str(error).split(":")[1:]
        for msg in msgs:
            err = err + msg
        log.error(f"{pid_message}{err}")
        if error_type in return_dict:
            # error_type record has errors already, append additional error.
            mgs_update = return_dict[error_type]
            mgs_update.append("ERROR: " + err)
            return_dict[error_type] = mgs_update
        else:
            # First error for the type provided, initialize array of errors for type.
            errors = ["ERROR: " + str(error)]
            return_dict[error_type] = errors
    else:
        log.error(f"{pid_message}{error_type} - {str(error)}")
        if error_type in return_dict:
            # Server has errors already, append additional error.
            mgs_update = return_dict[error_type]
            mgs_update.append("ERROR: " + error_type + " - " + str(error))
            return_dict[error_type] = mgs_update
        else:
            # First error for the server, initialize array of errors for server.
            errors = ["ERROR: " + error_type + " - " + str(error)]
            return_dict[error_type] = errors


def verify_eni_sg_combination(factoryserver, network_interface_attr_name,
                              sg_attr_name, subnet_attr_name, server_type, return_dict):
    server_has_error = False
    is_valid = True
    if factoryserver.get(network_interface_attr_name) \
        and ((factoryserver.get(sg_attr_name) and factoryserver[sg_attr_name][0] != '') \
             or (factoryserver.get(subnet_attr_name) and factoryserver[subnet_attr_name][0] != '')):
        # user has specified both ENI and SGs but this is not a valid combination.
        msg = (f"ERROR: Validation failed - Specifying {server_type} ENI and also {server_type} "
               f"Security Group or Subnet is not supported. ENIs will inherit the SGs and Subnet of the ENI.")
        server_has_error = True
        add_server_validation_error(factoryserver, return_dict, msg)
        is_valid = False

    return is_valid, server_has_error


def verify_subnets(subnet_attr_name, factoryserver, ec2_client,
                   return_dict, server_has_error, server_type):
    type_subnet = f"{server_type} subnet"
    verify_subnet = {}
    subnet_vpc = ""
    if subnet_attr_name in factoryserver:
        if len(factoryserver[subnet_attr_name]) > 0:
            try:
                verify_subnet = ec2_client.describe_subnets(
                    SubnetIds=factoryserver[subnet_attr_name])
                subnet_vpc = verify_subnet['Subnets'][0]['VpcId']
            except Exception as error:
                # Error validating subnet.
                server_has_error = True
                add_server_validation_error(
                    factoryserver, return_dict, error, type_subnet)
        else:
            server_has_error = True
            msg = "ERROR: " + subnet_attr_name + " attribute is empty."
            add_server_validation_error(
                factoryserver, return_dict, msg, type_subnet)
    else:
        server_has_error = True
        msg = "ERROR: " + subnet_attr_name + " does not exist for server."
        add_server_validation_error(
            factoryserver, return_dict, msg, type_subnet)

    return verify_subnet, subnet_vpc, server_has_error


def verify_vpc_for_subnet_sg(verify_sgs, subnet_vpc, verify_subnet,
                             factoryserver, return_dict, type_sg,
                             server_has_error):
    subnet_id = ""
    if verify_subnet:
        subnet_id = verify_subnet['Subnets'][0]['SubnetId']
    if 'SecurityGroups' in verify_sgs:
        for sg in verify_sgs['SecurityGroups']:
            if subnet_vpc != sg['VpcId']:
                server_has_error = True
                msg = "ERROR: Subnet and Security groups must be in the same VPC: " + \
                      subnet_id + ", " + sg['GroupId']
                add_server_validation_error(factoryserver, return_dict, msg, type_sg)

    return server_has_error


def verify_security_group(factoryserver, sg_attr_name, ec2_client,
                          return_dict, subnet_vpc, verify_subnet,
                          server_has_error, server_type):
    type_sg = f"{server_type} security groups"
    if sg_attr_name in factoryserver:
        if len(factoryserver[sg_attr_name]) > 0:
            verify_sgs = {}
            try:
                verify_sgs = ec2_client.describe_security_groups(
                    GroupIds=factoryserver[sg_attr_name])
            except Exception as error:
                # Error validating SGs.
                server_has_error = True
                add_server_validation_error(
                    factoryserver, return_dict, error, type_sg)

            server_has_error = verify_vpc_for_subnet_sg(
                verify_sgs, subnet_vpc, verify_subnet,
                factoryserver, return_dict, type_sg,
                server_has_error)

        else:
            server_has_error = True
            msg = "ERROR: " + sg_attr_name + " attribute is empty."
            add_server_validation_error(
                factoryserver, return_dict, msg, type_sg)
    else:
        server_has_error = True
        msg = "ERROR: " + sg_attr_name + " does not exist for server: " + factoryserver['server_name']
        add_server_validation_error(
            factoryserver, return_dict, msg, type_sg)

    return server_has_error


def validate_server_networking_settings(ec2_client, factoryserver, network_interface_attr_name, sg_attr_name,
                                        subnet_attr_name, server_type, return_dict):
    print(factoryserver)

    # Identify invalid combination of ENI and security groups
    is_valid, server_has_error = verify_eni_sg_combination(
        factoryserver, network_interface_attr_name,
        sg_attr_name, subnet_attr_name, server_type, return_dict)

    # Exit and do not validate other settings as invalid configuration and waste of resource time until resolved.
    if not is_valid:
        return False

    # Check if ENI specified.
    if factoryserver.get(network_interface_attr_name):
        # Check ENI exist
        try:
            ec2_client.describe_network_interfaces(
                NetworkInterfaceIds=[factoryserver[network_interface_attr_name], ])
        except Exception as error:
            # Error validating ENI.
            server_has_error = True
            add_server_validation_error(
                factoryserver, return_dict, error, server_type + ' ENI')
    else:
        # Verify Subnets
        verify_subnet, subnet_vpc, server_has_error = verify_subnets(
            subnet_attr_name, factoryserver, ec2_client,
            return_dict, server_has_error, server_type)

        # Verify SGs
        server_has_error = verify_security_group(
            factoryserver, sg_attr_name, ec2_client, return_dict,
            subnet_vpc, verify_subnet, server_has_error, server_type)

    return not server_has_error


def check_errors(return_dict, action, final_status, total_servers_count):
    if len(return_dict.items()) > 0:
        log.error("ERROR: Launch templates validation failed - " + str(
            len(return_dict.items())) + " servers with errors.")
        print(str(return_dict.items()))
        return json.dumps(return_dict.items())
    else:
        if action.strip() == 'Validate Launch Template':
            if final_status == total_servers_count:
                msg = "SUCCESS: Launch templates validated for all servers in this Wave"
                log.info(msg)
                return msg
            else:
                msg = "ERROR: Launch templates validation failed"
                log.error(msg)
                return msg


def update_launch_template(factoryservers, action):
    try:
        # Check if the action is launch servers or validate launch template
        actions = ['Launch Test Instances', 'Launch Cutover Instances', 'Validate Launch Template']
        if action.strip() not in actions:
            return
        # Enable multithreading
        processes = []
        manager = multiprocessing.Manager()
        status_list = manager.list()
        return_dict = manager.dict()
        total_servers_count = 0
        max_threads = 30

        # Update all servers that have a dedicated host with the total capacity required for the complete wave for the same host and instance type.
        # This is to ensure that we know straight away that we will not have capacity to complete the migration.
        # Needs to be performed here to take into account dedicated hosts shared across accounts.
        # To be done: We need to make this check more complex in future to include ensuring that a host supporting multiple instance types is calculated correctly. Example if the same host has capacity for 1 large and 2 small and we migrate 1 large and 1 small this is not detected until we try to launch them.
        populate_dedicated_host_requirements(factoryservers)

        for account in factoryservers:
            # Get total number of servers in each account
            total_servers_count = total_servers_count + len(account['servers'])
            # Assume role in the target account
            target_account_creds = lambda_mgn_utils.assume_role(str(account['aws_accountid']),
                                                                str(account['aws_region']))

            print("####################################################################################")
            print(
                "### Multithread processing Template, in Account: " + account['aws_accountid'] + ", Region: " + account[
                    'aws_region'] + " ###")
            print("####################################################################################")

            # Splitting the list into smaller chunks, max 30 chunks
            chunk_size = max_threads
            if len(account['servers']) < max_threads:
                chunk_size = len(account['servers'])
            for serverlist in lambda_mgn_utils.chunks(
                account['servers'], chunk_size):
                print(serverlist)
                p = multiprocessing.Process(target=multiprocessing_update, args=(
                    serverlist, target_account_creds, account['aws_region'], action, return_dict, status_list))
                processes.append(p)
                p.start()

        # Waiting for all processes to finish
        for process in processes:
            process.join()
        final_status = 0
        for item in status_list:
            final_status += item
        print("")

        # Check if any errors in the updating process
        error_result = check_errors(return_dict, action, final_status, total_servers_count)
        return error_result

    except Exception as error:
        error_message = lambda_mgn_utils.handle_error(
            error, "ERROR: UpdateLaunchTemplate:", "", True)
        return error_message


def check_server_os_family(factoryserver, server_has_error, return_dict):
    if 'server_os_family' in factoryserver:
        if factoryserver['server_os_family'].lower().strip() != 'windows' and factoryserver[
            'server_os_family'].lower().strip() != 'linux':
            server_has_error = True
            msg = "ERROR: server_os_family only supports Windows or Linux."
            add_server_validation_error(factoryserver, return_dict, msg)
    else:
        server_has_error = True
        msg = "ERROR: server_os_family does not exist for server."

        pid_message = lambda_mgn_utils.build_pid_message(False, f"- {msg}")

        log.error(pid_message)
        add_server_validation_error(factoryserver, return_dict, msg)

    return server_has_error


def verify_iam_instance_profile(factoryserver, iam_client, server_has_error,
                                return_dict, validated_count, action,
                                new_launch_template, launch_template_data_latest,
                                mgn_client, ec2_client, launch_template_latest_ver,
                                rg_client, license_client):
    verify_instance_profile = []
    if 'iamRole' in factoryserver:
        verify_instance_profile = iam_client.get_instance_profile(
            InstanceProfileName=factoryserver['iamRole'])

    if server_has_error:
        print(
            factoryserver['server_name'] + " : Validation errors occurred skipping update of launch template.")
    else:
        create_template = create_launch_template(factoryserver, action, new_launch_template,
                                                 launch_template_data_latest, mgn_client, ec2_client,
                                                 verify_instance_profile, launch_template_latest_ver,
                                                 rg_client, license_client)

        if create_template is not None and "ERROR" in create_template:
            add_server_validation_error(factoryserver, return_dict, create_template)
        else:
            validated_count = validated_count + 1

    return validated_count


def multiprocessing_update(serverlist, creds, region, action, return_dict, status_list):
    ec2_client = None
    iam_client = None
    mgn_client = None
    rg_client = None
    license_client = None

    try:
        target_account_session = lambda_mgn_utils.get_session(creds, region)
        ec2_client = target_account_session.client('ec2', region)
        iam_client = target_account_session.client('iam')
        mgn_client = target_account_session.client("mgn", region)
        rg_client = target_account_session.client('resource-groups')
        license_client = target_account_session.client('license-manager')

    except Exception as error:
        add_error(return_dict, error, "target account boto sessions")

    validated_count = 0

    for factoryserver in serverlist:
        try:
            server_has_error = False
            # Get Launch template latest version and data
            launch_template_latest_ver = \
                ec2_client.describe_launch_templates(LaunchTemplateIds=[factoryserver['launch_template_id']])[
                    'LaunchTemplates'][0]['LatestVersionNumber']
            launch_template_data_latest = \
                ec2_client.describe_launch_template_versions(LaunchTemplateId=factoryserver['launch_template_id'],
                                                             Versions=[str(launch_template_latest_ver)])[
                    'LaunchTemplateVersions'][0]['LaunchTemplateData']
            new_launch_template = \
                ec2_client.describe_launch_template_versions(LaunchTemplateId=factoryserver['launch_template_id'],
                                                             Versions=[str(launch_template_latest_ver)])[
                    'LaunchTemplateVersions'][0]['LaunchTemplateData']

            # Validate networking settings
            if not validate_server_networking_settings(ec2_client, factoryserver, 'network_interface_id',
                                                       'securitygroup_IDs', 'subnet_IDs', 'Live',
                                                       return_dict) and not server_has_error:
                server_has_error = True

            if not validate_server_networking_settings(ec2_client, factoryserver, 'network_interface_id_test',
                                                       'securitygroup_IDs_test', 'subnet_IDs_test', 'Test',
                                                       return_dict) and not server_has_error:
                server_has_error = True

            # Check server OS family is supported
            server_has_error = check_server_os_family(
                factoryserver, server_has_error, return_dict)

            # Verify Instance type
            if 'instanceType' in factoryserver:
                ec2_client.describe_instance_types(InstanceTypes=[factoryserver['instanceType']])
                mgn_client.update_launch_configuration(targetInstanceTypeRightSizingMethod='NONE',
                                                       sourceServerID=factoryserver['source_server_id'])
            else:
                mgn_client.update_launch_configuration(targetInstanceTypeRightSizingMethod='BASIC',
                                                       sourceServerID=factoryserver['source_server_id'])

            # Verify IAM instance profile
            validated_count = verify_iam_instance_profile(
                factoryserver, iam_client, server_has_error, return_dict, validated_count,
                action, new_launch_template, launch_template_data_latest, mgn_client,
                ec2_client, launch_template_latest_ver, rg_client, license_client)

        except Exception as error:
            add_server_validation_error(factoryserver, return_dict, error, "unhandled")

    status_list.append(validated_count)


def get_dedicated_host_capacity(factoryserver, dedicated_host_capacity):
    if factoryserver.get('dedicated_host_id'):
        if factoryserver['dedicated_host_id'] + ';' + factoryserver[
            'instanceType'] in dedicated_host_capacity:
            dedicated_host_capacity[
                factoryserver['dedicated_host_id'] + ';' + factoryserver['instanceType']] += 1
        else:
            dedicated_host_capacity[
                factoryserver['dedicated_host_id'] + ';' + factoryserver['instanceType']] = 1
    elif factoryserver.get('host_resource_group_arn'):
        if factoryserver['host_resource_group_arn'] + ';' + factoryserver[
            'instanceType'] in dedicated_host_capacity:
            dedicated_host_capacity[
                factoryserver['host_resource_group_arn'] + ';' + factoryserver['instanceType']] += 1
        else:
            dedicated_host_capacity[
                factoryserver['host_resource_group_arn'] + ';' + factoryserver['instanceType']] = 1

    return dedicated_host_capacity


# reviews MF serverlist and returns dict with all dedicated instances with instance types required for servers.
def get_dedicated_host_requirements(serverlist):
    dedicated_host_capacity = {}

    # Build list of dedicated host requirements.
    for factoryserver in serverlist:
        # Check update total dedicated host capacity requirements.
        if 'tenancy' in factoryserver and \
            factoryserver["tenancy"].lower() == DEDICATED_HOST_STRING and \
            'instanceType' in factoryserver:
            dedicated_host_capacity = get_dedicated_host_capacity(
                factoryserver, dedicated_host_capacity)

    return dedicated_host_capacity


def get_all_accounts_dedicated_hosts(accounts):
    all_accounts_dedicated_hosts = {}

    for account in accounts:
        # Build list of dedicated host requirements for the account.
        dedicated_host_capacity = get_dedicated_host_requirements(account['servers'])
        for dedicated_host, instance_capacity in dedicated_host_capacity.items():
            if dedicated_host in all_accounts_dedicated_hosts:
                # Add to total capacity required.
                all_accounts_dedicated_hosts[dedicated_host] += instance_capacity
            else:
                # Not already included so add.
                all_accounts_dedicated_hosts[dedicated_host] = instance_capacity

    return all_accounts_dedicated_hosts


def update_server_capacity_requirements(factoryserver, all_accounts_dedicated_hosts):
    if factoryserver.get('dedicated_host_id'):
        if factoryserver['dedicated_host_id'] + ';' + factoryserver[
            'instanceType'] in all_accounts_dedicated_hosts:
            # Update server with total capacity required for this dedicated host and type for the server list.
            # This means that during the check we validate against the total capacity requirements each time rather than individual server.
            factoryserver['dedicated_host_required_capacity'] = all_accounts_dedicated_hosts[
                factoryserver['dedicated_host_id'] + ';' + factoryserver['instanceType']]
    elif factoryserver.get('host_resource_group_arn'):
        if factoryserver['host_resource_group_arn'] + ';' + factoryserver[
            'instanceType'] in all_accounts_dedicated_hosts:
            # Update server with total capacity required for this dedicated host and type for the server list.
            # This means that during the check we validate against the total capacity requirements each time rather than individual server.
            factoryserver['dedicated_host_required_capacity'] = all_accounts_dedicated_hosts[
                factoryserver['host_resource_group_arn'] + ';' + factoryserver['instanceType']]

    return factoryserver


def populate_dedicated_host_requirements(accounts):
    try:

        # First we need to loop all accounts to gather requirements total.
        # This is needed to as we need to check if a dedicated host is shared across account we factor this into the calculation.
        all_accounts_dedicated_hosts = get_all_accounts_dedicated_hosts(accounts)

        # Once we have the dedicated host requirements for all accounts we can now update the capacity requirements on each server.
        for account in accounts:
            for factoryserver in account['servers']:
                # Check update total dedicated host capacity requirements.
                if 'tenancy' in factoryserver and \
                    factoryserver["tenancy"].lower() == DEDICATED_HOST_STRING and \
                    'instanceType' in factoryserver:
                    factoryserver = update_server_capacity_requirements(
                        factoryserver, all_accounts_dedicated_hosts)

        log.info(f'Dedicated host requirements for wave: {all_accounts_dedicated_hosts}')

        return
    except Exception as error:
        pid_message = lambda_mgn_utils.build_pid_message(True, str(error))
        log.error(pid_message)
        return "ERROR: " + str(error)


def check_instance_capacity(dedicated_hosts, requested_instance_type,
                            requested_capacity, dedicated_host_id):
    available_capacity = dedicated_hosts['Hosts'][0]['AvailableCapacity']['AvailableInstanceCapacity']
    for instance_capacity in available_capacity:
        if instance_capacity['InstanceType'] == requested_instance_type:
            if instance_capacity['AvailableCapacity'] >= requested_capacity:
                return 'SUCCESS: Host Id: ' + dedicated_host_id + ' available capacity of instance type ' + requested_instance_type + ' (Available=' + str(
                    instance_capacity['AvailableCapacity']) + ', Total Requested=' + str(
                    requested_capacity) + ').'
            else:
                return 'ERROR: Host Id: ' + dedicated_host_id + ' does not have available capacity of instance type ' + requested_instance_type + ' (Available=' + str(
                    instance_capacity['AvailableCapacity']) + ', Total Requested for Wave=' + str(
                    requested_capacity) + ').'


# Verify that the provided dedicated host ID exists and that the instance type is supported.
def verify_dedicated_host(ec2_client, dedicated_host_id, requested_instance_type, requested_capacity):
    try:

        dedicated_hosts = ec2_client.describe_hosts(HostIds=[dedicated_host_id])

        if dedicated_hosts.get('Hosts'):
            # Check that the instance type is matching this dedicated host.
            instance_family = dedicated_hosts['Hosts'][0]['HostProperties']['InstanceFamily']
            if requested_instance_type.split(".")[0] != instance_family:
                return 'ERROR: Host Supported Instance Family does not match required (Host=' + instance_family + ', Requested=' + \
                    requested_instance_type.split(".")[0] + ')'

            # Check that capacity is currently available for this instance type.
            message = check_instance_capacity(dedicated_hosts, requested_instance_type,
                                              requested_capacity, dedicated_host_id)
            return message
        else:
            return f'ERROR: Dedicated Host Id ({dedicated_host_id}) not found.'
    except Exception as error:
        error_message = lambda_mgn_utils.handle_error_with_pid(error, "")
        return error_message


def update_disk_type(factoryserver, new_launch_template):
    ebs_volume_type = "gp3"
    if 'ebs_volume_type' in factoryserver:
        ebs_volume_type = factoryserver['ebs_volume_type']

    ebs_iops = 3000
    if 'ebs_iops' in factoryserver:
        ebs_iops = factoryserver['ebs_iops']

    ebs_throughput = 125
    if 'ebs_throughput' in factoryserver:
        ebs_throughput = factoryserver['ebs_throughput']

    ebs_encrypted = False
    if 'ebs_encrypted' in factoryserver:
        ebs_encrypted = factoryserver['ebs_encrypted']
        if 'ebs_kms_key_id' in factoryserver:
            ebs_kms_key_id = factoryserver['ebs_kms_key_id']
        else:
            ebs_kms_key_id = ""  # replace with default key id if required.

    for blockdevice in new_launch_template['BlockDeviceMappings']:
        blockdevice['Ebs']['VolumeType'] = ebs_volume_type
        blockdevice['Ebs']['Iops'] = int(ebs_iops)
        blockdevice['Ebs']['Throughput'] = int(ebs_throughput)
        if ebs_encrypted:
            blockdevice['Ebs']['Encrypted'] = ebs_encrypted
            blockdevice['Ebs']['KmsKeyId'] = ebs_kms_key_id
        elif 'Encrypted' in blockdevice['Ebs']:
            blockdevice['Ebs']['Encrypted'] = False
            blockdevice['Ebs']['KmsKeyId'] = ''

    return new_launch_template


def update_metadata_options(factoryserver, metadata_options,
                            factory_server_tag, metadata_tag,
                            tag_value_1, tag_value_2):
    if factoryserver.get(factory_server_tag):
        metadata_options[metadata_tag] = tag_value_1
    else:
        metadata_options[metadata_tag] = tag_value_2

    return metadata_options


def update_http_put_response_hop_limit(factoryserver, metadata_options):
    if 'instance_metadata_options_http_hop_limit' in factoryserver:
        try:
            metadata_options['HttpPutResponseHopLimit'] = int(
                factoryserver['instance_metadata_options_http_hop_limit'])
        except ValueError:
            # incorrect value entered, needs to be int.
            metadata_options['HttpPutResponseHopLimit'] = 1
    return metadata_options


def update_template(new_launch_template, metadata_options, factoryserver):
    # Update metadata options
    if metadata_options:
        new_launch_template['MetadataOptions'] = metadata_options

    # Enable EBS Optimization
    if 'ebs_optimized' in factoryserver:
        new_launch_template['EbsOptimized'] = factoryserver['ebs_optimized']

    # update instance type
    if 'instanceType' in factoryserver:
        new_launch_template['InstanceType'] = factoryserver['instanceType']

    return new_launch_template


def check_eni(factoryserver, mgn_client, live_eni_used, test_eni_used):
    # This is live ENI
    if factoryserver.get('network_interface_id'):
        live_eni_used = True

    #  This is testing ENI
    if factoryserver.get('network_interface_id_test'):
        test_eni_used = True

    if factoryserver.get('server_boot_mode_uefi'):
        mgn_client.update_launch_configuration(
            bootMode='UEFI',
            sourceServerID=factoryserver['source_server_id'])
    else:
        mgn_client.update_launch_configuration(
            bootMode='LEGACY_BIOS',
            sourceServerID=factoryserver['source_server_id'])

    return live_eni_used, test_eni_used


def verify_host(factoryserver, p_tenancy, ec2_client, rg_client, pid_message):
    if factoryserver.get('dedicated_host_id'):
        if 'instanceType' in factoryserver:
            return_message = verify_dedicated_host(
                ec2_client, factoryserver['dedicated_host_id'],
                factoryserver['instanceType'],
                factoryserver['dedicated_host_required_capacity'])
            if not return_message.startswith('ERROR'):
                p_tenancy['HostId'] = factoryserver['dedicated_host_id']
            else:
                log.error(f"{pid_message}{return_message}")
                return factoryserver['server_name'] + ' - ' + return_message, p_tenancy
        else:
            msg = "ERROR: Instance Type is required if specifying dedicated host ID."
            log.error(f"{pid_message}{msg}")
            return msg, p_tenancy
    elif factoryserver.get('host_resource_group_arn'):
        return_message = verify_host_resource_group_resources(rg_client, factoryserver['host_resource_group_arn'])
        if not return_message.startswith('ERROR'):
            p_tenancy['HostResourceGroupArn'] = factoryserver['host_resource_group_arn']
        else:
            log.error(f"{pid_message}{return_message}")
            return factoryserver['server_name'] + ' - ' + return_message, p_tenancy
    elif factoryserver.get('license_configuration_arn') is None or \
        factoryserver.get('license_configuration_arn') == '':
        msg = "ERROR: Dedicated host ID, Host Resource Group ARN or License Configuration ARN is required if specifying tenancy as dedicated host."
        log.error(f"{pid_message}{msg}")
        return msg, p_tenancy

    return None, p_tenancy


def update_tenancy(factoryserver, ec2_client, mgn_client, rg_client, pid_message_prefix):
    p_tenancy = {}

    if 'tenancy' in factoryserver:
        license_mgn = {}
        if factoryserver["tenancy"].lower() == "dedicated":
            p_tenancy['Tenancy'] = 'dedicated'
            license_mgn = {'osByol': False}
        elif factoryserver["tenancy"].lower() == DEDICATED_HOST_STRING:
            p_tenancy['Tenancy'] = 'host'
            license_mgn = {'osByol': True}
            pid_message = f"{pid_message_prefix}{factoryserver['server_name']}:"
            msg, p_tenancy = verify_host(factoryserver, p_tenancy, ec2_client,
                                         rg_client, pid_message)
            if msg is not None:
                return msg
        else:  # Default is always shared and license provided.
            p_tenancy['Tenancy'] = 'default'
            license_mgn = {'osByol': False}

        if factoryserver['server_os_family'].lower() == 'linux':
            license_mgn = {'osByol': True}

        mgn_client.update_launch_configuration(
            licensing=license_mgn, sourceServerID=factoryserver['source_server_id'])
    else:
        p_tenancy['Tenancy'] = 'default'

    return p_tenancy


def update_instance_profile(verify_instance_profile, new_launch_template):
    if len(verify_instance_profile) > 0:
        instance_profile_name = {}
        instance_profile_name['Arn'] = verify_instance_profile['InstanceProfile']['Arn']
        new_launch_template['IamInstanceProfile'] = instance_profile_name
    return new_launch_template


def update_license_specifications(factoryserver, license_client,
                                  new_launch_template, pid_message_prefix):
    if factoryserver.get('license_configuration_arn'):
        return_message = verify_license_configuration(
            license_client, factoryserver['license_configuration_arn'])
        if not return_message.startswith('ERROR'):
            new_launch_template['LicenseSpecifications'] = [
                {
                    'LicenseConfigurationArn': factoryserver.get('license_configuration_arn')
                },
            ]
        else:
            log.error(f"{pid_message_prefix}{return_message}")
            return factoryserver['server_name'] + ' - ' + return_message, new_launch_template

    return None, new_launch_template


def update_termination_protection(factoryserver, new_launch_template,
                                  termination_tag_name):
    if termination_tag_name in factoryserver:
        new_launch_template['DisableApiTermination'] = \
            factoryserver[termination_tag_name]
    else:
        if 'DisableApiTermination' in new_launch_template:
            del new_launch_template['DisableApiTermination']

    return new_launch_template


def update_launch_template_for_test_instance(
    factoryserver, new_launch_template, pid_message_prefix,
    ec2_client, launch_template_latest_ver):
    # update tags into template
    add_tags_to_launch_template(factoryserver, new_launch_template, 'test')

    # Update termination protection
    new_launch_template = update_termination_protection(
        factoryserver, new_launch_template, 'termination_protection_test')

    add_network_interfaces_to_launch_template(factoryserver, new_launch_template, True)

    log.info(f"{pid_message_prefix}*** Create New Test Launch Template data: ***")
    print(new_launch_template)
    new_template = ec2_client.create_launch_template_version(
        LaunchTemplateId=factoryserver['launch_template_id'],
        SourceVersion=str(launch_template_latest_ver),
        LaunchTemplateData=new_launch_template)
    new_template_ver = new_template['LaunchTemplateVersion']['VersionNumber']
    if new_template['ResponseMetadata']['HTTPStatusCode'] != 200:
        msg = "ERROR: Update Failed - Test Launch Template for server: " + factoryserver['server_name']
        log.error(f"{pid_message_prefix}{msg}")
        return msg, new_launch_template
    else:
        msg = "Update SUCCESS: Test Launch template updated for server: " + factoryserver['server_name']
        log.info(f"{pid_message_prefix}{msg}")
    log.info(f"{pid_message_prefix}Test Template updated, the latest version is: {str(new_template_ver)}")
    ec2_client.modify_launch_template(
        LaunchTemplateId=factoryserver['launch_template_id'],
        DefaultVersion=str(new_template_ver))


def update_launch_template_for_cutover_instance(
    factoryserver, new_launch_template, pid_message_prefix,
    ec2_client, launch_template_latest_ver):
    # update tags into template
    add_tags_to_launch_template(factoryserver, new_launch_template, 'live')

    # Update termination protection
    new_launch_template = update_termination_protection(
        factoryserver, new_launch_template, 'termination_protection')

    add_network_interfaces_to_launch_template(factoryserver, new_launch_template, False)

    log.info(f"{pid_message_prefix}*** Create New Cutover Launch Template data: ***")
    print(new_launch_template)
    new_template = ec2_client.create_launch_template_version(
        LaunchTemplateId=factoryserver['launch_template_id'],
        SourceVersion=str(launch_template_latest_ver),
        LaunchTemplateData=new_launch_template)
    new_template_ver = new_template['LaunchTemplateVersion']['VersionNumber']
    if new_template['ResponseMetadata']['HTTPStatusCode'] != 200:
        msg = "ERROR: Update Failed - Cutover Launch Template for server: " + factoryserver['server_name']
        log.error(f"{pid_message_prefix}{msg}")
        return msg
    else:
        msg = "Update SUCCESS: Cutover Launch template updated for server: " + factoryserver['server_name']
        log.info(f"{pid_message_prefix}{msg}")
    log.info(f"{pid_message_prefix}Cutover Template updated, the latest version is: {str(new_template_ver)}")
    ec2_client.modify_launch_template(LaunchTemplateId=factoryserver['launch_template_id'],
                                      DefaultVersion=str(new_template_ver))


def check_eni_sg_combination(eni_used, is_live_eni_used, factoryserver,
                             pid_message_prefix, status):
    this_status = status
    eni_type = "Test"
    sg_id_tag = "securitygroup_IDs_test"
    subnet_id_tag = "subnet_IDs_test"
    if is_live_eni_used:
        eni_type = "Live"
        sg_id_tag = "securitygroup_IDs"
        subnet_id_tag = "subnet_IDs"

    if eni_used and (
        (factoryserver.get(sg_id_tag) and factoryserver[sg_id_tag][0] != '') or
            (subnet_id_tag in factoryserver and factoryserver[subnet_id_tag][0] != '')):
        # user has specified both ENI and SGs but this is not a valid combination.
        this_status = False
        msg = (f"ERROR: Validation failed - Specifying {eni_type} ENI and also {eni_type} "
               f"Security Group or Subnet is not supported. ENIs will inherit the SGs and Subnet of the ENI: {factoryserver['server_name']}")
        log.error(f"{pid_message_prefix}{msg}")
        return msg, this_status

    return None, this_status


def modify_template(is_cutover, pid_message_prefix, new_launch_template,
                    factoryserver, template_ver, ec2_client):
    eni_type = "Test"
    if is_cutover:
        eni_type = 'Cutover'

    log.info(f"{pid_message_prefix}*** Validate New {eni_type} Launch Template data: ***")
    print(new_launch_template)
    new_template = ec2_client.create_launch_template_version(
        LaunchTemplateId=factoryserver['launch_template_id'],
        SourceVersion=str(template_ver),
        LaunchTemplateData=new_launch_template)
    new_template_ver = new_template['LaunchTemplateVersion']['VersionNumber']
    log.info(f"{pid_message_prefix}{eni_type} Template updated, the latest version is: {str(new_template_ver)}")
    if new_template['ResponseMetadata']['HTTPStatusCode'] != 200:
        status = False
        msg = f"ERROR: Validation failed - {eni_type} Launch Template data for server: " + factoryserver[
            'server_name']
        log.error(f"{pid_message_prefix}{msg}")
        return msg, status, new_template_ver
    else:
        msg = f"SUCCESS: {eni_type} Launch template validated for server: " + factoryserver['server_name']
        log.info(f"{pid_message_prefix}{msg}")
        status = True

    ec2_client.modify_launch_template(
        LaunchTemplateId=factoryserver['launch_template_id'],
        DefaultVersion=str(new_template_ver))

    return None, status, new_template_ver


def revert_template(ec2_client, factoryserver, new_template_ver_cutover,
                    launch_template_data_latest, pid_message_prefix):
    latest_template = ec2_client.create_launch_template_version(
        LaunchTemplateId=factoryserver['launch_template_id'],
        SourceVersion=str(new_template_ver_cutover),
        LaunchTemplateData=launch_template_data_latest)
    latest_template_ver = latest_template['LaunchTemplateVersion']['VersionNumber']
    log.info("Pid: " + str(
        os.getpid()) + " - Template reverted back after validation, the latest version is: " + str(
        latest_template_ver))
    if latest_template['ResponseMetadata']['HTTPStatusCode'] != 200:
        status = False
        msg = "ERROR: Revert to old version failed for server: " + factoryserver['server_name']
        log.error(f"{pid_message_prefix}{msg}")
        return msg
    else:
        status = True

    ec2_client.modify_launch_template(
        LaunchTemplateId=factoryserver['launch_template_id'],
        DefaultVersion=str(latest_template_ver))

    msg = "SUCCESS: All Launch templates validated for server: " + factoryserver['server_name']
    if status == False:
        msg = "ERROR: Launch template validation failed for server: " + factoryserver['server_name']
    log.info(f"{pid_message_prefix}{msg}")
    return msg


def update_launch_template_for_test_and_cutover_instances(
    factoryserver, new_launch_template, pid_message_prefix,
    ec2_client, launch_template_latest_ver, test_eni_used,
    live_eni_used, launch_template_data_latest):
    status = False

    # update tags into template
    add_tags_to_launch_template(factoryserver, new_launch_template, 'test')

    # Update termination protection
    new_launch_template = update_termination_protection(
        factoryserver, new_launch_template, 'termination_protection_test')

    # Validate that the server does not have both ENI and Subnet specified.
    msg, status = check_eni_sg_combination(test_eni_used, False, factoryserver,
                                           pid_message_prefix, status)
    if msg is not None:
        return msg

    add_network_interfaces_to_launch_template(factoryserver, new_launch_template, True)

    msg, status, new_template_ver_test = modify_template(
        False, pid_message_prefix, new_launch_template, factoryserver,
        launch_template_latest_ver, ec2_client)
    if msg is not None:
        return msg

    # update tags into template
    add_tags_to_launch_template(factoryserver, new_launch_template, 'live')

    ## Update termination protection
    new_launch_template = update_termination_protection(
        factoryserver, new_launch_template, 'termination_protection')

    msg, status = check_eni_sg_combination(live_eni_used, True, factoryserver,
                                           pid_message_prefix, status)
    if msg is not None:
        return msg

    add_network_interfaces_to_launch_template(factoryserver, new_launch_template, False)

    msg, status, new_template_ver_cutover = modify_template(
        True, pid_message_prefix, new_launch_template, factoryserver,
        new_template_ver_test, ec2_client)
    if msg is not None:
        return msg

    ### Revert Launch template back to old version
    msg = revert_template(ec2_client, factoryserver, new_template_ver_cutover,
                          launch_template_data_latest, pid_message_prefix)
    return msg


def create_launch_template(factoryserver, action, new_launch_template, launch_template_data_latest,
                           mgn_client, ec2_client, verify_instance_profile, launch_template_latest_ver,
                           rg_client, license_client):
    test_eni_used = False
    live_eni_used = False

    try:
        # Update Launch template
        # The following attributes are optional in CMF if these additional settings are needing to be set per server
        # the follow attribute needs to be creating in the server schema:
        # ebs_volume_type as string
        # ebs_throughput as string
        # ebs_iops as string
        # ebs_encrypted as checkbox
        # ebs_kms_key_id as string
        # termination_protection as checkbox
        # termination_protection_test as checkbox
        # ebs_optimized as checkbox
        # instance_metadata_options_tags as checkbox
        # instance_metadata_options_http_endpoint as checkbox
        # instance_metadata_options_http_v6 as checkbox
        # instance_metadata_options_http_hop_limit as string
        # instance_metadata_options_http_tokens as checkbox
        # tags_live as tag (these are combined with the tags attribute)
        # tags_test as tag (these are combined with the tags attribute)
        # server_boot_mode_uefi as checkbox
        # license_configuration_arn as string
        # host_resource_group_arn as string

        # Update disk type
        new_launch_template = update_disk_type(factoryserver, new_launch_template)

        # Read any metadata options.
        metadata_options = {}
        metadata_options = update_metadata_options(
            factoryserver, metadata_options,
            'instance_metadata_options_tags',
            'InstanceMetadataTags',
            'enabled', 'disabled')

        metadata_options = update_metadata_options(
            factoryserver, metadata_options,
            'instance_metadata_options_http_endpoint',
            'HttpEndpoint',
            'enabled', 'disabled')

        metadata_options = update_metadata_options(
            factoryserver, metadata_options,
            'instance_metadata_options_http_v6',
            'HttpProtocolIpv6',
            'enabled', 'disabled')

        metadata_options = update_http_put_response_hop_limit(
            factoryserver, metadata_options)

        metadata_options = update_metadata_options(
            factoryserver, metadata_options,
            'instance_metadata_options_http_tokens',
            'HttpTokens',
            'required', 'optional')

        # Update metadata options, EBS optimization,
        # and instance type in new launch template
        new_launch_template = update_template(
            new_launch_template, metadata_options, factoryserver)

        # check if ENIs provided for test or live
        live_eni_used, test_eni_used = check_eni(factoryserver, mgn_client,
                                                 live_eni_used, test_eni_used)

        # update tenancy
        pid_message_prefix = lambda_mgn_utils.build_pid_message(False, " - ")
        new_launch_template['Placement'] = update_tenancy(
            factoryserver, ec2_client, mgn_client, rg_client, pid_message_prefix)

        # update instance profile
        new_launch_template = update_instance_profile(
            verify_instance_profile, new_launch_template)

        # update license specifications
        msg, new_launch_template = update_license_specifications(
            factoryserver, license_client, new_launch_template, pid_message_prefix)
        if msg is not None:
            return msg

        ## Update Launch template with Test SG and subnet
        if action.strip() == "Launch Test Instances":
            msg = update_launch_template_for_test_instance(
                factoryserver, new_launch_template, pid_message_prefix,
                ec2_client, launch_template_latest_ver)
            return msg

        # Update Launch template with Cutover SG and subnet
        elif action.strip() == "Launch Cutover Instances":
            msg = update_launch_template_for_cutover_instance(
                factoryserver, new_launch_template, pid_message_prefix,
                ec2_client, launch_template_latest_ver)
            return msg

        ## Validating Launch template with both test and cutover info
        elif action.strip() == "Validate Launch Template":
            msg = update_launch_template_for_test_and_cutover_instances(
                factoryserver, new_launch_template, pid_message_prefix,
                ec2_client, launch_template_latest_ver, test_eni_used,
                live_eni_used, launch_template_data_latest)
            return msg

    except Exception as error:
        message_suffix = ""
        if ":" in str(error):
            message_suffix = f" full:  {str(error)})"
        error_message = lambda_mgn_utils.handle_error_with_pid(error, message_suffix)
        return error_message


def add_tags_to_launch_template(factory_server, new_launch_template, additional_tags=None):
    base_tags_key = 'tags'
    factory_server_all_tags = []

    pid_message_prefix = lambda_mgn_utils.build_pid_message(False, " - ")
    pid_message_suffix = f" on server: {factory_server['server_name']}"

    # Add base tags to be added.
    if base_tags_key in factory_server:
        factory_server_all_tags.extend(factory_server[base_tags_key])

    if additional_tags is not None:
        cmf_tags_key = 'tags_' + additional_tags
        if cmf_tags_key in factory_server:
            factory_server_all_tags.extend(factory_server[cmf_tags_key])

    # clear existing tags in template except AWS automatic tags.
    for tags in new_launch_template['TagSpecifications']:
        if tags['ResourceType'] == 'instance' or tags['ResourceType'] == 'volume':
            remaining_tags = []
            for tag in tags['Tags']:
                log.debug(f"{pid_message_prefix}checking tag {tag['Key']}{pid_message_suffix}")
                if tag['Key'].lower().startswith('aws') or tag['Key'].lower() == 'name':
                    # Removed tag as it is not AWS provided or called name
                    log.debug(f"{pid_message_prefix}keeping tag {tag['Key']}{pid_message_suffix}")
                    remaining_tags.append(tag)
            tags['Tags'] = remaining_tags

    # add tags to template Tags
    for tags in new_launch_template['TagSpecifications']:
        if tags['ResourceType'] == 'instance' or tags['ResourceType'] == 'volume':
            for item in factory_server_all_tags:
                if 'key' in item:
                    item['Key'] = item['key']
                    del item['key']
                if 'value' in item:
                    item['Value'] = item['value']
                    del item['value']
                log.debug(f"{pid_message_prefix}checking tag: {item['Value']}{pid_message_suffix}")
                tag_exist = False
                for tag in tags['Tags']:
                    if item['Key'].lower() == tag['Key'].lower():
                        tag['Value'] = item['Value']
                        tag_exist = True
                        log.info(
                            f"{pid_message_prefix}Replaced existing value for tag: {tag['Key']}{pid_message_suffix}")
                if tag_exist == False:
                    tags['Tags'].append(item)


def add_network_interfaces_to_launch_template(factory_server, new_launch_template, use_test_nic_configuration=False):
    eni_used = False
    test_attribute_suffix = ''

    if use_test_nic_configuration:
        test_attribute_suffix = '_test'

    # check if ENIs provided
    network_interface_id_str = 'network_interface_id' + test_attribute_suffix
    if factory_server.get(network_interface_id_str):
        eni_used = True

    if eni_used:
        # update ENI if provided, removes other interfaces and replaces with ENI provided, this will use subnet and SGs defined for ENI.
        update_launch_template_network_interfaces_eni(
            new_launch_template, factory_server[network_interface_id_str])
    else:
        # Update network interfaces with subnet, security groups and private IP addresses if specified.
        update_launch_template_network_interfaces_no_eni(
            factory_server, new_launch_template, test_attribute_suffix)


def update_launch_template_network_interfaces_eni(launch_template, network_interface_id):
    network_interfaces = []
    network_interface = {'NetworkInterfaceId': network_interface_id,
                         'DeviceIndex': 0}
    network_interfaces.append(network_interface)
    launch_template['NetworkInterfaces'] = network_interfaces


def update_launch_template_network_interfaces_no_eni(factory_server, launch_template, test_attribute_suffix=''):
    for nic in launch_template['NetworkInterfaces']:
        # Update private IP address if specified.
        if factory_server.get('private_ip' + test_attribute_suffix) is not None and factory_server[
            'private_ip' + test_attribute_suffix].strip() != '':
            ipaddrs = []
            ip = {'Primary': True, 'PrivateIpAddress': factory_server['private_ip' + test_attribute_suffix]}
            ipaddrs.append(ip)
            nic['PrivateIpAddresses'] = ipaddrs
        else:
            if 'PrivateIpAddresses' in nic:
                del nic['PrivateIpAddresses']

        # Update Subnet Id and security group Ids if no ENI provided.
        nic['Groups'] = factory_server['securitygroup_IDs' + test_attribute_suffix]
        nic['SubnetId'] = factory_server['subnet_IDs' + test_attribute_suffix][0]


def get_host_resource_group_resources(rg_client, host_resource_group_arn):
    resources = []
    paginator = rg_client.get_paginator('list_group_resources')
    page_iterator = paginator.paginate(
        Group=host_resource_group_arn,
        Filters=[
            {
                'Name': 'resource-type',
                'Values': [
                    'AWS::EC2::Host',
                ]
            }
        ],
    )
    for page in page_iterator:
        resources.extend(page['Resources'])
    return resources


def verify_host_resource_group_resources(rg_client, host_resource_group_arn):
    try:
        resources = get_host_resource_group_resources(rg_client, host_resource_group_arn)
    except rg_client.exceptions.NotFoundException:
        return f'ERROR: Host Resource Group ARN ({host_resource_group_arn}) not found.'

    if len(resources) > 0:
        return f'SUCCESS: Host Resource Group ARN ({host_resource_group_arn}) found and has len(resources) hosts.'

    msg = f'WARNING: Host Resource Group ARN ({host_resource_group_arn}) has no hosts allocated currently.'
    log.warning(msg)

    return msg


def verify_license_configuration(license_client, license_configuration_arn):
    # get license configuration from AWS boto3
    try:
        license_configuration = license_client.get_license_configuration(
            LicenseConfigurationArn=license_configuration_arn)
    except license_client.exceptions.InvalidParameterValueException:
        return f'ERROR: License Configuration ARN ({license_configuration_arn}) not found.'

    log.debug(license_configuration)

    license_configuration_status = license_configuration['Status']
    if license_configuration_status == 'AVAILABLE':
        return f'SUCCESS: License Configuration ARN ({license_configuration_arn}) has license configuration status AVAILABLE.'
    else:
        msg = f'ERROR: License Configuration ARN ({license_configuration_arn}) status not AVAILABLE.'
        log.error(msg)

    return msg
