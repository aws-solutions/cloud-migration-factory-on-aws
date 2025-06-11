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
from datetime import datetime, UTC

TIME_OUT = 60 * 60

SERVER_INSTANCE_ID_ATTR_NAME = 'target_instance_id'


def unix_time_millis(dt):
    epoch = datetime.fromtimestamp(0, UTC)
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


def get_instance_id(server_list, cmf_access_token):
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
                sourceserver = mfcommon.get_mgn_source_server(
                    factoryserver, mgn_sourceservers)
                if sourceserver is not None:
                    update_target_instance_id(sourceserver, factoryserver, account, cmf_access_token)
    return server_list


def update_target_instance_id(sourceserver, factoryserver, account, cmf_access_token):
    # Get target instance Id for the source server in Application Migration Service
    # at this point sourceserver['isArchived'] should be False, but double check
    if sourceserver['isArchived'] == False:
        if 'launchedInstance' in sourceserver:
            if 'ec2InstanceID' in sourceserver['launchedInstance']:
                update_server_instance_id_in_cmf(cmf_access_token, factoryserver, sourceserver['launchedInstance'][
                    'ec2InstanceID'])
                print(factoryserver['server_name'] + " : " + factoryserver[SERVER_INSTANCE_ID_ATTR_NAME])
            else:
                update_server_instance_id_in_cmf(cmf_access_token, factoryserver, '')
                print("ERROR: target instance Id does not exist for server: " + factoryserver[
                    'server_name'] + ", please wait for a few minutes")
        else:
            update_server_instance_id_in_cmf(cmf_access_token, factoryserver, '')
            print("ERROR: target instance does not exist for server: " + factoryserver[
                'server_name'] + ", please wait for a few minutes")
    else:
        print("ERROR: Server: " + factoryserver[
            'server_name'] + " is archived in Application Migration Service (Account: " + account[
                  'aws_accountid'] + ", Region: " + account[
                  'aws_region'] + "), Please install the agent")
        sys.exit()


def verify_instance_status(get_servers):
    instance_not_ready = 1
    failure_status = 0
    current_time = datetime.now(UTC)
    while instance_not_ready > 0:  # NOSONAR: this is not a bug instance_not_ready is updated in the loop
        # refresh token
        cmf_access_token = mfcommon.factory_login(True)
        print("******************************")
        print("* Getting Target Instance Id *")
        print("******************************")
        server_list = get_instance_id(get_servers, cmf_access_token)
        failure_status, instance_not_ready = verify_server_list(server_list, cmf_access_token)

        if instance_not_ready > 0:
            print("")
            print("**************************************************")
            print("* Instances booting up - auto retry in 2 minutes *")
            print("**************************************************")
            print("", flush=True)
            time.sleep(120)

        if failure_status != 0:
            # Check if timeout reached.
            new_time = datetime.now(UTC)
            time_elapsed = unix_time_millis(new_time) - unix_time_millis(current_time)
            print(str(time_elapsed) + " seconds elapsed")
            print("")
            if time_elapsed > TIME_OUT:
                # Timeout occurred, exit loop.
                print("It has been more than 30 minutes since launching servers, "
                      "please check issues on the server before running this again", flush=True)
                break
        else:
            # No more errors/warnings present, exit loop.
            break

    return failure_status


def verify_server_list(server_list, token):
    failure_status = 0
    instance_not_ready = 0
    for account in server_list:
        failure_status, instance_not_ready = \
            verify_account_in_server_list(account, failure_status, instance_not_ready, token)

    return failure_status, instance_not_ready


def verify_account_in_server_list(account, failure_status, instance_not_ready, token):
    target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
    print("")
    print("######################################################")
    print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
    print("######################################################")

    ec2_client = target_account_session.client("ec2", region_name=account['aws_region'])
    instance_ids = []
    ec2_descriptions = None
    for server in account['servers']:
        if SERVER_INSTANCE_ID_ATTR_NAME in server:
            if server[SERVER_INSTANCE_ID_ATTR_NAME] != '':
                instance_ids.append(server[SERVER_INSTANCE_ID_ATTR_NAME])
    try:
        ec2_descriptions = ec2_client.describe_instance_status(InstanceIds=instance_ids, IncludeAllInstances=True)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
            print("")
            print(
                "*** Target instance IDs in MGN are no longer available or instance not yet created, "
                "this is most likely due to the status being reverted and instances terminated. ***")
        else:
            raise e

    update_instance_statuses(account, ec2_descriptions)
    failure_status, instance_not_ready = print_server_verification_results(account, failure_status, instance_not_ready)
    update_mgn_status(account, token)

    return failure_status, instance_not_ready


def update_server_instance_id_in_cmf(cmf_access_token, server, instance_id):
    """
        Updates CMF server record with new instance Id.
    """

    if instance_id == server.get(SERVER_INSTANCE_ID_ATTR_NAME, None):
        # No changes found.
        return

    instance_id_update_payload = {
        SERVER_INSTANCE_ID_ATTR_NAME: instance_id
    }

    mfcommon.put_data_to_api(cmf_access_token, mfcommon.get_mf_config_user_api_id(), f"{mfcommon.serverendpoint}/{server['server_id']}", instance_id_update_payload)

    server[SERVER_INSTANCE_ID_ATTR_NAME] = instance_id


def update_mgn_status(account, token):
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


def print_server_verification_results(account, failure_status, instance_not_ready):
    server_passed, server_failed, server_not_in_mgn, target_server_not_exist, failure_status = \
        determine_servers_statuses(account, failure_status)

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

    return failure_status, instance_not_ready


def determine_servers_statuses(account, failure_status):
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

    return server_passed, server_failed, server_not_in_mgn, target_server_not_exist, failure_status


def update_instance_statuses(account, ec2_descriptions):
    for instance in account['servers']:
        if SERVER_INSTANCE_ID_ATTR_NAME in instance:
            if instance[SERVER_INSTANCE_ID_ATTR_NAME] != '' and ec2_descriptions and 'InstanceStatuses' in ec2_descriptions:
                update_instance_statuses_for_target_instance_id(instance, ec2_descriptions)
            else:
                instance['Status'] = "target_not_exist"
        else:
            instance['Status'] = "not_in_mgn"


def update_instance_statuses_for_target_instance_id(instance, ec2_descriptions):
    for status in ec2_descriptions['InstanceStatuses']:
        if status['InstanceState']['Name'] == "running":
            if instance[SERVER_INSTANCE_ID_ATTR_NAME] == status['InstanceId']:
                if status['InstanceStatus']['Status'].lower() == "ok" and \
                        status['SystemStatus']['Status'].lower() == "ok":
                    instance['Status'] = "ok"
                elif status['InstanceStatus']['Status'].lower() == "impaired" and \
                        status['SystemStatus']['Status'].lower() == "ok":
                    instance['Status'] = "impaired"
                else:
                    instance['Status'] = "failed"
        else:
            instance['Status'] = "failed"


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--AppIds', default=None)
    parser.add_argument('--ServerIds', default=None)
    parser.add_argument('--NoPrompts', default=False, type=mfcommon.parse_boolean,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    args = parser.parse_args(arguments)

    print("")
    print("*Login to Migration factory*", flush=True)
    token = mfcommon.factory_login()

    print("*** Getting Server List ****", flush=True)
    get_servers = mfcommon.get_factory_servers(
        waveid=args.Waveid,
        app_ids=mfcommon.parse_list(args.AppIds),
        server_ids=mfcommon.parse_list(args.ServerIds),
        token=token,
        os_split=False,
        rtype='Rehost'
    )

    print("")
    print("*****************************")
    print("** Verify instance status **")
    print("*****************************", flush=True)

    failure_count = verify_instance_status(get_servers)

    if failure_count > 0:
        print(str(failure_count) + " servers have status as failed or impaired or not found . Check log for details.")
        return 1
    else:
        print("All servers have had status check completed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
