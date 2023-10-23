#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 01SEP2023.01

from __future__ import print_function
import sys
import argparse
import boto3
import botocore.exceptions
import time
import mfcommon
from datetime import datetime

TIME_OUT = 60 * 60


def unix_time_millis(dt):
    epoch = datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds()


def assume_role(account_id, region):
    sts_client = boto3.client('sts', region_name=region)
    role_arn = 'arn:aws:iam::' + account_id + ':role/CMF-MGNAutomation'
    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.
    try:
        user = sts_client.get_caller_identity()['Arn']
        sessionname = user.split('/')[1]
        response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=sessionname)
        credentials = response['Credentials']
        session = boto3.Session(
            region_name=region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        return session
    except botocore.exceptions.ClientError as e:
        print(str(e))


# Pagination for describe MGN source servers
def get_mgn_source_servers(mgn_client_base):
    token = None
    source_server_data = []
    paginator = mgn_client_base.get_paginator('describe_source_servers')
    while True:
        response = paginator.paginate(filters={},
                                      PaginationConfig={
                                          'StartingToken': token})
        for page in response:
            source_server_data.extend(page['items'])
        try:
            token = page['NextToken']
            print(token)
        except KeyError:
            return source_server_data


def get_instance_id(server_list):
    for account in server_list:
        target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
        print("")
        print("Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'])
        mgn_client = target_account_session.client("mgn", account['aws_region'])
        mgn_sourceservers = get_mgn_source_servers(mgn_client)
        for factoryserver in account['servers']:
            if 'server_fqdn' not in factoryserver:
                print("ERROR: server_fqdn does not exist for server: " + factoryserver['server_name'])
                sys.exit()
            else:
                sourceserver = mfcommon.get_MGN_Source_Server(factoryserver, mgn_sourceservers)
                if sourceserver is not None:
                    # Get target instance Id for the source server in Application Migration Service
                    if sourceserver['isArchived'] == False:
                        if 'launchedInstance' in sourceserver:
                            if 'ec2InstanceID' in sourceserver['launchedInstance']:
                                factoryserver['target_ec2InstanceID'] = sourceserver['launchedInstance'][
                                    'ec2InstanceID']
                                print(factoryserver['server_name'] + " : " + factoryserver['target_ec2InstanceID'])
                            else:
                                factoryserver['target_ec2InstanceID'] = ''
                                print("ERROR: target instance Id does not exist for server: " + factoryserver[
                                    'server_name'] + ", please wait for a few minutes")
                        else:
                            factoryserver['target_ec2InstanceID'] = ''
                            print("ERROR: target instance does not exist for server: " + factoryserver[
                                'server_name'] + ", please wait for a few minutes")
                    else:
                        print("ERROR: Server: " + factoryserver[
                            'server_name'] + " is archived in Application Migration Service (Account: " + account[
                                  'aws_accountid'] + ", Region: " + account[
                                  'aws_region'] + "), Please install the agent")
                        sys.exit()
    return server_list


def verify_instance_status(get_servers, token):
    instance_not_ready = 1
    current_time = datetime.utcnow()
    while instance_not_ready > 0:
        instance_not_ready = 0
        failure_status = 0
        print("******************************")
        print("* Getting Target Instance Id *")
        print("******************************")
        server_list = get_instance_id(get_servers)
        for account in server_list:
            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            print("")
            print("######################################################")
            print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
            print("######################################################")

            ec2_client = target_account_session.client("ec2", region_name=account['aws_region'])
            instance_ids = []
            for server in account['servers']:
                if 'target_ec2InstanceID' in server:
                    if server['target_ec2InstanceID'] != '':
                        instance_ids.append(server['target_ec2InstanceID'])
            try:
                resp = ec2_client.describe_instance_status(InstanceIds=instance_ids, IncludeAllInstances=True)
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                    print("")
                    print(
                        "*** Target instance IDs in MGN are no longer available, this is most likely due to the status being reverted and instances terminated. ***")
                    return
                else:
                    raise e

            for instance in account['servers']:
                if 'target_ec2InstanceID' in instance:
                    if instance['target_ec2InstanceID'] != '':
                        for status in resp['InstanceStatuses']:
                            if status['InstanceState']['Name'] == "running":
                                if instance['target_ec2InstanceID'] == status['InstanceId']:
                                    if status['InstanceStatus']['Status'].lower() == "ok" and status['SystemStatus'][
                                        'Status'].lower() == "ok":
                                        instance['Status'] = "ok"
                                    elif status['InstanceStatus']['Status'].lower() == "impaired" and \
                                        status['SystemStatus']['Status'].lower() == "ok":
                                        instance['Status'] = "impaired"
                                    else:
                                        instance['Status'] = "failed"
                            else:
                                instance['Status'] = "failed"
                    else:
                        instance['Status'] = "target_not_exist"
                else:
                    instance['Status'] = "not_in_mgn"
            # Print out result
            server_passed = {}
            server_failed = {}
            server_not_in_mgn = {}
            target_server_not_exist = {}
            for instance in account['servers']:
                if instance['Status'] == "ok":
                    server_passed[instance['server_fqdn']] = "ok"
                elif instance['Status'] == "failed":
                    server_failed[instance['server_fqdn']] = "failed"
                    failure_status += 1
                elif instance['Status'] == 'target_not_exist':
                    target_server_not_exist[instance['server_fqdn']] = "target_not_exist"
                    failure_status += 1
                elif instance['Status'] == 'not_in_mgn':
                    server_not_in_mgn[instance['server_fqdn']] = "not_in_mgn"
                    failure_status += 1
                elif instance['Status'] == "impaired":
                    server_failed[instance['server_fqdn']] = "impaired"
                    failure_status += 1

            if len(server_passed) > 0:
                print("----------------------------------------------------")
                print("- The following instances PASSED 2/2 status checks -")
                print("----------------------------------------------------", flush=True)
                for passed in server_passed.keys():
                    print(passed, flush=True)
                print("")
            if len(server_failed) > 0:
                instance_not_ready = instance_not_ready + 1
                print("-----------------------------------------------------------------")
                print("- WARNING: the following instances FAILED 2/2 status checks -----")
                print("-----------------------------------------------------------------", flush=True)
                for failed in server_failed.keys():
                    print(failed)
                print("", flush=True)
            if len(target_server_not_exist) > 0:
                instance_not_ready = instance_not_ready + 1
                print("----------------------------------------------------------------")
                print("-  The following source servers do not have a target instance  -")
                print("----------------------------------------------------------------", flush=True)
                for target_not_exist in target_server_not_exist.keys():
                    print(target_not_exist)
                print("", flush=True)
            if len(server_not_in_mgn) > 0:
                print("------------------------------------------------------------------")
                print("-  The following source servers do not exist in App Mig Service  -")
                print("------------------------------------------------------------------", flush=True)
                for not_in_mgn in server_not_in_mgn.keys():
                    print(not_in_mgn)
                print("", flush=True)

            # Updating migration factory migration_status attributes
            for instance in account['servers']:
                server_status = ''
                if instance['Status'] == "ok":
                    server_status = "2/2 status checks : Passed"
                elif instance['Status'] == "failed":
                    server_status = "2/2 status checks : Failed"
                elif instance['Status'] == "target_not_exist":
                    server_status = "2/2 status checks : Target instance not exist"
                elif instance['Status'] == "not_in_mgn":
                    server_status = "2/2 status checks : Server not in MGN"
                elif instance['Status'] == "impaired":
                    server_status = "2/2 status checks : Failed"

                updateserver = mfcommon.update_server_migration_status(token, instance['server_id'], server_status)
                if updateserver.status_code == 401:
                    print("Error: Access to migration_status attribute is denied")
                    sys.exit(1)
                elif updateserver.status_code != 200:
                    print("Error: Update migration_status attribute failed")
                    sys.exit(1)

        if instance_not_ready > 0:
            print("")
            print("***********************************************")
            print("* Instance booting up - retry after 2 minutes *")
            print("***********************************************")
            print("", flush=True)
            time.sleep(120)

        if failure_status == 0:
            return failure_status
        else:
            new_time = datetime.utcnow()
            time_elapsed = unix_time_millis(new_time) - unix_time_millis(current_time)
            print(str(time_elapsed) + " seconds elapsed")
            print("")
            if time_elapsed > TIME_OUT:
                print(
                    "It has been more than 30 minutes since launching servers, please check issues on the server before running this again",
                    flush=True)
                return failure_status


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--NoPrompts', default=False, type=bool,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    args = parser.parse_args(arguments)

    print("")
    print("*Login to Migration factory*", flush=True)
    token = mfcommon.Factorylogin()

    print("*** Getting Server List ****", flush=True)
    get_servers = mfcommon.get_factory_servers(args.Waveid, token, False, 'Rehost')

    print("")
    print("*****************************")
    print("** Verify instance status **")
    print("*****************************", flush=True)

    failure_count = verify_instance_status(get_servers, token)

    if failure_count > 0:
        print(str(failure_count) + " servers have status as failed or impaired or not found . Check log for details.")
        return 1
    else:
        print("All servers have had status check completed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
