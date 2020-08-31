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

application = os.environ["application"]
environment = os.environ["environment"]

servers_table_name = "{}-{}-servers".format(application, environment)
apps_table_name = "{}-{}-apps".format(application, environment)

servers_table = boto3.resource("dynamodb").Table(servers_table_name)
apps_table = boto3.resource("dynamodb").Table(apps_table_name)


def check(launchtype, session, headers, endpoint, HOST, projectname, waveid):
    serverlist = []
    applist = []
    r = requests.get(
        HOST + endpoint.format("projects"), headers=headers, cookies=session
    )
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

        getserver = servers_table.scan()["Items"]
        servers = sorted(getserver, key=lambda i: i["server_name"])

        getapp = apps_table.scan()["Items"]
        apps = sorted(getapp, key=lambda i: i["app_name"])

        # Get App list
        applist = []
        for app in apps:
            if "wave_id" in app:
                if str(app["wave_id"]) == str(waveid) and str(
                    app["cloudendure_projectname"]
                ) == str(projectname):
                    applist.append(app["app_id"])
        # Get Server List
        for app in applist:
            for server in servers:
                if app == server["app_id"]:
                    serverlist.append(server)
        if len(serverlist) == 0:
            return (
                "ERROR: Serverlist for wave "
                + waveid
                + " in Migration Factory is empty...."
            )
    except:
        print(sys.exc_info())
        sys.exit(6)

    machine_status = 0
    m = requests.get(
        HOST + endpoint.format("projects/{}/machines").format(project_id),
        headers=headers,
        cookies=session,
    )
    for server in serverlist:
        machine_exist = False
        for machine in json.loads(m.text)["items"]:
            if (
                server["server_name"].lower()
                == machine["sourceProperties"]["name"].lower()
                or server["server_fqdn"].lower()
                == machine["sourceProperties"]["name"].lower()
            ):
                machine_exist = True

            if machine_exist:
                if "lastConsistencyDateTime" not in machine["replicationInfo"]:
                    print(
                        "Machine: "
                        + machine["sourceProperties"]["name"]
                        + " replication in progress, please wait for a few minutes...."
                    )
                else:
                    if launchtype == "test":
                        if "lastTestLaunchDateTime" in machine["lifeCycle"]:
                            machine_status += 1
                            print(
                                "Machine: "
                                + machine["sourceProperties"]["name"]
                                + " has been migrated to the TEST environment...."
                            )
                        else:
                            print(
                                "Machine: "
                                + machine["sourceProperties"]["name"]
                                + " has NOT been migrated to the TEST environment, please wait...."
                            )
                    elif launchtype == "cutover":
                        if "lastCutoverDateTime" in machine["lifeCycle"]:
                            machine_status += 1
                            print(
                                "Machine: "
                                + machine["sourceProperties"]["name"]
                                + " has been migrated to the PROD environment...."
                            )
                        else:
                            print(
                                "Machine: "
                                + machine["sourceProperties"]["name"]
                                + " has NOT been migrated to the PROD environment...."
                            )
        if machine_exist == False:
            return (
                "ERROR: Name: "
                + server["server_name"]
                + " or FQDN: "
                + server["server_fqdn"]
                + " does not exist in CloudEndure...."
            )

    if machine_status == len(serverlist):
        if launchtype == "test":
            return "All Machines in the config file have been migrated to the TEST environment...."
        if launchtype == "cutover":
            return "All Machines in the config file have been migrated to the PROD environment...."
    else:
        if launchtype == "test":
            return "*WARNING*: Some machines in the config file have NOT been migrated to the TEST environment...."
        if launchtype == "cutover":
            return "*WARNING*: Some machines in the config file have NOT been migrated to the PROD environment...."
