#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 01SEP2023.01

from __future__ import print_function
import sys
import argparse
import boto3
import botocore.exceptions
import csv
import mfcommon


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


def get_instance_id(serverlist):
    for account in serverlist:
        target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
        print("")
        print("Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'])
        mgn_client = target_account_session.client("mgn", account['aws_region'])
        mgn_sourceservers = get_mgn_source_servers(mgn_client)
        for factoryserver in account['servers']:
            if 'server_fqdn' not in factoryserver:
                print("ERROR: server_fqdn does not exist for server: " + factoryserver['server_name'])
                sys.exit(1)
            else:
                sourceserver = mfcommon.get_mgn_source_server(
                    factoryserver, mgn_sourceservers)
                if sourceserver is not None:
                    update_target_instance_id(sourceserver, factoryserver, account)
    return serverlist


def update_target_instance_id(sourceserver, factoryserver, account):
    # Get target instance Id for the source server in Application Migration Service
    # at this point sourceserver['isArchived'] should be False, but double check
    if not sourceserver['isArchived']:
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
        sys.exit(1)


def get_instance_ips(instance_list, waveid):
    all_instance_ips = []
    for account in instance_list:
        target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
        print("")
        print("######################################################")
        print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
        print("######################################################")
        ec2_client = target_account_session.client("ec2", region_name=account['aws_region'])
        instance_ids = get_instance_ids(account)
        if len(instance_ids) != 0:
            ec2_desc = ec2_client.describe_instances(InstanceIds=instance_ids)
        else:
            print("")
            print("*** No target instances available for this wave ***")
            return

        for r in ec2_desc['Reservations']:
            extract_instance_ids_from_ec2_reservation(r, all_instance_ips)
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


def get_instance_ids(account):
    instance_ids = []
    for server in account['servers']:
        if 'target_ec2InstanceID' in server:
            if server['target_ec2InstanceID'] != '':
                instance_ids.append(server['target_ec2InstanceID'])

    return instance_ids


def extract_instance_ids_from_ec2_reservation(r, all_instance_ips):
    for instance in r['Instances']:
        instance_ips = {}
        instance_name = ""
        ips = ""
        name_exist = False
        for tag in instance['Tags']:
            if tag['Key'] == "Name" and tag['Value'] != "":
                instance_name = tag['Value']
                name_exist = True
        if not name_exist:
            print("ERROR: Name Tag does not exist for instance " + instance['InstanceId'])
            sys.exit(1)
        for nic in instance['NetworkInterfaces']:
            for ip in nic['PrivateIpAddresses']:
                ips = ips + ip['PrivateIpAddress'] + ","
        instance_ips['instance_name'] = instance_name
        instance_ips['instance_ips'] = ips[:-1]
        print(instance_name + " , " + ips[:-1])
        all_instance_ips.append(instance_ips)


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
    print("*Login to Migration factory*")
    token = mfcommon.factory_login()

    print("*** Getting Server List ****")
    get_servers = mfcommon.get_factory_servers(
        waveid=args.Waveid,
        app_ids=mfcommon.parse_list(args.AppIds),
        server_ids=mfcommon.parse_list(args.ServerIds),
        token=token,
        os_split=False,
        rtype='Rehost'

    )

    print("******************************")
    print("* Getting Target Instance Id *")
    print("******************************")

    instance_list = get_instance_id(get_servers)
    print("")
    print("*****************************")
    print("* Get target Instance IPs *")
    print("*****************************")

    get_instance_ips(instance_list, args.Waveid)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
