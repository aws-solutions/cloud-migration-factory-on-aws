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
if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko
import boto3
import botocore.exceptions
import mfcommon

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint
windows_fail = 0
linux_fail = 0
def check_windows(Servers_Windows, RDPPort):
    global windows_fail
    for s in Servers_Windows:
        command = "(Test-NetConnection -ComputerName " + s["server_fqdn"] + " -Port " + RDPPort + ").TcpTestSucceeded"
        p = subprocess.Popen(["powershell.exe", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tcpresult = False
        output, error = p.communicate()
        if (output):
            print(" RDP test to Server " + s["server_fqdn"] + " : Pass", flush = True)
        else:
            print(" RDP test to Server " + s["server_fqdn"] + " : Fail", flush = True)
            windows_fail += 1
    return windows_fail


def check_ssh_connectivity(ip, user_name, pass_key, is_key, SSHPort):
    global linux_fail
    ssh, error = open_ssh(ip, user_name, pass_key, is_key, SSHPort)
    if ssh is None or len(error) > 0:
        print(" SSH test to server " + ip + " : Fail", flush = True)
        linux_fail += 1
    else:
        print(" SSH test to server " + ip + " : Pass", flush = True)
    return linux_fail

def open_ssh(host, username, key_pwd, using_key, SSHPort):
    ssh = None
    error = ''
    try:
        if using_key:
            from io import StringIO
            private_key = paramiko.RSAKey.from_private_key(StringIO(key_pwd))
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
    parser.add_argument('--NoPrompts', default=False, type=bool, help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretLinux', default=None)
    args = parser.parse_args(arguments)

    UserHOST = ""

    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit(1)

    print("****************************")
    print("*Login to Migration factory*")
    print("****************************", flush = True)
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************", flush = True)
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST)
    user_name = ''
    pass_key = ''
    key_exist = False
    windows_status = 0
    linux_status = 0


    print("")

    if windows_exist:
        print("")
        print("*********************************************")
        print("*Checking RDP Access for Windows servers*")
        print("*********************************************")
        print("", flush = True)
        for account in get_servers:
            if len(account["servers_windows"]) > 0:
                windows_status = check_windows(account["servers_windows"], args.RDPPort)

    if linux_exist:
        print("")
        print("********************************************")
        print("*Checking SSH connections for Linux servers*")
        print("********************************************")
        print("", flush = True)
        for account in get_servers:
            if len(account["servers_linux"]) > 0:
                for server in account["servers_linux"]:
                   linux_credentials = mfcommon.getServerCredentials(user_name, pass_key, server, args.SecretLinux, args.NoPrompts)
                   linux_status = check_ssh_connectivity(server["server_fqdn"], linux_credentials['username'], linux_credentials['password'], key_exist, args.SSHPort)

    if windows_status > 0 or linux_status > 0:
        print("One or more servers failed to pass the connection check. Check log for details.")
        return 1
    else:
        print("All servers have had server connection check completed successfully.")
        return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
