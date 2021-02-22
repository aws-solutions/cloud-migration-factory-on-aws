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
import sys
import requests
import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr

application = os.environ['application']
environment = os.environ['environment']

servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)

servers_table = boto3.resource('dynamodb').Table(servers_table_name)
apps_table = boto3.resource('dynamodb').Table(apps_table_name)

def remove(session, headers, endpoint, HOST, projectname, waveid):
    cleanup = ""
    cleanupfail = ""
    serverlist = []
    applist = []
    
    # Get Projects
    r = requests.get(HOST + endpoint.format('projects'), headers=headers, cookies=session)
    if r.status_code != 200:
        return "ERROR: Failed to fetch the project...."
    try:
        # Get Project ID
        projects = json.loads(r.text)["items"]
        project_exist = False
        for project in projects:
            if project["name"] == projectname:
               project_id = project["id"]
               project_exist = True
        if project_exist == False:
            return "ERROR: Project Name does not exist in CloudEndure...."

        # Get all Apps and servers from migration factory
        getserver = scan_dynamodb_server_table()
        servers = sorted(getserver, key = lambda i: i['server_name'])

        getapp = scan_dynamodb_app_table()
        apps = sorted(getapp, key = lambda i: i['app_name'])

        # Get App list
        applist = []
        for app in apps:
            if 'wave_id' in app:
                if str(app['wave_id']) == str(waveid) and str(app['cloudendure_projectname']) == str(projectname):
                    applist.append(app['app_id'])
        # Get Server List
        for app in applist:
            for server in servers:
                if app == server['app_id']:
                    serverlist.append(server)
        if len(serverlist) == 0:
            return "ERROR: Serverlist for wave " + waveid + " in Migration Factory is empty...."
    except:
        print(sys.exc_info())
        sys.exit(6)

    m = requests.get(HOST + endpoint.format('projects/{}/machines').format(project_id), headers=headers, cookies=session)
    machine_status = 0
    for server in serverlist:
        machine_exist = False
        for machine in json.loads(m.text)["items"]:
           if server["server_name"].lower() == machine['sourceProperties']['name'].lower():
                  machine_exist = True
                  if 'lastCutoverDateTime' in machine["lifeCycle"]:
                      machine_data = {'machineIDs': [machine['id']]}
                      remove = requests.delete(HOST + endpoint.format('projects/{}/machines').format(project_id), data = json.dumps(machine_data), headers=headers, cookies=session)
                      if remove.status_code == 204:
                          print("Machine: " + machine['sourceProperties']['name'] + " has been removed from CloudEndure....")
                          cleanup = cleanup + server["server_name"] + ","
                          machine_status += 1
                      else:
                          return "ERROR: Machine: " + machine['sourceProperties']['name'] + " cleanup failed...."
                  else:
                      cleanupfail = cleanupfail + server["server_name"] + ","
        if machine_exist == False:
               return "ERROR: Machine: " + server["server_name"] + " does not exist in CloudEndure...."

    if len(cleanup) > 0 and len(cleanupfail) == 0:
       cleanup = cleanup[:-1]
       return "Server: " + cleanup + " have been removed from CloudEndure...."
    if len(cleanup) == 0 and len(cleanupfail) > 0:
       cleanupfail = cleanupfail[:-1]
       return "ERROR: Machine: " + cleanupfail + " has not been migrated to PROD environment...."
    if len(cleanup) > 0 and len(cleanupfail) > 0:
       cleanup = cleanup[:-1]
       cleanupfail = cleanupfail[:-1]
       return "Server: " + cleanup + " have been removed from CloudEndure.... | " + "ERROR: Machine: " + cleanupfail + " has not been migrated to PROD environment, please wait for 15 mins...."

# Pagination for server DDB table scan  
def scan_dynamodb_server_table():
    response = servers_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluate key for server is   " + str(response['LastEvaluatedKey']))
        response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])
    return(scan_data)

# Pagination for app DDB table scan  
def scan_dynamodb_app_table():
    response = apps_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluate key for app is   " + str(response['LastEvaluatedKey']))
        response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])
    return(scan_data)