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

# Version: 13APR2021.01

from __future__ import print_function
import sys
import argparse
import json
import boto3
import botocore.exceptions
import csv
import mfcommon

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

def assume_role(account_id, region):

    sts_client = boto3.client('sts')
    role_arn = 'arn:aws:iam::' + account_id + ':role/Factory-Automation'
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

def GetInstanceId(serverlist):
        for account in serverlist:
            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            print("")
            print("Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'])
            mgn_client = target_account_session.client("mgn", account['aws_region'])
            mgn_sourceservers = mgn_client.describe_source_servers(filters={})
            for factoryserver in account['servers']:
                if 'server_fqdn' not in factoryserver:
                    print("ERROR: server_fqdn does not exist for server: " + factoryserver['server_name'])
                    sys.exit()
                else:
                    sourceserver = mfcommon.get_MGN_Source_Server(factoryserver, mgn_sourceservers['items'])
                    if sourceserver is not None:
                        # Get target instance Id for the source server in Application Migration Service
                        if sourceserver['isArchived'] == False:
                                if 'launchedInstance' in sourceserver:
                                    if 'ec2InstanceID' in sourceserver['launchedInstance']:
                                        factoryserver['target_ec2InstanceID'] = sourceserver['launchedInstance']['ec2InstanceID']
                                        print(factoryserver['server_name'] + " : " + factoryserver['target_ec2InstanceID'])
                                    else:
                                        factoryserver['target_ec2InstanceID'] = ''
                                        print("ERROR: target instance Id does not exist for server: " + factoryserver['server_name'] + ", please wait for a few minutes")
                                else:
                                    factoryserver['target_ec2InstanceID'] = ''
                                    print("ERROR: target instance does not exist for server: " + factoryserver['server_name'] + ", please wait for a few minutes")
                        else:
                            print("ERROR: Server: " + factoryserver['server_name'] + " is archived in Application Migration Service (Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + "), Please install the agent")
                            sys.exit()
        return serverlist

def get_instance_ips(InstanceList, waveid):
        all_instance_ips = []
        for account in InstanceList:
            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            print("")
            print("######################################################")
            print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
            print("######################################################")
            #### Change this line, and not hardcoded endpoint_url
            ec2_client = target_account_session.client("ec2", region_name=account['aws_region'])
            instanceIds = []
            for server in account['servers']:
                if 'target_ec2InstanceID' in server:
                    if server['target_ec2InstanceID'] != '':
                        instanceIds.append(server['target_ec2InstanceID'])
            if len(instanceIds) != 0:
                #resp = ec2_client.describe_instances(InstanceIds=instanceIds, Filters=[{'Name': 'instance-state-name', 'Values': ['available', 'terminated']}])
                resp = ec2_client.describe_instances(InstanceIds=instanceIds)
            else:
                print("")
                print("*** No target instances available for this wave ***")
                return

            for r in resp['Reservations']:
                for instance in r['Instances']:
                    instance_ips = {}
                    instance_name = ""
                    ips = ""
                    name_exist = False
                    for tag in instance['Tags']:
                        if tag['Key'] == "Name":
                            if tag['Value'] != "":
                                instance_name = tag['Value']
                                name_exist = True
                    if name_exist == False:
                        print("ERROR: Name Tag does not exist for instance " + instance['InstanceId'])
                        sys.exit()
                    for nic in instance['NetworkInterfaces']:
                        for ip in nic['PrivateIpAddresses']:
                            ips = ips + ip['PrivateIpAddress'] + ","
                    instance_ips['instance_name'] = instance_name
                    instance_ips['instance_ips'] = ips[:-1]
                    print(instance_name + " , " + ips[:-1])
                    all_instance_ips.append(instance_ips)
        filename = "Wave" + waveid + "-IPs.csv"
        if len(all_instance_ips) != 0:
            with open(filename, "w", newline='') as csvfile:
                writer = csv.DictWriter(csvfile, all_instance_ips[0].keys())
                writer.writeheader()
                writer.writerows(all_instance_ips)
            print("")
            print("*** Exported Instance IPs to " + filename + " ***")
        else:
            print("")
            print("*** No target instances available for this wave ***")

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    args = parser.parse_args(arguments)

    UserHOST = ""
    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit()

    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************")
    get_servers = mfcommon.get_factory_servers(args.Waveid, token, UserHOST, False)

    print("******************************")
    print("* Getting Target Instance Id *")
    print("******************************")

    InstanceList = GetInstanceId(get_servers)
    print("")
    print("*****************************")
    print("* Get target Instance IPs *")
    print("*****************************")

    get_instance_ips(InstanceList, args.Waveid)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
