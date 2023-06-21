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
import getpass
import datetime
import time
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
    r = requests.get(HOST + endpoint.format('projects'),
                     headers=headers,
                     cookies=session,
                     timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
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

def GetRegion(project_id):
    region_ids = []
    rep = requests.get(HOST + endpoint.format('projects/{}/replicationConfigurations').format(project_id),
                       headers=headers,
                       cookies=session,
                       timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
    for item in json.loads(rep.text)['items']:
        region = requests.get(HOST + endpoint.format('cloudCredentials/{}/regions/{}').format(item['cloudCredentials'], item['region']),
                              headers=headers,
                              cookies=session,
                              timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
        name = json.loads(region.text)['name']
        region_code = ""
        if "Northern Virginia" in name:
            region_code = 'us-east-1'
        elif "Frankfurt" in name:
            region_code = 'eu-central-1'
        elif "Paris" in name:
            region_code = 'eu-west-3'
        elif "Stockholm" in name:
            region_code = 'eu-north-1'
        elif "Northern California" in name:
            region_code = 'us-west-1'
        elif "Oregon" in name:
            region_code = 'us-west-2'
        elif "AWS GovCloud (US)" in name:
            region_code = 'us-gov-west-1'
        elif "Bahrain" in name:
            region_code = 'me-south-1'
        elif "Hong Kong" in name:
            region_code = 'ap-east-1'
        elif "Tokyo" in name:
            region_code = 'ap-northeast-1'
        elif "Singapore" in name:
            region_code = 'ap-southeast-1'
        elif "AWS GovCloud (US-East)" in name:
            region_code = 'us-gov-east-1'
        elif "Mumbai" in name:
            region_code = 'ap-south-1'
        elif "South America" in name:
            region_code = 'sa-east-1'
        elif "Sydney" in name:
            region_code = 'ap-southeast-2'
        elif "London" in name:
            region_code = 'eu-west-2'
        elif "Central" in name:
            region_code = 'ca-central-1'
        elif "Ireland" in name:
            region_code = 'eu-west-1'
        elif "Seoul" in name:
            region_code = 'ap-northeast-2'
        elif "Ohio" in name:
            region_code = 'us-east-2'
        else:
            print("Incorrect Region Name")
        region_ids.append(region_code)
    return region_ids

def GetServerList(projectname, waveid, token):
    try:
        # Get all Apps and servers from migration factory
        auth = {"Authorization": token}
        servers = json.loads(requests.get(UserHOST + serverendpoint,
                                          headers=auth,
                                          timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT).text)
        apps = json.loads(requests.get(UserHOST + appendpoint,
                                       headers=auth,
                                       timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT).text)

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
        m = requests.get(HOST + endpoint.format('projects/{}/machines').format(project_id),
                         headers=headers,
                         cookies=session,
                         timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
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
                            target_replica = requests.get(HOST + endpoint.format('projects/{}/replicas').format(project_id) + '/' + machine['replica'],
                                                          headers=headers,
                                                          cookies=session,
                                                          timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
                            # print(json.loads(target_replica.text))
                            InstanceInfo['InstanceName'] = machine['sourceProperties']['name'].lower()
                            InstanceInfo['InstanceId'] = json.loads(target_replica.text)['machineCloudId']
                            InstanceInfo["lifeCycle"] = machine["lifeCycle"]
                            InstanceList.append(InstanceInfo)
                    else:
                        print("ERROR: Target instance doesn't exist for machine: " + machine['sourceProperties']['name'])
                        sys.exit(12)
        return InstanceList

def verify_instance_status(InstanceList, serverlist, token, access_key_id, secret_access_key, region_ids):
    print("")
    auth = {"Authorization": token}
    found_in_region = None

    instanceIds = []
    for instance in InstanceList:
        instanceIds.append(instance['InstanceId'])

    for region_id in region_ids:
        ec2_client = boto3.client('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region_id)
        try:
            resp = ec2_client.describe_instance_status(InstanceIds=instanceIds, IncludeAllInstances=True)
            found_in_region = region_id
            print("INFO: Instance(s) found in region: " + found_in_region)
            break
        except:
            pass

    if found_in_region is not None:
        ec2_client = boto3.client('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=found_in_region)
    else:
        print("ERROR: Instances not found in Replication Regions.")

    print("")
    instance_not_ready = True
    count = 0
    while instance_not_ready:
        instance_not_ready = False
        instance_stopped = True
        while instance_stopped:
            resp = ec2_client.describe_instance_status(InstanceIds=instanceIds, IncludeAllInstances=True)
            instance_stopped_list = []
            instance_stopped = False
            for instance in InstanceList:
                for status in resp['InstanceStatuses']:
                    if status['InstanceState']['Name'] == "running":
                        if instance['InstanceId'] == status['InstanceId']:
                            if status['InstanceStatus']['Status'].lower() == "ok" and status['SystemStatus']['Status'].lower() == "ok":
                                instance['Status'] = "ok"
                            else:
                                instance['Status'] = "failed"
                    else:
                        instance_stopped = True
                if instance_stopped:
                    instance_stopped_list.append(instance['InstanceName'])
            if instance_stopped:
                print("-------------------------------------------------------------")
                print("- WARNING: the following instances are not in running state -")
                print("- Please wait for a few minutes                             -")
                print("-------------------------------------------------------------")
                for instance in instance_stopped_list:
                    print(" - " + instance)
                print("")
                print("*** Retry after 1 minute ***")
                print("")
                time.sleep(60)

        # Print out result
        server_passed = {}
        server_failed = {}
        for instance in InstanceList:
            if instance['Status'] == "ok":
                server_passed[instance['InstanceName']] = "ok"
            elif instance['Status'] == "failed":
                server_failed[instance['InstanceName']] = "failed"
        if len(server_passed) > 0:
            print("----------------------------------------------------")
            print("- The following instances PASSED 2/2 status checks -")
            print("----------------------------------------------------")
            for passed in server_passed.keys():
                print(passed)
            print("")
        if len(server_failed) > 0:
            instance_not_ready = True
            print("-----------------------------------------------------------------")
            print("- WARNING: the following instances FAILED 2/2 status checks -----")
            print("-----------------------------------------------------------------")
            for failed in server_failed.keys():
                print(failed)

        # Updating migration factory migration_status attributes
        for instance in InstanceList:
            lifeCycle = ""
            if 'lastCutoverDateTime' in instance['lifeCycle']:
                if 'lastTestLaunchDateTime' in instance['lifeCycle']:
                    if instance['lifeCycle']['lastCutoverDateTime'] > instance['lifeCycle']['lastTestLaunchDateTime']:
                        lifeCycle = "Cutover Launch - "
                    else:
                        lifeCycle = "Test Launch - "
                else:
                    lifeCycle = "Cutover Launch - "
            elif 'lastTestLaunchDateTime' in instance['lifeCycle']:
                lifeCycle = "Test Launch - "
            if instance['Status'] == "ok":
                serverattr = {"migration_status": lifeCycle + "2/2 status checks : Passed"}
            elif instance['Status'] == "failed":
                serverattr = {"migration_status": lifeCycle + "2/2 status checks : Failed"}
            for s in serverlist:
                if s['server_name'].lower() == instance['InstanceName'].lower():
                    updateserver = requests.put(UserHOST + serverendpoint + '/' + s['server_id'],
                                                headers=auth,
                                                data=json.dumps(serverattr),
                                                timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
            if updateserver.status_code == 401:
               print("Error: Access to migration_status attribute is denied")
               sys.exit(9)
            elif updateserver.status_code != 200:
               print("Error: Update migration_status attribute failed")
               sys.exit(10)

        if instance_not_ready:
            count = count + 1
            if count > 12:
                print("")
                print("*******************************    ERROR     **********************************")
                print("* Instances has FAILED 2/2 check for more than 1 hour, please contact support *")
                print("*******************************************************************************")
                sys.exit(14)
            print("")
            print("***********************************************")
            print("* Instance booting up - retry after 5 minutes *")
            print("***********************************************")
            print("")
            time.sleep(300)

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
    region_ids = GetRegion(project_id)
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
    print("** Verify instance  status **")
    print("*****************************")

    verify_instance_status(InstanceList, serverlist, token, input("AWS Access key id: "), getpass.getpass('Secret access key: '), region_ids)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
