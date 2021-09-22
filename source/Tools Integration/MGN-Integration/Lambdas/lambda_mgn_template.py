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
import json
import boto3
import botocore.exceptions
import lambda_mgn
import multiprocessing
import logging
from botocore import config

log = logging.getLogger()
log.setLevel(logging.INFO)

if 'solution_identifier' in os.environ:
    solution_identifier= json.loads(os.environ['solution_identifier'])
    user_agent_extra_param = {"user_agent_extra":solution_identifier}
    boto_config = config.Config(**user_agent_extra_param)
else:
    boto_config = None

def update_launch_template(factoryservers, action):
  try:
    # Check if the action is launch servers or validate launch template
    if action != 'Launch Test Instances' and action != 'Launch Cutover Instances' and action != 'Validate Launch Template':
        return
    # Enable multithreading
    processes = []
    manager = multiprocessing.Manager()
    status_list = manager.list()
    return_dict = manager.dict()
    total_servers_count = 0
    max_threads = 30

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
    if len(return_dict.values()) > 0:
        log.error("ERROR: Launch templates validation failed")
        print(return_dict.values())
        return str(return_dict.values()[0])
    else:
        if action == 'Validate Launch Template':
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
  try:
    target_account_session = lambda_mgn.get_session(creds, region)
    ec2_client = target_account_session.client('ec2', region)
    iam_client = target_account_session.client('iam')
    mgn_client = target_account_session.client("mgn", region_name=region, config=boto_config)
    validated_count = 0
    for factoryserver in serverlist:
        # Get Launch template latest version and data
        launch_template_latest_ver = ec2_client.describe_launch_templates(LaunchTemplateIds=[factoryserver['launch_template_id']])['LaunchTemplates'][0]['LatestVersionNumber']
        launch_template_data_latest = ec2_client.describe_launch_template_versions(LaunchTemplateId=factoryserver['launch_template_id'], Versions=[str(launch_template_latest_ver)])['LaunchTemplateVersions'][0]['LaunchTemplateData']
        new_launch_template = ec2_client.describe_launch_template_versions(LaunchTemplateId=factoryserver['launch_template_id'], Versions=[str(launch_template_latest_ver)])['LaunchTemplateVersions'][0]['LaunchTemplateData']

        # Verify Launch templates inputs
        subnet_vpc = ""
        subnet_vpc_test = ""
        # Verify Subnets and SGs
        if 'subnet_IDs_test' in factoryserver and 'subnet_IDs' in factoryserver:
            if len(factoryserver['subnet_IDs_test']) > 0 and len(factoryserver['subnet_IDs']) > 0:
                verify_subnet_test = ec2_client.describe_subnets(SubnetIds=factoryserver['subnet_IDs_test'])
                subnet_vpc_test = verify_subnet_test['Subnets'][0]['VpcId']
                verify_subnet = ec2_client.describe_subnets(SubnetIds=factoryserver['subnet_IDs'])
                subnet_vpc = verify_subnet['Subnets'][0]['VpcId']
            else:
                msg = "ERROR: Subnet_IDs or Subnet_IDs_test attribute is empty for server: " + factoryserver['server_name']
                log.error("Pid: " + str(os.getpid()) + " - " + msg)
                return_dict[factoryserver['server_name']] = msg
                break
        else:
            msg = "ERROR: Subnet_IDs or Subnet_IDs_test does not exist for server: " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return_dict[factoryserver['server_name']] = msg
            break
        if 'securitygroup_IDs_test' in factoryserver and 'securitygroup_IDs' in factoryserver:
            if len(factoryserver['securitygroup_IDs_test']) > 0 and len(factoryserver['securitygroup_IDs']) > 0:
                verify_sgs_test = ec2_client.describe_security_groups(GroupIds=factoryserver['securitygroup_IDs_test'])
                for sg in verify_sgs_test['SecurityGroups']:
                    if subnet_vpc_test != sg['VpcId']:
                        msg = "ERROR: Subnet and Security groups must be in the same VPC: " + verify_subnet_test['Subnets'][0]['SubnetId'] + ", " + sg['GroupId']
                        log.error("Pid: " + str(os.getpid()) + " - " + msg)
                        return_dict[factoryserver['server_name']] = msg
                        break
                verify_sgs = ec2_client.describe_security_groups(GroupIds=factoryserver['securitygroup_IDs'])
                for sg in verify_sgs['SecurityGroups']:
                    if subnet_vpc != sg['VpcId']:
                        msg = "ERROR: Subnet and Security groups must be in the same VPC: " + verify_subnet['Subnets'][0]['SubnetId'] + ", " + sg['GroupId']
                        log.error("Pid: " + str(os.getpid()) + " - " + msg)
                        return_dict[factoryserver['server_name']] = msg
                        break
            else:
                msg = "ERROR: securitygroup_IDs or securitygroup_IDs_test attribute is empty for server: " + factoryserver['server_name']
                log.error("Pid: " + str(os.getpid()) + " - " + msg)
                return_dict[factoryserver['server_name']] = msg
                break
        else:
            msg = "ERROR: securitygroup_IDs or securitygroup_IDs_test does not exist for server: " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return_dict[factoryserver['server_name']] = msg
            break
        if 'server_os_family' in factoryserver:
            if factoryserver['server_os_family'].lower().strip() != 'windows' and factoryserver['server_os_family'].lower().strip() != 'linux':
                msg = "ERROR: server_os_family only supports Windows or Linux - " + factoryserver['server_name']
                log.error("Pid: " + str(os.getpid()) + " - " + msg)
                return_dict[factoryserver['server_name']] = msg
                break
        else:
            msg = "ERROR: server_os_family does not exist for server - " + factoryserver['server_name']
            log.error("Pid: " + str(os.getpid()) + " - " + msg)
            return_dict[factoryserver['server_name']] = msg
            break

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
        create_template = create_launch_template(factoryserver, action, new_launch_template, launch_template_data_latest, mgn_client, ec2_client, verify_instance_profile, launch_template_latest_ver)
        if create_template is not None and "ERROR" in create_template:
            log.error("Pid: " + str(os.getpid()) + " - " + str(create_template))
            return_dict[factoryserver['server_name']] = create_template
        else:
            validated_count = validated_count + 1

    status_list.append(validated_count)

  except Exception as error:
        if ":" in str(error):
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + err)
            return_dict[factoryserver['server_name']] = "ERROR: " + err
        else:
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + str(error))
            return_dict[factoryserver['server_name']] = "ERROR: " + str(error)

def create_launch_template(factoryserver, action, new_launch_template, launch_template_data_latest, mgn_client, ec2_client, verify_instance_profile, launch_template_latest_ver):
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
    ## Update Subnet Id and security group Ids
    for nic in new_launch_template['NetworkInterfaces']:
        if 'private_ip' in factoryserver:
          if factoryserver['private_ip'] is not None and factoryserver['private_ip'].strip() != '':
             ipaddrs = []
             ip = {}
             ip['Primary'] = True
             ip['PrivateIpAddress'] = factoryserver['private_ip']
             ipaddrs.append(ip)
             nic['PrivateIpAddresses'] = ipaddrs

    ## Update Launch template with Test SG and subnet
    if action == "Launch Test Instances":
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
    elif action == "Launch Cutover Instances":
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
    elif action == "Validate Launch Template":
        status = False
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
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + err)
            return "ERROR: " + err
        else:
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + str(error))
            return "ERROR: " + str(error)

def chunks(l, n):
    for i in range(0, n):
        yield l[i::n]
