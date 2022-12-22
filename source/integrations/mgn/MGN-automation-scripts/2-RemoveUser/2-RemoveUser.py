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

# Version: 09APR2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import subprocess
import getpass
if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko
import boto3
import botocore.exceptions
import mfcommon
import os

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

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
        return ssh
    except IOError as io_error:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(io_error)
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(ssh_exception)
        print(error)


def find_distribution(ssh):
    distribution = "linux"
    output = ''
    error = ''
    try:
        stdin, stdout, stderr = ssh.exec_command("cat /etc/*release")  # nosec B601
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
    except IOError as io_error:
        error = "Unable to find distribution due to " + str(io_error)
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to find distribution due to " + str(ssh_exception)
        print(error)
    if "ubuntu" in output:
        distribution = "ubuntu"
    elif "fedora" in output:
        distribution = "fedora"
    elif "suse" in output:
        distribution = "suse"
    return distribution


def get_add_user_cmd(ssh, new_user_name, new_user_password):
    try:
        distribution = find_distribution(ssh)
        if "ubuntu" in distribution:
            command = 'sudo useradd -m ' + new_user_name + ' -p ' + new_user_password + ' -G sudo'
        else:
            command = 'sudo adduser -m ' + new_user_name + ' -p ' + new_user_password + ' -g wheel'
    except Exception as ex:
        print("Error while fetching add user command due to " + str(ex))
    else:
        return command


def create_user(host, system_login_username, system_key_pwd, using_key, new_user_name, new_password):
    if not (new_user_name and new_password):
        print("User name or password cannot be null or empty for the new user")
        return
    ssh_client = None
    status = True
    try:
        ssh_client = open_ssh(host, system_login_username, system_key_pwd, using_key)
        try:
            add_user_cmd = get_add_user_cmd(ssh_client, new_user_name, new_password)
            no_password_sudoers_cmd = "sudo sh -c \"echo '" + new_user_name + " ALL=NOPASSWD: ALL' >> /etc/sudoers\""
            ssh_client.exec_command(add_user_cmd)  # nosec B601
            ssh_client.exec_command("sleep 2")  # nosec B601
            stdin, stdout, stderr = ssh_client.exec_command("cut -d: -f1 /etc/passwd")  # nosec B601
            users_output_str = stdout.read().decode("utf-8")
            users_list = users_output_str.split("\n")
            if new_user_name in users_list:
                print("")
                print("User %s got created successfully on host %s" %(new_user_name, host))
                ssh_client.exec_command(no_password_sudoers_cmd)  # nosec B601
                print("Modified sudoers to set NOPASSWORD for user " + new_user_name)
            else:
                print("User %s not created on host %s" % (new_user_name, host))
        except paramiko.SSHException as ssh_exception:
            error = "Server fails to execute the AddUser command on host " + host + " with username " + \
                    new_user_name + " due to " + str(ssh_exception)
            print(error)
            status = False
    except Exception as ex:
        error = "Error while creating user on host " + host + " with username " + \
                new_user_name + " due to " + str(ex)
        print(error)
        status = False
    finally:
        if ssh_client:
            ssh_client.close()
    return status


def delete_linux_user(host, system_login_username, system_key_pwd, using_key, username_to_delete):
    if not username_to_delete:
        print("User name to delete cannot be null or empty")
        return
    ssh_client = None
    status = True
    try:
        ssh_client = open_ssh(host, system_login_username, system_key_pwd, using_key)
        try:
            delete_user_cmd = 'sudo userdel -r ' + username_to_delete
            ssh_client.exec_command(delete_user_cmd)  # nosec B601
            ssh_client.exec_command("sleep 2")  # nosec B601
            stdin, stdout, stderr = ssh_client.exec_command("cut -d: -f1 /etc/passwd")  # nosec B601
            users_output_str = stdout.read().decode("utf-8")
            users_list = users_output_str.split("\n")
            if not username_to_delete in users_list:
                print("User deleted successfully on " + host)
            else:
                print("Deletion of user %s is not successfull on %s" %(
                    username_to_delete, host))
                status = False
        except paramiko.SSHException as ssh_exception:
            error = "Server fails to execute the remove user on host " + host + " with username " + \
                    username_to_delete + " due to " + str(ssh_exception)
            print(error)
            status = False
    except Exception as ex:
        error = "Error while deleting user on host " + host + " with username " + \
                username_to_delete + " due to " + str(ex)
        print(error)
        status = False
    finally:
        if ssh_client:
            ssh_client.close()
    return status
def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--NoPrompts', default=False, type=bool, help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--LocalUserSecret', default=None)
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
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST, True, 'Rehost')
    count = 0
    for account in get_servers:
        if len(account["servers_windows"]) > 0:
            for server in account["servers_windows"]:
                try :
                    cred = mfcommon.getServerCredentials("", "", server, args.SecretWindows, args.NoPrompts)
                    if cred['username'] != "":
                        if "\\" not in cred['username'] and "@" not in cred['username']:
                            #Assume local account provided, prepend server name to user ID.
                            server_name_only = server["server_fqdn"].split(".")[0]
                            cred['username'] = server_name_only + "\\" + cred['username']
                            print("INFO: Using local account to connect: " + cred['username'])
                        else:
                            print("INFO: Using domain account to connect: " + cred['username'])
                    local_user = mfcommon.getServerCredentials("", "", server, args.LocalUserSecret, args.NoPrompts)
                    creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + cred['username'] + "', (ConvertTo-SecureString '" + cred['password'] + "' -AsPlainText -Force)))"
                    p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server["server_fqdn"] + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    command1 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {net user " + local_user['username'] + " /delete}" + creds
                    print("------------------------------------------------------")
                    print("- Deleting a local user on: " + server['server_fqdn'] + " -")
                    print("------------------------------------------------------")
                    p = subprocess.Popen(["powershell.exe", command1], stdout=subprocess.PIPE,stderr = subprocess.PIPE)
                    stdout, stderr = p.communicate()
                    if 'ErrorId' in  str(stderr):
                        print(str(stderr))
                        count+=1
                    else:
                        print(local_user['username'] + " user removed from server: " + server['server_fqdn'])
                    print("")
                except:
                    count+=1
                    print("User creation failed on server: " + server['server_fqdn'])

        if len(account["servers_linux"]) > 0:
            for server in account["servers_linux"]:
                status = True
                host = server["server_fqdn"]
                cred = mfcommon.getServerCredentials("", "", server, args.SecretLinux, args.NoPrompts)
                new_user = mfcommon.getServerCredentials("", "", server, args.LocalUserSecret, args.NoPrompts)
                status = delete_linux_user(host, cred['username'], cred['password'], cred['private_key'], new_user['username'])
                if not status:
                    count+=1
                    print(new_user['username'] + "- user deletion failed on server: " + server['server_fqdn'])

    if (count > 0):
        print( "User deletion failed on one or more servers. Check log for details.")
        return 1
    else:
        print("User deletion completed successfully all servers.")
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
