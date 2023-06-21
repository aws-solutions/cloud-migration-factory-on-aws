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

# Version: 29MAY2022.01

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
import os

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)


def open_ssh(host, username, key_pwd, using_key):
    ssh = None
    try:
        if using_key:
            from io import StringIO
            private_key = paramiko.RSAKey.from_private_key(StringIO(key_pwd))
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
            stdin, stdout, stderr = ssh.exec_command(cmd)  # nosec B601
            for line in stdout.readlines():
                output = output + line
            for line in stderr.readlines():
                error = error + line
    except IOError as io_error:
        error = "Unable to execute the command " + cmd + " on " + host + " due to " + \
                str(io_error)
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to execute the command " + cmd + " on " + host + " due to " + \
                str(ssh_exception)
        print(error)
    except Exception as e:
        error = "Unable to execute the command " + cmd + " on " + host + " due to " + str(e)
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
    parser.add_argument('--NoPrompts', default=False, type=bool,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretWindows', default=None)
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
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*Getting Server List*")
    print("****************************")
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST)
    user_name = ''
    pass_key = ''
    key_exist = False
    failures = False
    if windows_exist:
        print("****************************")
        print("*Shutting down Windows servers*")
        print("****************************", flush=True)

        for account in get_servers:
            if len(account["servers_windows"]) > 0:
                for server in account["servers_windows"]:
                    windows_credentials = mfcommon.getServerCredentials('', '', server, args.SecretWindows,
                                                                        args.NoPrompts)
                    if windows_credentials['username'] != "":
                        if "\\" not in windows_credentials['username'] and "@" not in windows_credentials['username']:
                            # Assume local account provided, prepend server name to user ID.
                            server_name_only = server["server_fqdn"].split(".")[0]
                            windows_credentials['username'] = server_name_only + "\\" + windows_credentials['username']
                            print("INFO: Using local account to connect: " + windows_credentials['username'])
                    else:
                        print("INFO: Using domain account to connect: " + windows_credentials['username'])
                    command = "Stop-Computer -Force"
                    print("Shutting down server: " + server['server_fqdn'], flush=True)

                    invoke_command = "Invoke-Command -ComputerName %s -ScriptBlock{%s}" % (server['server_fqdn'],
                                                                                           command)
                    invoke_command += " -Credential (New-Object System.Management.Automation.PSCredential('" + \
                                      windows_credentials['username'] + "', (ConvertTo-SecureString '" + \
                                      windows_credentials['password'] + "' -AsPlainText -Force)))"

                    p = subprocess.Popen(["powershell.exe", invoke_command], stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    stdout, stderr = p.communicate()
                    if 'ErrorId' in str(stderr):
                        print(str(stderr), flush=True)
                        failures = True
                    else:
                        print("Shutdown completed for server: " + server['server_fqdn'], flush=True)
    if linux_exist:
        print("")
        print("****************************")
        print("*Shutting down Linux servers*")
        print("****************************")
        print("", flush=True)
        for account in get_servers:
            if len(account["servers_linux"]) > 0:
                for server in account["servers_linux"]:
                    linux_credentials = mfcommon.getServerCredentials(user_name, pass_key, server, args.SecretLinux,
                                                                      args.NoPrompts)
                    output, error = execute_cmd(server['server_fqdn'], linux_credentials['username'],
                                                linux_credentials['password'], "sudo shutdown now",
                                                linux_credentials['private_key'])
                    if not error:
                        print("Shutdown successful on " + server['server_fqdn'], flush=True)
                    else:
                        print("unable to shutdown server " + server['server_fqdn'] + " due to " + error, flush=True)
                        failures = True
    if failures:
        print("One or more servers failed to shutdown. Check log for details.")
        return 1
    else:
        print("All servers have had shutdown completed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
