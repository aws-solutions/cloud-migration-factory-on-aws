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

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

def open_ssh(host, username, key_pwd, using_key):
    ssh = None
    try:
        if using_key:
            private_key = paramiko.RSAKey.from_private_key_file(key_pwd)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, pkey=private_key)
        else:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=key_pwd)
    except IOError as io_error:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(io_error)
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(ssh_exception)
        print(error)
    return ssh

def execute_cmd(host, username, key, cmd, using_key):
    output = ''
    error = ''
    ssh = None
    try:
        ssh = open_ssh(host, username, key, using_key)
        if ssh is None:
            error = "Not able to get the SSH connection for the host " + host
            print(error)
        else:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            for line in stdout.readlines():
                output = output + line
            for line in stderr.readlines():
                error = error + line
    except IOError as io_error:
        error = "Unable to execute the command " + cmd + " on " +host+ " due to " + \
                str(io_error)
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to execute the command " + cmd + " on " +host+ " due to " + \
                str(ssh_exception)
        print(error)
    except Exception as e:
        error = "Unable to execute the command " + cmd + " on " +host+ " due to " + str(e)
        print(error)
    finally:
        if ssh is not None:
            ssh.close()
    return output, error


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--WindowsUser', default="")
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
    print("*Getting Server List*")
    print("****************************")
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST)
    user_name = ''
    pass_key = ''
    key_exist = False
    if linux_exist:
        user_name, pass_key, key_exist = mfcommon.get_linux_password()

    if windows_exist:
        print("****************************")
        print("*Shutting down Windows servers*")
        print("****************************")

        if args.WindowsUser != "":
            windows_password = mfcommon.GetWindowsPassword()

        for account in get_servers:
            if len(account["servers_windows"]) > 0:
                for server in account["servers_windows"]:
                    command = "Stop-Computer -ComputerName " + server['server_fqdn'] + " -Force"
                    if args.WindowsUser != "":
                        command += " -Credential (New-Object System.Management.Automation.PSCredential(\"" + args.WindowsUser + "\", (ConvertTo-SecureString \"" + windows_password + "\" -AsPlainText -Force)))"
                    print("Shutting down server: " + server['server_fqdn'])
                    p = subprocess.Popen(["powershell.exe", command], stdout=sys.stdout)
                    p.communicate()
    if linux_exist:
        print("")
        print("****************************")
        print("*Shutting down Linux servers*")
        print("****************************")
        print("")
        for account in get_servers:
            if len(account["servers_linux"]) > 0:
                for server in account["servers_linux"]:
                    output, error = execute_cmd(server['server_fqdn'], user_name, pass_key, "sudo shutdown now", key_exist)
                    if not error:
                        print("Shutdown successful on " + server['server_fqdn'])
                    else:
                        print("unable to shutdown server " + server['server_fqdn'] + " due to " + error)
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
