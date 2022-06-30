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

import sys
import argparse
import json
import requests
import getpass
import paramiko
import mfcommon

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
                print("User %s was created successfully on host %s" %(new_user_name, host))
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
    parser.add_argument('--CloudEndureProjectName', default="")
    args = parser.parse_args(arguments)

    UserHOST = endpoints['UserApiUrl']
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
    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************")
    Servers_Windows, Servers_Linux = mfcommon.ServerList(args.Waveid, token, UserHOST,
                                                args.CloudEndureProjectName)

    if len(Servers_Linux) > 0:
        print("******************************************")
        print("* Enter Linux Sudo username and password *")
        print("******************************************")
        admin_usr_name = input("Linux admin user name: ")
        has_key = input("If you use a private key to login, press [Y] or if use password press [N]: ")
        if has_key.lower() in 'y':
            pass_key = input('Private Key file name: ')
        else:
            pass_key_first = getpass.getpass('Linux Password: ')
            pass_key_second = getpass.getpass('Re-enter Password: ')
            while(pass_key_first != pass_key_second):
                print("Password mismatch, please try again!")
                pass_key_first = getpass.getpass('Linux Password: ')
                pass_key_second = getpass.getpass('Re-enter Password: ')
            pass_key = pass_key_second
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
            for server in Servers_Linux:
                host = server["server_fqdn"]
                create_user(host, admin_usr_name, pass_key, has_key.lower() in
                        'y', new_user_name, new_password)
                print("")
        else:
            print("")
            print("**********************************************")
            print("*Deleting local sudo users on all the servers*")
            print("**********************************************")
            print("")
            new_user_name = input("Enter local User Name: ")
            print("")
            for server in Servers_Linux:
                host = server["server_fqdn"]
                delete_linux_user(host, admin_usr_name, pass_key, has_key.lower() in
                        'y', new_user_name)
                print("")
    else:
        print("ERROR: There are no Linux servers in this Wave")


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
