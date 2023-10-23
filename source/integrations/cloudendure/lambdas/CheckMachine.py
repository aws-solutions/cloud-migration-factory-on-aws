#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from __future__ import print_function
import sys
import requests
import json
import os
import datetime


def status(session, headers, endpoint, HOST, project_id, launchtype, dryrun, serverlist, relaunch):
    testservers = ""
    cutoverservers = ""
    nottested = ""
    machine_status = 0
    REQUESTS_DEFAULT_TIMEOUT = 60
    m = requests.get(HOST + endpoint.format('projects/{}/machines').format(project_id),
                     headers=headers,
                     cookies=session,
                     timeout=REQUESTS_DEFAULT_TIMEOUT)
    for server in serverlist:
        machine_exist = False
        for machine in json.loads(m.text)["items"]:
            if server["server_name"].lower() == machine['sourceProperties']['name'].lower():
                machine_exist = True
                # Check if replication is done
                if 'lastConsistencyDateTime' not in machine['replicationInfo']:
                    return "ERROR: Machine: " + machine['sourceProperties'][
                        'name'] + " replication in progress, please wait for a few minutes...."
                else:
                    # check replication lag
                    a = int(machine['replicationInfo']['lastConsistencyDateTime'][11:13])
                    b = int(machine['replicationInfo']['lastConsistencyDateTime'][14:16])
                    x = int(datetime.datetime.utcnow().isoformat()[11:13])
                    y = int(datetime.datetime.utcnow().isoformat()[14:16])
                    result = (x - a) * 60 + (y - b)
                    if result > 180:
                        message = "ERROR: Machine: " + machine['sourceProperties'][
                            'name'] + " replication lag is more than 180 minutes...."
                        message = message + "- Current Replication lag for " + machine['sourceProperties'][
                            'name'] + " is: " + str(result) + " minutes...."
                        return message
                    else:
                        # Check dryrun flag and skip the rest of checks
                        if dryrun.lower() == "yes":
                            machine_status += 1
                        else:
                            if (relaunch == False):
                                # Check if the target machine has been tested already
                                if launchtype == "test":
                                    if 'lastTestLaunchDateTime' not in machine[
                                        "lifeCycle"] and 'lastCutoverDateTime' not in machine["lifeCycle"]:
                                        machine_status += 1
                                    else:
                                        testservers = testservers + server["server_name"] + ","
                                # Check if the target machine has been migrated to PROD already
                                elif launchtype == "cutover":
                                    if 'lastTestLaunchDateTime' in machine["lifeCycle"]:
                                        if 'lastCutoverDateTime' not in machine["lifeCycle"]:
                                            machine_status += 1
                                        else:
                                            cutoverservers = cutoverservers + server["server_name"] + ","
                                    else:
                                        nottested = nottested + server["server_name"] + ","
                            else:
                                machine_status += 1
        if machine_exist == False:
            return "ERROR: Machine: " + server["server_name"] + " does not exist in CloudEndure...."

    if launchtype == "test":
        if len(testservers) > 0:
            testservers = testservers[:-1]
            return "ERROR: Machine: " + testservers + " has been tested already...."
    if launchtype == "cutover":
        if len(cutoverservers) > 0 and len(nottested) == 0:
            cutoverservers = cutoverservers[:-1]
            return "ERROR: Machine: " + cutoverservers + " has been migrated already...."
        if len(cutoverservers) > 0 and len(nottested) > 0:
            cutoverservers = cutoverservers[:-1]
            nottested = nottested[:-1]
            return "ERROR: Machine: " + cutoverservers + " has been migrated already | ERROR: Machine: " + nottested + " has not been tested...."
        if len(cutoverservers) == 0 and len(nottested) > 0:
            nottested = nottested[:-1]
            return "ERROR: Machine: " + nottested + " has not been tested...."

    if machine_status == len(serverlist):
        print("All Machines are ready....")
        print("")
    else:
        return "ERROR: some machines are not ready...."
