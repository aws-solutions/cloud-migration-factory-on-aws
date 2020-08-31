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
import datetime


def status(
    session,
    headers,
    endpoint,
    HOST,
    project_id,
    launchtype,
    dryrun,
    serverlist,
    relaunch,
):
    testservers = ""
    cutoverservers = ""
    nottested = ""
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
            ):
                machine_exist = True
                server_id = server["server_name"].lower()
            elif (
                server["server_fqdn"].lower()
                == machine["sourceProperties"]["name"].lower()
            ):
                machine_exist = True
                server_id = server["server_fqdn"].lower()
                # Check if replication is done

            if machine_exist:
                if "lastConsistencyDateTime" not in machine["replicationInfo"]:
                    return (
                        "ERROR: Machine: "
                        + machine["sourceProperties"]["name"]
                        + " replication in progress, please wait for a few minutes...."
                    )
                else:
                    # check replication lag
                    a = int(
                        machine["replicationInfo"]["lastConsistencyDateTime"][11:13]
                    )
                    b = int(
                        machine["replicationInfo"]["lastConsistencyDateTime"][14:16]
                    )
                    x = int(datetime.datetime.utcnow().isoformat()[11:13])
                    y = int(datetime.datetime.utcnow().isoformat()[14:16])
                    result = (x - a) * 60 + (y - b)
                    if result > 180:
                        message = (
                            "ERROR: Machine: "
                            + machine["sourceProperties"]["name"]
                            + " replication lag is more than 180 minutes...."
                        )
                        message = (
                            message
                            + "- Current Replication lag for "
                            + machine["sourceProperties"]["name"]
                            + " is: "
                            + str(result)
                            + " minutes...."
                        )
                        return message
                    else:
                        # Check dryrun flag and skip the rest of checks
                        if dryrun.lower() == "yes":
                            machine_status += 1
                        else:
                            if relaunch == False:
                                # Check if the target machine has been tested already
                                if launchtype == "test":
                                    if (
                                        "lastTestLaunchDateTime"
                                        not in machine["lifeCycle"]
                                        and "lastCutoverDateTime"
                                        not in machine["lifeCycle"]
                                    ):
                                        machine_status += 1
                                    else:
                                        testservers = testservers + server_id + ","
                                # Check if the target machine has been migrated to PROD already
                                elif launchtype == "cutover":
                                    if "lastTestLaunchDateTime" in machine["lifeCycle"]:
                                        if (
                                            "lastCutoverDateTime"
                                            not in machine["lifeCycle"]
                                        ):
                                            machine_status += 1
                                        else:
                                            cutoverservers = (
                                                cutoverservers + server_id + ","
                                            )
                                    else:
                                        nottested = nottested + server_id + ","
                            else:
                                machine_status += 1
        if machine_exist == False:
            return (
                "ERROR: Name: "
                + server["server_name"]
                + " or FQDN: "
                + server["server_fqdn"]
                + " does not exist in CloudEndure...."
            )

    if launchtype == "test":
        if len(testservers) > 0:
            testservers = testservers[:-1]
            return "ERROR: Machine: " + testservers + " has been tested already...."
    if launchtype == "cutover":
        if len(cutoverservers) > 0 and len(nottested) == 0:
            cutoverservers = cutoverservers[:-1]
            return (
                "ERROR: Machine: " + cutoverservers + " has been migrated already...."
            )
        if len(cutoverservers) > 0 and len(nottested) > 0:
            cutoverservers = cutoverservers[:-1]
            nottested = nottested[:-1]
            return (
                "ERROR: Machine: "
                + cutoverservers
                + " has been migrated already | ERROR: Machine: "
                + nottested
                + " has not been tested...."
            )
        if len(cutoverservers) == 0 and len(nottested) > 0:
            nottested = nottested[:-1]
            return "ERROR: Machine: " + nottested + " has not been tested...."

    if machine_status == len(serverlist):
        print("All Machines are ready....")
        print("")
    else:
        return "ERROR: some machines are not ready...."
