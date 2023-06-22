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
headers = {'Content-Type': 'application/json'}
session = {}

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

UserHOST = endpoints['UserApiUrl']

def GetCEProject(projectname):
    r = requests.get(HOST + mfcommon.ce_endpoint.format('projects'),
                     headers=headers,
                     cookies=session,
                     timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
    if r.status_code != 200:
        print("ERROR: Failed to fetch the projects....")
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

def ProjectList(waveid, token, UserHOST, serverendpoint, appendpoint):
# Get all Apps and servers from migration factory
    auth = {"Authorization": token}
    servers = json.loads(requests.get(UserHOST + serverendpoint,
                                      headers=auth,
                                      timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT).text)
    #print(servers)
    apps = json.loads(requests.get(UserHOST + appendpoint,
                                   headers=auth,
                                   timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT).text)
    #print(apps)
    newapps = []

    CEProjects = []
    # Check project names in CloudEndure
    for app in apps:
        Project = {}
        if 'wave_id' in app:
            if str(app['wave_id']) == str(waveid):
                newapps.append(app)
                if 'cloudendure_projectname' in app:
                    Project['ProjectName'] = app['cloudendure_projectname']
                    project_id = GetCEProject(Project['ProjectName'])
                    Project['ProjectId'] = project_id
                    if Project not in CEProjects:
                        CEProjects.append(Project)
                else:
                    print("ERROR: App " + app['app_name'] + " is not linked to any CloudEndure project....")
                    sys.exit(5)
    Projects = GetServerList(newapps, servers, CEProjects, waveid)
    return Projects

def GetServerList(apps, servers, CEProjects, waveid):
    servercount = 0
    Projects = CEProjects
    for Project in Projects:
        ServersList = []
        for app in apps:
            if str(app['cloudendure_projectname']) == Project['ProjectName']:
                for server in servers:
                    if app['app_id'] == server['app_id']:
                        if 'server_os_family' in server:
                                if 'server_fqdn' in server:
                                        ServersList.append(server)
                                else:
                                    print("ERROR: server_fqdn for server: " + server['server_name'] + " doesn't exist")
                                    sys.exit(4)
                        else:
                            print ('server_os_family attribute does not exist for server: ' + server['server_name'] + ", please update this attribute")
                            sys.exit(2)
        Project['Servers'] = ServersList
        # print(Project)
        servercount = servercount + len(ServersList)
    if servercount == 0:
        print("ERROR: Serverlist for wave: " + waveid + " is empty....")
        sys.exit(3)
    else:
        return Projects


def verify_replication(projects, token):
    # Get Machine List from CloudEndure
    auth = {"Authorization": token}
    Not_finished = True
    while Not_finished:
        Not_finished = False
        replication_status = []
        for project in projects:
            print("")
            project_id = project['ProjectId']
            serverlist = project['Servers']
            m = requests.get(HOST + mfcommon.ce_endpoint.format('projects/{}/machines').format(project_id),
                             headers=headers,
                             cookies=session,
                             timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
            if "sourceProperties" not in m.text:
                print("ERROR: Failed to fetch the machines for project: " + project['ProjectName'])
                sys.exit(7)
            machine_status = {}
            replication_not_finished = False
            print("")
            print("***** Replication Status for CE Project: " + project['ProjectName'] + " *****")
            for server in serverlist:
                machine_exist = False
                for machine in json.loads(m.text)["items"]:
                    if server["server_name"].lower() == machine['sourceProperties']['name'].lower():
                        machine_exist = True
                        if 'lastConsistencyDateTime' not in machine['replicationInfo']:
                            steps = machine['replicationInfo']['initiationStates']['items'][-1]['steps']
                            laststep = ""
                            for step in reversed(steps):
                                if step['status'] == 'SUCCEEDED':
                                    laststep = step['name']
                                    break
                            if laststep == "ESTABLISHING_AGENT_REPLICATOR_COMMUNICATION":
                                if 'nextConsistencyEstimatedDateTime' in machine['replicationInfo']:
                                    a = int(machine['replicationInfo']['nextConsistencyEstimatedDateTime'][11:13])
                                    b = int(machine['replicationInfo']['nextConsistencyEstimatedDateTime'][14:16])
                                    x = int(datetime.datetime.utcnow().isoformat()[11:13])
                                    y = int(datetime.datetime.utcnow().isoformat()[14:16])
                                    result = (a - x) * 60 + (b - y)
                                    if result < 60:
                                        machine_status[server["server_name"]] = "Initial sync in progress, ETA: " + str(result) + " Minutes"
                                    else:
                                        hours = int(result / 60)
                                        machine_status[server["server_name"]] = "Initial sync in progress, ETA: " + str(hours) + " Hours"
                                else:
                                    machine_status[server["server_name"]] = "Initial sync in progress"
                            else:
                                machine_status[server["server_name"]] = laststep
                        else:
                            # check replication lag
                            a = int(machine['replicationInfo']['lastConsistencyDateTime'][11:13])
                            b = int(machine['replicationInfo']['lastConsistencyDateTime'][14:16])
                            x = int(datetime.datetime.utcnow().isoformat()[11:13])
                            y = int(datetime.datetime.utcnow().isoformat()[14:16])
                            result = (x - a) * 60 + (y - b)
                            if result > 60:
                                hours = int(result / 60)
                                machine_status[server["server_name"]] = "Replication lag: " + str(hours) + " Hours"
                            elif result > 5 and result <= 60:
                                machine_status[server["server_name"]] = "Replication lag: " + str(result) + " Minutes"
                            else:
                                machine_status[server["server_name"]] = "Continuous Data Replication"
                if machine_exist == False:
                    print("ERROR: Machine: " + server["server_name"] + " does not exist in CloudEndure....")
                    machine_status[server["server_name"]] = "Does not exist in CloudEndure"
            for server in serverlist:
                if machine_status[server["server_name"]] != "":
                    print ("Server " + server["server_name"] + " replication status: " + machine_status[server["server_name"]])
                    serverattr = {"replication_status": machine_status[server["server_name"]]}
                    if machine_status[server["server_name"]] != "Continuous Data Replication" and machine_status[server["server_name"]] != "Does not exist in CloudEndure":
                        replication_not_finished = True
                else:
                    print ("Server " + server["server_name"] + " replication status: Not Started" )
                    serverattr = {"replication_status": "Not Started"}
                    replication_not_finished = True
                updateserver = requests.put(UserHOST + mfcommon.serverendpoint + '/' + server['server_id'],
                                            headers=auth,
                                            data=json.dumps(serverattr),
                                            timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
                if updateserver.status_code == 401:
                    print("Error: Access to replication_status attribute is denied")
                    sys.exit(9)
                elif updateserver.status_code != 200:
                    print("Error: Update replication_status attribute failed")
                    sys.exit(10)
            replication_status.append(replication_not_finished)
        for status in replication_status:
            if status == True:
               Not_finished = True
        if Not_finished:
            print("")
            print("***************************************************")
            print("* Replication in progress - retry after 5 minutes *")
            print("***************************************************")
            time.sleep(300)

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
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

    print("***********************")
    print("* Getting Server List *")
    print("***********************")
    Projects = ProjectList(args.Waveid, token, UserHOST, mfcommon.serverendpoint, mfcommon.appendpoint)
    print("")
    for project in Projects:
        print("***** Servers for CE Project: " + project['ProjectName'] + " *****")
        for server in project['Servers']:
            print(server['server_name'])
        print("")
    print("")
    print("*****************************")
    print("* Verify replication status *")
    print("*****************************")
    verify_replication(Projects, token)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
