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
import paramiko
import boto3
import botocore.exceptions
import mfcommon

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

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


def find_distribution(ssh):
    distribution = "linux"
    output = ''
    error = ''
    try:
        stdin, stdout, stderr = ssh.exec_command("cat /etc/*release")
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
    try:
        ssh_client = open_ssh(host, system_login_username, system_key_pwd, using_key)
        try:
            add_user_cmd = get_add_user_cmd(ssh_client, new_user_name, new_password)
            no_password_sudoers_cmd = "sudo sh -c \"echo '" + new_user_name + " ALL=NOPASSWD: ALL' >> /etc/sudoers\""
            ssh_client.exec_command(add_user_cmd)
            ssh_client.exec_command("sleep 2")
            stdin, stdout, stderr = ssh_client.exec_command("cut -d: -f1 /etc/passwd")
            users_output_str = stdout.read().decode("utf-8")
            users_list = users_output_str.split("\n")
            if new_user_name in users_list:
                print("")
                print("User %s got created successfully on host %s" %(new_user_name, host))
                ssh_client.exec_command(no_password_sudoers_cmd)
                print("Modified sudoers to set NOPASSWORD for user " + new_user_name)
            else:
                print("User %s not created on host %s" % (new_user_name, host))
        except paramiko.SSHException as ssh_exception:
            error = "Server fails to execute the AddUser command on host " + host + " with username " + \
                    new_user_name + " due to " + str(ssh_exception)
            print(error)
    except Exception as ex:
        error = "Error while creating user on host " + host + " with username " + \
                new_user_name + " due to " + str(ex)
        print(error)
    finally:
        if ssh_client:
            ssh_client.close()


def delete_linux_user(host, system_login_username, system_key_pwd, using_key, username_to_delete):
    if not username_to_delete:
        print("User name to delete cannot be null or empty")
        return
    ssh_client = None
    try:
        ssh_client = open_ssh(host, system_login_username, system_key_pwd, using_key)
        try:
            delete_user_cmd = 'sudo userdel -r ' + username_to_delete
            ssh_client.exec_command(delete_user_cmd)
            ssh_client.exec_command("sleep 2")
            stdin, stdout, stderr = ssh_client.exec_command("cut -d: -f1 /etc/passwd")
            users_output_str = stdout.read().decode("utf-8")
            users_list = users_output_str.split("\n")
            if not username_to_delete in users_list:
                print("User deleted successfully on " + host)
            else:
                print("Deletion of user %s is not successfull on %s" %(
                    username_to_delete, host))
        except paramiko.SSHException as ssh_exception:
            error = "Server fails to execute the AddUser command on host " + host + " with username " + \
                    username_to_delete + " due to " + str(ssh_exception)
            print(error)
    except Exception as ex:
        error = "Error while deleting user on host " + host + " with username " + \
                username_to_delete + " due to " + str(ex)
        print(error)
    finally:
        if ssh_client:
            ssh_client.close()

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

    target_os = ""
    target_os = input("Enter target OS (Windows or Linux): ")
    while target_os.lower() != 'windows' and target_os.lower() != 'linux':
        print("Please provide a valid OS, either Windows or Linux")
        target_os = input("ReEnter target OS (Windows or Linux): ")
        print("")

    choice_flag = True
    choice = 3
    while choice_flag:
        print("1. Create user")
        print("2. Delete user")
        print("3. Exit")
        choice = input("Enter your choice [1-3]: ")
        if choice == '3':
            sys.exit(0)
        elif choice != '1' and choice != '2':
            print("Please provide a valid option [1, 2, 3]")
            print("")
        else:
            choice_flag = False
    if target_os.lower() == 'windows':

        if args.WindowsUser != "":
            Windows_Password = mfcommon.GetWindowsPassword()
            creds = " -Credential (New-Object System.Management.Automation.PSCredential(\"" + args.WindowsUser + "\", (ConvertTo-SecureString \"" + Windows_Password + "\" -AsPlainText -Force)))"
        else:
            creds = ""

        if choice == '1':
            print("")
            print("************************************")
            print("*Creating local admin on the server*")
            print("************************************")
            LocalAdminUser = input("Enter new Local admin username: ")
            localadmin_pass_first = getpass.getpass('New local admin Password: ')
            localadmin_pass_second = getpass.getpass('Re-enter Password: ')
            while(localadmin_pass_first != localadmin_pass_second):
                print("Password mismatch, please try again!")
                localadmin_pass_first = getpass.getpass('New local admin Password: ')
                localadmin_pass_second = getpass.getpass('Re-enter Password: ')
            localadmin_pass = localadmin_pass_second
            print("")
            for account in get_servers:
                if len(account["servers_windows"]) > 0:
                    for server in account["servers_windows"]:
                        if args.WindowsUser != "":
                            p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server["server_fqdn"] + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        command1 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {net user " + LocalAdminUser + " " + localadmin_pass + " /add}" + creds
                        print("------------------------------------------------------")
                        print("- Creating a local user on: " + server['server_fqdn'] + " -")
                        print("------------------------------------------------------")
                        p = subprocess.Popen(["powershell.exe", command1], stdout=sys.stdout)
                        p.communicate()
                        command2 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {net localgroup Administrators " + LocalAdminUser + " /add}" + creds
                        print("Adding user to local admin group on server: " + server['server_fqdn'])
                        p = subprocess.Popen(["powershell.exe", command2], stdout=sys.stdout)
                        p.communicate()
            print("")
        else:
            print("")
            print("*************************************")
            print("*Deleting local admin on the servers*")
            print("*************************************")
            print("")
            LocalAdminUser = input("Enter local admin UserName to be deleted: ")
            print("")
            for account in get_servers:
                if len(account["servers_windows"]) > 0:
                    for server in account["servers_windows"]:
                        if args.WindowsUser != "":
                            p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server["server_fqdn"] + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        command1 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {net user " + LocalAdminUser + " /delete}" + creds
                        print("------------------------------------------------------")
                        print("- Deleting a local user on: " + server['server_fqdn'] + " -")
                        print("------------------------------------------------------")
                        p = subprocess.Popen(["powershell.exe", command1], stdout=sys.stdout)
                        p.communicate()
    elif target_os.lower() == 'linux':
        user_name = ''
        pass_key = ''
        key_exist = False
        user_name, pass_key, key_exist = mfcommon.get_linux_password()
        if choice == '1':
            print("")
            print("*********************************************")
            print("* Creating local sudo user on Linux servers *")
            print("*********************************************")
            print("")
            new_user_name = input("Enter New User Name: ")
            new_password = getpass.getpass('Enter New Password: ')
            confirm_password = getpass.getpass('Re-Enter New Password: ')
            while new_password != confirm_password:
                print('Both the passwords should match, Please try again!')
                new_password = getpass.getpass('Enter New Password: ')
                confirm_password = getpass.getpass('Re-Enter New Password: ')
            print("")
            for account in get_servers:
                if len(account["servers_linux"]) > 0:
                    for server in account["servers_linux"]:
                        host = server["server_fqdn"]
                        create_user(host, user_name, pass_key, key_exist, new_user_name, new_password)
        else:
            print("")
            print("**********************************************")
            print("*Deleting local sudo users on all the servers*")
            print("**********************************************")
            print("")
            new_user_name = input("Enter local User Name: ")
            print("")
            for account in get_servers:
                if len(account["servers_linux"]) > 0:
                    for server in account["servers_linux"]:
                        host = server["server_fqdn"]
                        delete_linux_user(host, user_name, pass_key, key_exist, new_user_name)
                        print("")


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
