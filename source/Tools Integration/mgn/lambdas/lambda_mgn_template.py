#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################

from __future__ import print_function
import os
import boto3
import botocore.exceptions
import lambda_mgn
import multiprocessing
import logging
import json

log = logging.getLogger()
log.setLevel(logging.INFO)

def add_server_validation_error(factoryserver, return_dict, error, additional_context = None):

  if additional_context:
    #Append : to message.
    additional_context += ": "
  else:
    #init to null string.
    additional_context = ""

  if ":" in str(error):
      err = ''
      msgs = str(error).split(":")[1:]
      for msg in msgs:
          err = err + msg
      log.error("Pid: " + str(os.getpid()) + " - ERROR: " + factoryserver['server_name'] + ": " + additional_context + err)
      if factoryserver['server_name'] in return_dict:
        # Server has errors already, append additional error.
        mgs_update = return_dict[factoryserver['server_name']]
        mgs_update.append("ERROR: " + additional_context + err)
        return_dict[factoryserver['server_name']] = mgs_update
      else:
        #First error for the server, initialize array of errors for server.
        errors = ["ERROR: " + additional_context + err]
        return_dict[factoryserver['server_name']] = errors
  else:
      log.error("Pid: " + str(os.getpid()) + " - ERROR: " + factoryserver['server_name'] + ": " + additional_context + str(error))
      if factoryserver['server_name'] in return_dict:
        # Server has errors already, append additional error.
        mgs_update = return_dict[factoryserver['server_name']]
        mgs_update.append("ERROR: " + additional_context + str(error))
        return_dict[factoryserver['server_name']] = mgs_update
      else:
        #First error for the server, initialize array of errors for server.
        errors = ["ERROR: " + additional_context + str(error)]
        return_dict[factoryserver['server_name']] = errors

def add_error(return_dict, error, error_type = 'non-specific'):

  if ":" in str(error):
      err = ''
      msgs = str(error).split(":")[1:]
      for msg in msgs:
          err = err + msg
      log.error("Pid: " + str(os.getpid()) + " - ERROR: " + err)
      if error_type in return_dict:
        # error_type record has errors already, append additional error.
        mgs_update = return_dict[error_type]
        mgs_update.append("ERROR: " + err)
        return_dict[error_type] = mgs_update
      else:
        #First error for the type provided, initialize array of errors for type.
        errors = ["ERROR: " + str(error)]
        return_dict[error_type] = errors
  else:
      log.error("Pid: " + str(os.getpid()) + " - ERROR: " + error_type + " - " + str(error))
      if error_type in return_dict:
        # Server has errors already, append additional error.
        mgs_update = return_dict[error_type]
        mgs_update.append("ERROR: " + error_type + " - " + str(error))
        return_dict[error_type] = mgs_update
      else:
        #First error for the server, initialize array of errors for server.
        errors = ["ERROR: " + error_type + " - " + str(error)]
        return_dict[error_type] = errors

def validate_server_networking_settings(ec2_client, factoryserver, network_interface_attr_name, sg_attr_name, subnet_attr_name, type, return_dict):

  server_has_error = False

  print(factoryserver)

  if (network_interface_attr_name in factoryserver and factoryserver[network_interface_attr_name] is not None and factoryserver[network_interface_attr_name] != '')\
    and ((sg_attr_name in factoryserver and (factoryserver[sg_attr_name] is not None and factoryserver[sg_attr_name] != '')) or (subnet_attr_name in factoryserver and (factoryserver[subnet_attr_name] is not None and factoryserver[subnet_attr_name][0] != ''))):
    # user has specified both ENI and SGs but this is not a valid combination.
    msg = "ERROR: Validation failed - Specifying " + type + " ENI and also " + type + " Security Group or Subnet is not supported. ENIs will inherit the SGs and Subnet of the ENI."
    server_has_error = True
    add_server_validation_error(factoryserver, return_dict, msg)
    # Exit and do not validate other settings as invalid configuration and waste of resource time until resolved.
    return False

  # Check if ENI specified.
  if network_interface_attr_name in factoryserver and factoryserver[network_interface_attr_name] is not None and factoryserver[network_interface_attr_name] != '':
    # Check ENI exist
    try:
      verify_eni = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[factoryserver[network_interface_attr_name],])
    except Exception as error:
      # Error validating ENI.
      server_has_error = True
      add_server_validation_error(factoryserver, return_dict, error, type + ' ENI')
      pass
  else:
    # Verify Subnets and SGs.
    if subnet_attr_name in factoryserver:
        if len(factoryserver[subnet_attr_name]) > 0:
            try:
              verify_subnet = ec2_client.describe_subnets(SubnetIds=factoryserver[subnet_attr_name])
              subnet_vpc = verify_subnet['Subnets'][0]['VpcId']
            except Exception as error:
              # Error validating subnet.
              server_has_error = True
              add_server_validation_error(factoryserver, return_dict, error, type +' subnet')
              pass
        else:
            server_has_error = True
            msg = "ERROR: " + subnet_attr_name + " attribute is empty."
            add_server_validation_error(factoryserver, return_dict, msg, type +' subnet')
    else:
        server_has_error = True
        msg = "ERROR: " + subnet_attr_name + " does not exist for server."
        add_server_validation_error(factoryserver, return_dict, msg, type +' subnet')

    if sg_attr_name in factoryserver:
        if len(factoryserver[sg_attr_name]) > 0:
            verify_sgs = {}
            try:
              verify_sgs = ec2_client.describe_security_groups(GroupIds=factoryserver[sg_attr_name])
            except Exception as error:
              # Error validating SGs.
              server_has_error = True
              add_server_validation_error(factoryserver, return_dict, error, type + " security groups")
              pass

            if 'SecurityGroups' in verify_sgs:
              for sg in verify_sgs['SecurityGroups']:
                  if subnet_vpc != sg['VpcId']:
                      server_has_error = True
                      msg = "ERROR: Subnet and Security groups must be in the same VPC: " + verify_subnet['Subnets'][0]['SubnetId'] + ", " + sg['GroupId']
                      add_server_validation_error(factoryserver, return_dict, msg, type + ' security groups')

        else:
            server_has_error = True
            msg = "ERROR: " + sg_attr_name + " attribute is empty."
            add_server_validation_error(factoryserver, return_dict, msg, type + ' security groups')
    else:
        server_has_error = True
        msg = "ERROR: " + sg_attr_name + " does not exist for server: " + factoryserver['server_name']
        add_server_validation_error(factoryserver, return_dict, msg, type + ' security groups')

  return not server_has_error


def update_launch_template(factoryservers, action):
  try:
    # Check if the action is launch servers or validate launch template
    if action.strip() != 'Launch Test Instances' and action.strip() != 'Launch Cutover Instances' and action.strip() != 'Validate Launch Template':
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
    # TODO We need to make this check more complex in future to include ensuring that a host supporting multiple instance types is calculated correctly. Example if the same host has capacity for 1 large and 2 small and we migrate 1 large and 1 small this is not detected until we try to launch them.
    populate_dedicated_host_requirements(factoryservers)

    for account in factoryservers:
        # Get total number of servers in each account
        total_servers_count = total_servers_count + len(account['servers'])
        # Assume role in the target account
        target_account_creds = lambda_mgn.assume_role(str(account['aws_accountid']))

        print("####################################################################################")
        print("### Multithread processing Template, in Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + " ###")
        print("####################################################################################")
        
        # Splitting the list into smaller chunks, max 30 chunks
        if len(account['servers']) < max_threads:
            for serverlist in chunks(account['servers'], len(account['servers'])):
                print(serverlist)
                p = multiprocessing.Process(target=multiprocessing_update, args=(serverlist, target_account_creds, account['aws_region'], action, return_dict, status_list))
                processes.append(p)
                p.start()
        else:
            for serverlist in chunks(account['servers'], max_threads):
                print(serverlist)
                p = multiprocessing.Process(target=multiprocessing_update, args=(serverlist, target_account_creds, account['aws_region'], action, return_dict, status_list))
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
    if len(return_dict.items()) > 0:
        log.error("ERROR: Launch templates validation failed - " + str(len(return_dict.items())) + " servers with errors.")
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

  except Exception as error:
        if ":" in str(error):
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            msg = "ERROR: " + err
            log.error(msg)
            return msg
        else:
            msg = "ERROR: " + str(error)
            log.error(msg)
            return msg

def multiprocessing_update(serverlist, creds, region, action, return_dict, status_list):
  ec2_client = None
  iam_client = None
  mgn_client = None

  try:
    target_account_session = lambda_mgn.get_session(creds, region)
    ec2_client = target_account_session.client('ec2', region)
    iam_client = target_account_session.client('iam')
    mgn_client = target_account_session.client("mgn", region)

  except Exception as error:
    add_error(return_dict, error, "target account boto sessions")

  validated_count = 0

  for factoryserver in serverlist:
    try:
      server_has_error = False
      # Get Launch template latest version and data
      launch_template_latest_ver = ec2_client.describe_launch_templates(LaunchTemplateIds=[factoryserver['launch_template_id']])['LaunchTemplates'][0]['LatestVersionNumber']
      launch_template_data_latest = ec2_client.describe_launch_template_versions(LaunchTemplateId=factoryserver['launch_template_id'], Versions=[str(launch_template_latest_ver)])['LaunchTemplateVersions'][0]['LaunchTemplateData']
      new_launch_template = ec2_client.describe_launch_template_versions(LaunchTemplateId=factoryserver['launch_template_id'], Versions=[str(launch_template_latest_ver)])['LaunchTemplateVersions'][0]['LaunchTemplateData']

      # Verify Launch templates inputs
      subnet_vpc = ""
      subnet_vpc_test = ""

      # Validate networking settings
      if not validate_server_networking_settings(ec2_client, factoryserver, 'network_interface_id', 'securitygroup_IDs', 'subnet_IDs', 'Live', return_dict) and not server_has_error:
        server_has_error = True

      if not validate_server_networking_settings(ec2_client, factoryserver, 'network_interface_id_test', 'securitygroup_IDs_test', 'subnet_IDs_test', 'Test', return_dict) and not server_has_error:
        server_has_error = True

      # Check server OS family is supported
      if 'server_os_family' in factoryserver:
          if factoryserver['server_os_family'].lower().strip() != 'windows' and factoryserver['server_os_family'].lower().strip() != 'linux':
              server_has_error = True
              msg = "ERROR: server_os_family only supports Windows or Linux."
              add_server_validation_error(factoryserver, return_dict, msg)
      else:
          server_has_error = True
          msg = "ERROR: server_os_family does not exist for server."
          log.error("Pid: " + str(os.getpid()) + " - " + msg)
          add_server_validation_error(factoryserver, return_dict, msg)

      # Verify Instance type
      if 'instanceType' in factoryserver:
          verify_instance_type = ec2_client.describe_instance_types(InstanceTypes=[factoryserver['instanceType']])
          mgn_client.update_launch_configuration(targetInstanceTypeRightSizingMethod='NONE', sourceServerID=factoryserver['source_server_id'])
      else:
          mgn_client.update_launch_configuration(targetInstanceTypeRightSizingMethod='BASIC', sourceServerID=factoryserver['source_server_id'])

      # Verify IAM instance profile
      verify_instance_profile = []
      if 'iamRole' in factoryserver:
          verify_instance_profile = iam_client.get_instance_profile(InstanceProfileName=factoryserver['iamRole'])

      if server_has_error:
        print(factoryserver['server_name'] + " : Validation errors occurred skipping update of launch template.")
      else:
          create_template = create_launch_template(factoryserver, action, new_launch_template, launch_template_data_latest, mgn_client, ec2_client, verify_instance_profile, launch_template_latest_ver)

          if create_template is not None and "ERROR" in create_template:
              add_server_validation_error(factoryserver, return_dict, create_template)
          else:
              validated_count = validated_count + 1

    except Exception as error:
      add_server_validation_error(factoryserver, return_dict, error, "unhandled")
      pass

  status_list.append(validated_count)



def check_dedicated_host_wave_capacity(serverlist, creds, region, return_dict):
  try:
    target_account_session = lambda_mgn.get_session(creds, region)
    ec2_client = target_account_session.client('ec2', region)

    return_msg = 'SUCCESS'
    dedicated_host_capacity = get_dedicated_host_wave_requirements(serverlist)

    for dedicated_host, instance_capacity in dedicated_host_capacity.items():
      hostid_instance = dedicated_host.split(';')
      tmp_return = verify_dedicated_host(ec2_client, hostid_instance[0], hostid_instance[1], instance_capacity)
      print(tmp_return)
      if tmp_return[:5] == 'ERROR':
         if return_msg == 'SUCCESS':
          return_msg = tmp_return
          return_dict[dedicated_host] = [tmp_return]
         else:
          return_msg += '; ' + tmp_return
          return_dict[dedicated_host] = [tmp_return]

    return return_msg
  except Exception as error:
    log.error("Pid: " + str(os.getpid()) + " - ERROR: " + str(error))
    return return_msg + " - ERROR: " + str(error)

# reviews MF serverlist and returns dict with all dedicated instances with instance types required for servers.
def get_dedicated_host_requirements(serverlist):

  dedicated_host_capacity = {}

  #   Build list of dedicated host requirements.
  for factoryserver in serverlist:
    #Check update total dedicated host capacity requirements.
    if 'tenancy' in factoryserver:
      if factoryserver["tenancy"].lower() == "dedicated host":
          if 'dedicated_host_id' in factoryserver:
            if 'instanceType' in factoryserver:
              if factoryserver['dedicated_host_id']+ ';' + factoryserver['instanceType'] in dedicated_host_capacity:
                dedicated_host_capacity[factoryserver['dedicated_host_id']+ ';' + factoryserver['instanceType']] += 1
              else:
                dedicated_host_capacity[factoryserver['dedicated_host_id']+ ';' + factoryserver['instanceType']] = 1
  return dedicated_host_capacity

def populate_dedicated_host_requirements(accounts):
  try:

    all_accounts_dedicated_hosts = {}

    # First we need to loop all accounts to gather requirements total.
    # This is needed to as we need to check if a dedicated host is shared across account we factor this into the calculation.
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

    # Once we have the dedicated host requirements for all accounts we can now update the capacity requirements on each server.
    for account in accounts:
      for factoryserver in account['servers']:
        #Check update total dedicated host capacity requirements.
        if 'tenancy' in factoryserver:
          if factoryserver["tenancy"].lower() == "dedicated host":
              if 'dedicated_host_id' in factoryserver:
                if 'instanceType' in factoryserver:
                  if factoryserver['dedicated_host_id']+ ';' + factoryserver['instanceType'] in all_accounts_dedicated_hosts:
                    # Update server with total capacity required for this dedicated host and type for the server list.
                    # This means that during the check we validate against the total capacity requirements each time rather than individual server.
                    factoryserver['dedicated_host_required_capacity'] = all_accounts_dedicated_hosts[factoryserver['dedicated_host_id']+ ';' + factoryserver['instanceType']]

    return
  except Exception as error:
    log.error("Pid: " + str(os.getpid()) + " - ERROR: " + str(error))
    return "ERROR: " + str(error)

# Verify that the provided dedicated host ID exists and that the instance type is supported.
def verify_dedicated_host(ec2_client, dedicated_host_id, requested_instance_type, requested_capacity):
  try:

    dedicated_hosts = ec2_client.describe_hosts(HostIds=[dedicated_host_id])

    if 'Hosts' in dedicated_hosts:
      if len(dedicated_hosts['Hosts']) == 1:
        #Check that the instance type is matching this dedicated host.
        Instance_family = dedicated_hosts['Hosts'][0]['HostProperties']['InstanceFamily']
        if requested_instance_type.split(".")[0] != Instance_family:
          return 'ERROR: Host Supported Instance Family does not match required (Host=' + Instance_family + ', Requested=' + requested_instance_type.split(".")[0] +')'

        #Check that capacity is currently available for this instance type.
        available_capacity = dedicated_hosts['Hosts'][0]['AvailableCapacity']['AvailableInstanceCapacity']
        for instance_capacity in available_capacity:
          if instance_capacity['InstanceType'] == requested_instance_type:
            if instance_capacity['AvailableCapacity'] >= requested_capacity:
              return 'SUCCESS: Host Id: ' + dedicated_host_id + ' available capacity of instance type ' + requested_instance_type + ' (Available=' + str(instance_capacity['AvailableCapacity']) + ', Total Requested=' + str(requested_capacity) + ').'
            else:
              return 'ERROR: Host Id: ' + dedicated_host_id + ' does not have available capacity of instance type ' + requested_instance_type + ' (Available=' + str(instance_capacity['AvailableCapacity']) + ', Total Requested for Wave=' + str(requested_capacity) + ').'
      else:
        return 'ERROR: Host Id not found.'
    else:
      return 'ERROR: Host Id not found.'
  except Exception as error:
    if ":" in str(error):
        err = ''
        msgs = str(error).split(":")[1:]
        for msg in msgs:
            err = err + msg
        log.error("Pid: " + str(os.getpid()) + " - ERROR: " + err)
        return "ERROR: " + err
    else:
        log.error("Pid: " + str(os.getpid()) + " - ERROR: " + str(error))
        return "ERROR: " + str(error)


def create_launch_template(factoryserver, action, new_launch_template, launch_template_data_latest, mgn_client, ec2_client, verify_instance_profile, launch_template_latest_ver):

  test_eni_used = False
  live_eni_used = False

  try:
    # Update Launch template
    ## Update disk type
    for blockdevice in new_launch_template['BlockDeviceMappings']:
        blockdevice['Ebs']['VolumeType'] = 'gp3'
        blockdevice['Ebs']['Iops'] = 3000
        blockdevice['Ebs']['Throughput'] = 125
    ## update instance type
    if 'instanceType' in factoryserver:
        new_launch_template['InstanceType'] = factoryserver['instanceType']

    ## check if ENIs provided for test or live
    if 'network_interface_id' in factoryserver and factoryserver['network_interface_id'] is not None and factoryserver['network_interface_id'] != '':
      live_eni_used = True

    if 'network_interface_id_test' in factoryserver and factoryserver['network_interface_id'] is not None and factoryserver['network_interface_id_test'] != '':
      test_eni_used = True

    ## update tenancy
    p_tenancy = {}
    if 'tenancy' in factoryserver:
        license = {}
        if factoryserver["tenancy"].lower() == "shared":
            p_tenancy['Tenancy'] = 'default'
            license = {'osByol': False}
        elif factoryserver["tenancy"].lower() == "dedicated":
            p_tenancy['Tenancy'] = 'dedicated'
            license = {'osByol': False}
        elif factoryserver["tenancy"].lower() == "dedicated host":
            p_tenancy['Tenancy'] = 'host'
            license = {'osByol': True}
            if 'dedicated_host_id' in factoryserver:
              if 'instanceType' in factoryserver:
                return_message = verify_dedicated_host(ec2_client, factoryserver['dedicated_host_id'], factoryserver['instanceType'], factoryserver['dedicated_host_required_capacity'])
                if return_message[:5] != 'ERROR':
                  p_tenancy['HostId'] = factoryserver['dedicated_host_id']
                else:
                  log.error("Pid: " + str(os.getpid()) + " - " + factoryserver['server_name'] + ':'  + return_message)
                  return factoryserver['server_name'] + ' - '  + return_message
              else:
                msg = "ERROR: Instance Type is required if specifying dedicated host ID."
                log.error("Pid: " + str(os.getpid()) + " - " + factoryserver['server_name'] + ':'  + msg)
                return msg
            else:
                msg = "ERROR: Dedicated host ID is required if specifying tenancy as dedicated host."
                log.error("Pid: " + str(os.getpid()) + " - " + factoryserver['server_name'] + ':'  + msg)
                return msg
        else:
            p_tenancy['Tenancy'] = 'default'
            license = {'osByol': False}
        if factoryserver['server_os_family'].lower() == 'linux':
            license = {'osByol': True}
        mgn_client.update_launch_configuration(licensing=license, sourceServerID=factoryserver['source_server_id'])
    else:
       p_tenancy['Tenancy'] = 'default'
    new_launch_template['Placement'] = p_tenancy
    ## update instance profile
    if len(verify_instance_profile) > 0:
        instance_profile_name = {}
        instance_profile_name['Arn'] = verify_instance_profile['InstanceProfile']['Arn']
        new_launch_template['IamInstanceProfile'] = instance_profile_name
    ## update tags
    if 'tags' in factoryserver:
      for tags in new_launch_template['TagSpecifications']:
        if tags['ResourceType'] == 'instance' or tags['ResourceType'] == 'volume':
           for item in factoryserver['tags']:
                if 'key' in item:
                    item['Key'] = item['key']
                    del item['key']
                if 'value' in item:
                    item['Value'] = item['value']
                    del item['value']
                TagExist = False
                for tag in tags['Tags']:
                    if item['Key'].lower() == tag['Key'].lower():
                       tag['Value'] = item['Value']
                       TagExist = True
                       log.info("Pid: " + str(os.getpid()) + " - Replaced existing value for tag: " + tag['Key'] + " on server: " + factoryserver['server_name'])
                if TagExist == False:
                   tags['Tags'].append(item)

    ## Update Launch template with Test SG and subnet
    if action.strip() == "Launch Test Instances":
        if test_eni_used:
          ## update ENI if provided, removes other interfaces and replaces with ENI provided, this will use subnet and SGs defined for ENI.
          network_interfaces = []
          network_interface = {}
          network_interface['NetworkInterfaceId'] = factoryserver['network_interface_id_test']
          network_interface['DeviceIndex'] = 0
          network_interfaces.append(network_interface)
          new_launch_template['NetworkInterfaces'] = network_interfaces
        else:
          ## Update Subnet Id and security group Ids if no ENI provided.
          for nic in new_launch_template['NetworkInterfaces']:
              if 'private_ip' in factoryserver:
                if factoryserver['private_IP'] is not None and factoryserver['private_IP'].strip() != '':
                   ipaddrs = []
                   ip = {}
                   ip['Primary'] = True
                   ip['PrivateIpAddress'] = factoryserver['private_ip']
                   ipaddrs.append(ip)
                   nic['PrivateIpAddresses'] = ipaddrs

        if not test_eni_used:
          for nic in new_launch_template['NetworkInterfaces']:
              nic['Groups'] = factoryserver['securitygroup_IDs_test']
              nic['SubnetId'] = factoryserver['subnet_IDs_test'][0]
        log.info("Pid: " + str(os.getpid()) + " - *** Create New Test Launch Template data: ***")
        print(new_launch_template)
        new_template = ec2_client.create_launch_template_version(LaunchTemplateId=factoryserver['launch_template_id'], SourceVersion=str(launch_template_latest_ver), LaunchTemplateData=new_launch_template)
        new_template_ver = new_template['LaunchTemplateVersion']['VersionNumber']
        if new_template['ResponseMetadata']['HTTPStatusCode'] != 200 :
            msg = "ERROR: Update Failed - Test Launch Template for server: " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return msg
        else:
            msg = "Update SUCCESS: Test Launch template updated for server: " + factoryserver['server_name']
            log.info("Pid: " + str(os.getpid()) + " - " + msg)
        log.info("Pid: " + str(os.getpid()) + " - Test Template updated, the latest version is: " + str(new_template_ver))
        set_default_ver = ec2_client.modify_launch_template(LaunchTemplateId=factoryserver['launch_template_id'],DefaultVersion=str(new_template_ver))
    
    ## Update Launch template with Cutover SG and subnet
    elif action.strip() == "Launch Cutover Instances":
        if live_eni_used:
          ## update ENI if provided, removes other interfaces and replaces with ENI provided, this will use subnet and SGs defined for ENI.
          network_interfaces = []
          network_interface = {}
          network_interface['NetworkInterfaceId'] = factoryserver['network_interface_id']
          network_interface['DeviceIndex'] = 0
          network_interfaces.append(network_interface)
          new_launch_template['NetworkInterfaces'] = network_interfaces
        else:
          ## Update Subnet Id and security group Ids if no ENI provided.
          for nic in new_launch_template['NetworkInterfaces']:
              if 'private_ip' in factoryserver:
                if factoryserver['private_ip'] is not None and factoryserver['private_ip'].strip() != '':
                   ipaddrs = []
                   ip = {}
                   ip['Primary'] = True
                   ip['PrivateIpAddress'] = factoryserver['private_IP']
                   ipaddrs.append(ip)
                   nic['PrivateIpAddresses'] = ipaddrs

        if not live_eni_used:
          for nic in new_launch_template['NetworkInterfaces']:
              nic['Groups'] = factoryserver['securitygroup_IDs']
              nic['SubnetId'] = factoryserver['subnet_IDs'][0]
        log.info("Pid: " + str(os.getpid()) + " - *** Create New Cutover Launch Template data: ***")
        print(new_launch_template)
        new_template = ec2_client.create_launch_template_version(LaunchTemplateId=factoryserver['launch_template_id'], SourceVersion=str(launch_template_latest_ver), LaunchTemplateData=new_launch_template)
        new_template_ver = new_template['LaunchTemplateVersion']['VersionNumber']
        if new_template['ResponseMetadata']['HTTPStatusCode'] != 200 :
            msg = "ERROR: Update Failed - Cutover Launch Template for server: " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return msg
        else:
            msg = "Update SUCCESS: Cutover Launch template updated for server: " + factoryserver['server_name']
            log.info("Pid: " + str(os.getpid()) + " - " + msg)
        log.info("Pid: " + str(os.getpid()) + " - Cutover Template updated, the latest version is: " + str(new_template_ver))
        set_default_ver = ec2_client.modify_launch_template(LaunchTemplateId=factoryserver['launch_template_id'],DefaultVersion=str(new_template_ver))
    
    ## Validating Launch template with both test and cutover info
    elif action.strip() == "Validate Launch Template":
        status = False
        if test_eni_used and (('securitygroup_IDs_test' in factoryserver and factoryserver['securitygroup_IDs_test'] != '') or ('subnet_IDs_test' in factoryserver and factoryserver['subnet_IDs_test'][0] != '')) :
          # user has specified both ENI and SGs but this is not a valid combination.
          status = False
          msg = "ERROR: Validation failed - Specifying Test ENI and also Test Security Group or Subnet is not supported. ENIs will inherit the SGs and Subnet of the ENI : " + factoryserver['server_name']
          log.error("Pid: " + str(os.getpid()) + " - " + msg)
          return msg

        if not test_eni_used:
          ### Update Launch template with test SG and subnet
          for nic in new_launch_template['NetworkInterfaces']:
              nic['Groups'] = factoryserver['securitygroup_IDs_test']
              nic['SubnetId'] = factoryserver['subnet_IDs_test'][0]
        log.info("Pid: " + str(os.getpid()) + " - *** Validate New Test Launch Template data: ***")
        print(new_launch_template)
        new_template_test = ec2_client.create_launch_template_version(LaunchTemplateId=factoryserver['launch_template_id'], SourceVersion=str(launch_template_latest_ver), LaunchTemplateData=new_launch_template)
        new_template_ver_test = new_template_test['LaunchTemplateVersion']['VersionNumber']
        log.info("Pid: " + str(os.getpid()) + " - Test Template updated, the latest version is: " + str(new_template_ver_test))
        if new_template_test['ResponseMetadata']['HTTPStatusCode'] != 200 :
            status = False
            msg = "ERROR: Validation failed - Test Launch Template data for server: " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return msg
        else:
            msg = "SUCCESS: Test Launch template validated for server: " + factoryserver['server_name']
            log.info("Pid: " + str(os.getpid()) + " - " + msg)
            status = True

        set_default_ver_test = ec2_client.modify_launch_template(LaunchTemplateId=factoryserver['launch_template_id'],DefaultVersion=str(new_template_ver_test))

        if live_eni_used and (('securitygroup_IDs' in factoryserver and factoryserver['securitygroup_IDs'] != '') or ('subnet_IDs' in factoryserver and factoryserver['subnet_IDs'][0] != '')) :
          # user has specified both ENI and SGs but this is not a valid combination.
          status = False
          msg = "ERROR: Validation failed - Specifying Live ENI and also Live Security Group or Subnet is not supported. ENIs will inherit the SGs and Subnet of the ENI : " + factoryserver['server_name']
          log.error("Pid: " + str(os.getpid()) + " - " + msg)
          return msg

        if not live_eni_used:
          ### Update Launch template with cutover SG and subnet
          for nic in new_launch_template['NetworkInterfaces']:
              nic['Groups'] = factoryserver['securitygroup_IDs']
              nic['SubnetId'] = factoryserver['subnet_IDs'][0]
        log.info("Pid: " + str(os.getpid()) + " - *** Validate New Cutover Launch Template data: ***")
        print(new_launch_template)
        new_template_cutover = ec2_client.create_launch_template_version(LaunchTemplateId=factoryserver['launch_template_id'], SourceVersion=str(new_template_ver_test), LaunchTemplateData=new_launch_template)
        new_template_ver_cutover = new_template_cutover['LaunchTemplateVersion']['VersionNumber']
        log.info("Pid: " + str(os.getpid()) + " - Cutover Template updated, the latest version is: " + str(new_template_ver_cutover))
        if new_template_cutover['ResponseMetadata']['HTTPStatusCode'] != 200 :
            status = False
            msg = "ERROR: Validation failed - Cutover Launch Template data for server: " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return msg
        else:
            msg = "SUCCESS: Cutover Launch template validated for server: " + factoryserver['server_name']
            log.info("Pid: " + str(os.getpid()) + " - " + msg)
            status = True

        set_default_ver_cutover = ec2_client.modify_launch_template(LaunchTemplateId=factoryserver['launch_template_id'],DefaultVersion=str(new_template_ver_cutover))

        ### Revert Launch template back to old version
        latest_template = ec2_client.create_launch_template_version(LaunchTemplateId=factoryserver['launch_template_id'], SourceVersion=str(new_template_ver_cutover), LaunchTemplateData=launch_template_data_latest)
        latest_template_ver = latest_template['LaunchTemplateVersion']['VersionNumber']
        log.info("Pid: " + str(os.getpid()) + " - Template reverted back after validation, the latest version is: " + str(latest_template_ver))
        if latest_template['ResponseMetadata']['HTTPStatusCode'] != 200 :
            status = False
            msg = "ERROR: Revert to old version failed for server: " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return msg
        else:
            status = True
        set_default_ver_latest = ec2_client.modify_launch_template(LaunchTemplateId=factoryserver['launch_template_id'],DefaultVersion=str(latest_template_ver))

        if status == True:
           msg = "SUCCESS: All Launch templates validated for server: " + factoryserver['server_name']
           log.info("Pid: " + str(os.getpid()) + " - " + msg)
           return msg
        else:
           msg = "ERROR: Launch template validation failed for server: " + factoryserver['server_name']
           log.error("Pid: " + str(os.getpid()) + " - " + msg)
           return msg
         
  except Exception as error:
        if ":" in str(error):
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + err + ' full: ' + str(error))
            return "ERROR: " + err  + ' full: ' + str(error)
        else:
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + str(error))
            return "ERROR: " + str(error)

def chunks(l, n):
    for i in range(0, n):
        yield l[i::n]