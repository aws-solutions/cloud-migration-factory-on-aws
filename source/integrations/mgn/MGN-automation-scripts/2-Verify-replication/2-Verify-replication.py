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

# Version: 29MAY2022.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import boto3
import botocore.exceptions
from datetime import datetime
import time
import mfcommon

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint
timeout = 60*60

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

def unix_time_millis(dt):
    epoch = datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds()

def assume_role(account_id, region):

    sts_client = boto3.client('sts')
    role_arn = 'arn:aws:iam::' + account_id + ':role/CMF-MGNAutomation'
    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.
    try:
        user = sts_client.get_caller_identity()['Arn']
        sessionname = user.split('/')[1]
        response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=sessionname)
        credentials = response['Credentials']
        session = boto3.Session(
            region_name = region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        return session
    except botocore.exceptions.ClientError as e:
        print(str(e))

#Pagination for describe MGN source servers
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

def verify_replication(serverlist, UserHOST):
    Not_finished = True
    count_fail = 0
    currentTime = datetime.utcnow()
    while Not_finished:
        auth = {"Authorization": mfcommon.Factorylogin()}
        Not_finished = False
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
            print("#### Replication Status for Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
            print("##########################################################################", flush = True)
            machine_status = {}
            for factoryserver in account['servers']:
                replication_not_finished = False
                if 'server_fqdn' not in factoryserver:
                    print("ERROR: server_fqdn does not exist for server: " + factoryserver['server_name'], flush = True)
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
                                if  replication_state == 'INITIAL_SYNC' or replication_state == 'RESCAN':
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
                                                    machine_status[factoryserver["server_name"]] = msg + str(result) + " Minutes"
                                                else:
                                                    hours = int(result / 60)
                                                    machine_status[factoryserver["server_name"]] = msg + str(hours) + " Hours"
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
                                     machine_status[factoryserver["server_name"]] = 'Disconnected - Please reinstall agent'
                                else:
                                     machine_status[factoryserver["server_name"]] = replication_state.lower().capitalize()
                            else:
                                machine_status[factoryserver["server_name"]] = 'Replication info not Available'
                        else:
                            machine_status[factoryserver["server_name"]] = 'Archived - Please reinstall agent'
                            count_fail += 1
                        # print replication status and update replication_status in migration factory
                        print ("Server " + factoryserver["server_name"] + " replication status: " + machine_status[factoryserver["server_name"]], flush = True)
                        serverattr = {"replication_status": machine_status[factoryserver["server_name"]]}
                        if machine_status[factoryserver["server_name"]] != "Healthy":
                            replication_not_finished = True
                        updateserver = requests.put(UserHOST + serverendpoint + '/' + factoryserver['server_id'], headers=auth, data=json.dumps(serverattr))
                        if updateserver.status_code == 401:
                            print("Error: Access to replication_status attribute is denied", flush = True)
                            sys.exit(1)
                        elif updateserver.status_code != 200:
                            print("Error: Update replication_status attribute failed", flush = True)
                            sys.exit(1)
                        replication_status.append(replication_not_finished)
                    # else:

        for status in replication_status:
            if status == True:
               Not_finished = True
        if Not_finished:
            print("")
            print("***************************************************")
            print("* Replication in progress - retry after 1 minute *")
            print("***************************************************", flush = True)
            time.sleep(60)
        print("")
        newTime = datetime.utcnow()
        timeElapsed = unix_time_millis(newTime) - unix_time_millis(currentTime)
        print(str(timeElapsed) + " seconds elapsed")
        print("")
        if timeElapsed > timeout:
            return -1
    return count_fail

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--NoPrompts', default=False, type=bool, help='Specify if user prompts for passwords are allowed. Default = False')
    args = parser.parse_args(arguments)

    UserHOST = ""
    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit(1)

    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************", flush = True)
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************", flush = True)
    get_servers = mfcommon.get_factory_servers(args.Waveid, token, UserHOST, False, 'Rehost')

    print("")
    print("*****************************")
    print("* Verify replication status *")
    print("*****************************", flush = True)
    failure_count = verify_replication(get_servers, UserHOST)

    if (failure_count == -1):
        print("The script has been running for more than 60 minutes, please verify the status and run this again as needed")
        return 1
    elif (failure_count > 0):
        print( str(failure_count) + " servers have had replication issues. Check log for details.")
        return 1
    else:
        print("All servers have had replication completed successfully.")
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
