#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 29MAY2022.01

from __future__ import print_function
import sys
import argparse
import boto3
import botocore.exceptions
from datetime import datetime
import time
import mfcommon

timeout = 60 * 60


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


def verify_replication(serverlist):
    not_finished = True
    count_fail = 0
    current_time = datetime.utcnow()
    while not_finished:
        not_finished = False
        replication_status = []
        for account in serverlist:
            replication_not_finished = False
            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            #### Change this line, and not hardcoded endpoint_url
            mgn_client = target_account_session.client("mgn", account['aws_region'])
            #### Change this line, and not hardcoded endpoint_url
            mgn_sourceservers = get_mgn_source_servers(mgn_client)
            print("")
            print("##########################################################################")
            print("#### Replication Status for Account: " + account['aws_accountid'],
                  ", region: " + account['aws_region'] + " ####")
            print("##########################################################################", flush=True)
            machine_status = {}
            for factoryserver in account['servers']:
                replication_not_finished = False
                if 'server_fqdn' not in factoryserver:
                    print("ERROR: server_fqdn does not exist for server: " + factoryserver['server_name'], flush=True)
                else:

                    sourceserver = mfcommon.get_MGN_Source_Server(factoryserver, mgn_sourceservers)

                    if sourceserver is not None:
                        if sourceserver['isArchived'] == False:
                            if 'dataReplicationInfo' in sourceserver:
                                replication_state = sourceserver['dataReplicationInfo']['dataReplicationState']
                                laststep = ""
                                steps = sourceserver['dataReplicationInfo']['dataReplicationInitiation']['steps']
                                for step in reversed(steps):
                                    if step['status'] == 'SUCCEEDED':
                                        laststep = step['name']
                                        break
                                if replication_state == 'INITIAL_SYNC' or replication_state == 'RESCAN':
                                    # Return message
                                    msg = ""
                                    if replication_state == 'INITIAL_SYNC':
                                        msg = "Initial sync, ETA "
                                    elif replication_state == 'RESCAN':
                                        msg = "Rescanning, ETA "
                                    # Calculate ETA
                                    if laststep == "START_DATA_TRANSFER":
                                        if 'etaDateTime' in sourceserver['dataReplicationInfo']:
                                            a = int(sourceserver['dataReplicationInfo']['etaDateTime'][11:13])
                                            b = int(sourceserver['dataReplicationInfo']['etaDateTime'][14:16])
                                            x = int(datetime.utcnow().isoformat()[11:13])
                                            y = int(datetime.utcnow().isoformat()[14:16])
                                            result = (a - x) * 60 + (b - y)
                                            if result < 60:
                                                machine_status[factoryserver["server_name"]] = msg + str(
                                                    result) + " Minutes"
                                            else:
                                                hours = int(result / 60)
                                                machine_status[factoryserver["server_name"]] = msg + str(
                                                    hours) + " Hours"
                                        else:
                                            machine_status[factoryserver["server_name"]] = msg + "not available"
                                    else:
                                        msg = msg + "not available"
                                        if laststep != '':
                                            machine_status[factoryserver["server_name"]] = laststep
                                        else:
                                            machine_status[factoryserver["server_name"]] = msg
                                elif replication_state.lower() == 'initiating':
                                    machine_status[factoryserver["server_name"]] = 'Initiating - ' + laststep
                                elif replication_state.lower() == 'continuous':
                                    machine_status[factoryserver["server_name"]] = 'Healthy'
                                elif replication_state.lower() == 'disconnected':
                                    machine_status[
                                        factoryserver["server_name"]] = 'Disconnected - Please reinstall agent'
                                else:
                                    machine_status[
                                        factoryserver["server_name"]] = replication_state.lower().capitalize()
                            else:
                                machine_status[factoryserver["server_name"]] = 'Replication info not Available'
                        else:
                            machine_status[factoryserver["server_name"]] = 'Archived - Please reinstall agent'
                            count_fail += 1
                        # print replication status and update replication_status in migration factory
                        print("Server " + factoryserver["server_name"] + " replication status: " + machine_status[
                            factoryserver["server_name"]], flush=True)

                        updateserver = mfcommon.update_server_replication_status(
                            mfcommon.Factorylogin(),
                            factoryserver['server_id'],
                            machine_status[factoryserver["server_name"]]
                        )
                        if machine_status[factoryserver["server_name"]] != "Healthy":
                            replication_not_finished = True
                        if updateserver.status_code == 401:
                            print("Error: Access to replication_status attribute is denied", flush=True)
                            sys.exit(1)
                        elif updateserver.status_code != 200:
                            print("Error: Update replication_status attribute failed", flush=True)
                            sys.exit(1)
                        replication_status.append(replication_not_finished)
                    # else:

        for status in replication_status:
            if status == True:
                not_finished = True
        if not_finished:
            print("")
            print("Replication in progress - next check in 1 minute.", flush=True)
            time.sleep(60)
        print("")
        new_time = datetime.utcnow()
        time_elapsed = unix_time_millis(new_time) - unix_time_millis(current_time)
        print(str(time_elapsed) + " seconds elapsed")
        print("")
        if time_elapsed > timeout:
            return -1
    return count_fail


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
    print("* Verify replication status *")
    print("*****************************", flush=True)
    failure_count = verify_replication(get_servers)

    if (failure_count == -1):
        print(
            "The script has been running for more than 60 minutes, please verify the status and run this again as needed")
        return 1
    elif (failure_count > 0):
        print(str(failure_count) + " servers have had replication issues. Check log for details.")
        return 1
    else:
        print("All servers have had replication completed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
