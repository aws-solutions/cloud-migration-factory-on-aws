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

# Version: 23MAR2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import boto3
import botocore.exceptions
import getpass
import datetime
import csv
import mfcommon

HOST = mfcommon.ce_address
headers = mfcommon.ce_headers
session = {}
endpoint = mfcommon.ce_endpoint

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

UserHOST = endpoints['UserApiUrl']

def GetCEProject(projectname, session, headers, endpoint, HOST):
    r = requests.get(HOST + endpoint.format('projects'), headers=headers, cookies=session)
    if r.status_code != 200:
        print("ERROR: Failed to fetch the project....")
        sys.exit(2)
    try:
        # Get Project ID
        project_id = ""
        projects = json.loads(r.text)["items"]
        project_exist = False
        for project in projects:
            if project["name"] == projectname:
               project_id = project["id"]
               project_exist = True
        if project_exist == False:
            print("ERROR: Project Name does not exist in CloudEndure....")
            sys.exit(3)
        return project_id
    except:
        print("ERROR: Failed to fetch the project....")
        sys.exit(4)

def GetServerList(projectname, waveid, token):
    try:
        # Get all Apps and servers from migration factory
        auth = {"Authorization": token}
        servers = json.loads(requests.get(UserHOST + serverendpoint, headers=auth).text)
        apps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)

        # Get App list
        applist = []
        for app in apps:
            if 'wave_id' in app and 'cloudendure_projectname' in app:
                if str(app['wave_id']) == str(waveid) and str(app['cloudendure_projectname']) == str(projectname):
                    applist.append(app['app_id'])
        # Get Server List
        serverlist = []
        for app in applist:
            for server in servers:
                if "app_id" in server:
                    if app == server['app_id']:
                        serverlist.append(server)
        if len(serverlist) == 0:
            print("ERROR: Serverlist for wave " + waveid + " in Migration Factory is empty....")
            sys.exit(5)
        return serverlist
    except:
        print("ERROR: Getting server list failed....")
        sys.exit(6)

def GetInstanceId(project_id, serverlist, session, headers, endpoint, HOST, token):
        # Get Machine List from CloudEndure
        m = requests.get(HOST + endpoint.format('projects/{}/machines').format(project_id), headers=headers, cookies=session)
        if "sourceProperties" not in m.text:
            print("ERROR: Failed to fetch the machines....")
            sys.exit(11)
        InstanceList = []
        for s in serverlist:
            for machine in json.loads(m.text)["items"]:
                if s['server_name'].lower() == machine['sourceProperties']['name'].lower():
                    if 'replica' in machine:
                        if machine['replica'] != '':
                            InstanceInfo = {}
                            # print(machine['replica'])
                            target_replica = requests.get(HOST + endpoint.format('projects/{}/replicas').format(project_id) + '/' + machine['replica'], headers=headers, cookies=session)
                            # print(json.loads(target_replica.text))
                            InstanceInfo['InstanceName'] = machine['sourceProperties']['name'].lower()
                            InstanceInfo['InstanceId'] = json.loads(target_replica.text)['machineCloudId']
                            InstanceInfo["lifeCycle"] = machine["lifeCycle"]
                            InstanceList.append(InstanceInfo)
                    else:
                        print("ERROR: Target instance doesn't exist for machine: " + machine['sourceProperties']['name'])
                        sys.exit(12)
        return InstanceList

def get_instance_ips(InstanceList, serverlist, token, access_key_id, secret_access_key, region_ids, waveid, projectname):
        print("")
        auth = {"Authorization": token}
        instanceIds = []
        for instance in InstanceList:
            instanceIds.append(instance['InstanceId'])

        found_in_region = None
        for region_id in region_ids:
            ec2_client = boto3.client('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region_id)
            try:
                resp = ec2_client.describe_instance_status(InstanceIds=instanceIds)
                found_in_region = region_id
                print("INFO: Instance(s) found in region: " + found_in_region)
                break
            except botocore.exceptions.ClientError as error:
                if error.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                    # Instance might be in another region if there are mulitple replication configurations returned.
                    pass
                else:
                    print(error)
                    return
            except:
                pass

        if found_in_region is None:
            sep = ", "
            print("ERROR: Instance(s) not found in CE Replication Regions: " + sep.join(region_ids))
            return

        resp = ec2_client.describe_instances(InstanceIds=instanceIds)
        all_instance_ips = []
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
                    sys.exit(7)
                for nic in instance['NetworkInterfaces']:
                     for ip in nic['PrivateIpAddresses']:
                         ips = ips + ip['PrivateIpAddress'] + ","
                instance_ips['instance_name'] = instance_name
                instance_ips['instance_ips'] = ips[:-1]
                all_instance_ips.append(instance_ips)
        filename = "Wave" + waveid + "-" + projectname + "-IPs.csv"
        print("*** Exporting Instance IPs to " + filename + " ***")
        with open(filename, "w", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, all_instance_ips[0].keys())
            writer.writeheader()
            writer.writerows(all_instance_ips)

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--CloudEndureProjectName', required=True)
    parser.add_argument('--Waveid', required=True)
    args = parser.parse_args(arguments)

    print("******************************")
    print("* Login to Migration factory *")
    print("******************************")
    token = mfcommon.Factorylogin()

    print("")
    print("************************")
    print("* Login to CloudEndure *")
    print("************************")
    r_session, r_token = mfcommon.CElogin(input('CE API Token: '))
    if r_session is None:
        print("ERROR: CloudEndure Login Failed.")
        sys.exit(5)

    session['session'] = r_session

    if r_token is not None:
        headers['X-XSRF-TOKEN'] = r_token

    project_id = GetCEProject(args.CloudEndureProjectName, session, headers, endpoint, HOST)
    region_ids = mfcommon.GetCERegion(project_id, session, headers)

    print("***********************")
    print("* Getting Server List *")
    print("***********************")

    serverlist = GetServerList(args.CloudEndureProjectName, args.Waveid, token)
    for server in serverlist:
        print(server['server_name'])
    print("")

    print("******************************")
    print("* Getting Target Instance Id *")
    print("******************************")

    InstanceList = GetInstanceId(project_id, serverlist, session, headers, endpoint, HOST, token)
    for instance in InstanceList:
        print(instance['InstanceName'] + " : " + instance['InstanceId'])
    print("")
    print("*****************************")
    print("* Get target Instance  IPs *")
    print("*****************************")

    get_instance_ips(InstanceList, serverlist, token, input("AWS Access key id: "), getpass.getpass('Secret access key: '), region_ids, args.Waveid, args.CloudEndureProjectName)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
