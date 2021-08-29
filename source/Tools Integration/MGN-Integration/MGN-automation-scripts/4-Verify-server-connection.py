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

# Version: 11APR2021.01

from __future__ import print_function
import sys
import argparse
import json
import subprocess
import paramiko
import boto3
import botocore.exceptions
import mfcommon

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

def check_windows(Servers_Windows, RDPPort):
    for s in Servers_Windows:
        command = "(Test-NetConnection -ComputerName " + s["server_fqdn"] + " -Port " + RDPPort + ").TcpTestSucceeded"
        p = subprocess.Popen(["powershell.exe", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tcpresult = False
        output, error = p.communicate()
        if (output):
            print(" RDP test to Server " + s["server_fqdn"] + " : Pass")
        else:
            print(" RDP test to Server " + s["server_fqdn"] + " : Fail")


def check_ssh_connectivity(ip, user_name, pass_key, is_key, SSHPort):
    ssh, error = open_ssh(ip, user_name, pass_key, is_key, SSHPort)
    if ssh is None or len(error) > 0:
        print(" SSH test to server " + ip + " : Fail")
        return None
    else:
        print(" SSH test to server " + ip + " : Pass")

def open_ssh(host, username, key_pwd, using_key, SSHPort):
    ssh = None
    error = ''
    try:
        if using_key:
            private_key = paramiko.RSAKey.from_private_key_file(key_pwd)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, port=SSHPort, username=username, pkey=private_key)
        else:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=key_pwd)
    except IOError as io_error:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(io_error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(ssh_exception)
    return ssh, error

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--SSHPort', default="22")
    parser.add_argument('--RDPPort', default="3389")
    args = parser.parse_args(arguments)

    UserHOST = ""

    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit()

    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************")
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST)
    user_name = ''
    pass_key = ''
    key_exist = False
    if linux_exist:
        user_name, pass_key, key_exist = mfcommon.get_linux_password()

    print("")

    if windows_exist:
        print("")
        print("*********************************************")
        print("*Checking RDP Access for Windows servers*")
        print("*********************************************")
        print("")
        for account in get_servers:
            if len(account["servers_windows"]) > 0:
                check_windows(account["servers_windows"], args.RDPPort)

    if linux_exist:
        print("")
        print("********************************************")
        print("*Checking SSH connections for Linux servers*")
        print("********************************************")
        print("")
        for account in get_servers:
            if len(account["servers_linux"]) > 0:
                for server in account["servers_linux"]:
                   check_ssh_connectivity(server["server_fqdn"], user_name, pass_key, key_exist, args.SSHPort)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
