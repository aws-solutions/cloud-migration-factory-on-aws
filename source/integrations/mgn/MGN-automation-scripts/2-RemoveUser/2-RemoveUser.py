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
import mfcommon


def find_distribution(ssh):
    distribution = "linux"
    output = ''
    error = ''
    try:
        _, stdout, stderr = ssh.exec_command("cat /etc/*release")  # nosec B601
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


def delete_linux_user(host, system_login_username, system_key_pwd, using_key, username_to_delete):
    if not username_to_delete:
        print("User name to delete cannot be null or empty")
        return
    ssh_client = None
    status = True
    try:
        ssh_client, error = mfcommon.open_ssh(host, system_login_username, system_key_pwd, using_key)
        if ssh_client is None:
            print(error)
            return False
        try:
            delete_user_cmd = 'sudo userdel -r ' + username_to_delete
            ssh_client.exec_command(delete_user_cmd)  # nosec B601
            ssh_client.exec_command("sleep 2")  # nosec B601
            _, stdout, _ = ssh_client.exec_command("cut -d: -f1 /etc/passwd")  # nosec B601
            users_output_str = stdout.read().decode("utf-8")
            users_list = users_output_str.split("\n")
            if username_to_delete not in users_list:
                print("User deleted successfully on " + host)
            else:
                print("Deletion of user %s is not successfull on %s" % (
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


def process_user_remove_for_linux_servers(cmf_servers, current_user_secret, remove_user_secret, no_prompts=True):
    failure_count = 0
    for server in cmf_servers:
        status = True
        host = server["server_fqdn"]
        cred = mfcommon.get_server_credentials(
            "", "", server, current_user_secret, no_prompts)
        new_user = mfcommon.get_server_credentials(
            "", "", server, remove_user_secret, no_prompts)
        status = delete_linux_user(host, cred['username'], cred['password'], cred['private_key'],
                                   new_user['username'])
        if not status:
            failure_count += 1
            print(new_user['username'] + "- user deletion failed on server: " + server['server_fqdn'])

    return failure_count


def process_user_remove_for_windows_servers(cmf_servers, current_user_secret, remove_user_secret, no_prompts=True):
    failure_count = 0

    mfcommon.add_windows_servers_to_trusted_hosts(cmf_servers)

    for server in cmf_servers:
        try:
            cred = mfcommon.get_server_credentials(
                "", "", server, current_user_secret, no_prompts)
            if cred['username'] != "":
                if "\\" not in cred['username'] and "@" not in cred['username']:
                    # Assume local account provided, prepend server name to user ID.
                    server_name_only = server["server_fqdn"].split(".")[0]
                    cred['username'] = server_name_only + "\\" + cred['username']
                    print("INFO: Using local account to connect: " + cred['username'])
                else:
                    print("INFO: Using domain account to connect: " +
                          cred['username'])
            local_user = mfcommon.get_server_credentials(
                "", "", server, remove_user_secret, no_prompts)
            creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + cred[
                'username'] + "', (ConvertTo-SecureString '" + cred['password'] + "' -AsPlainText -Force)))"

            command1 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {net user '" + \
                       local_user['username'] + "' /delete}" + creds
            print("------------------------------------------------------")
            print("- Deleting a local user on: " + server['server_fqdn'] + " -")
            print("------------------------------------------------------")
            p = subprocess.Popen(["powershell.exe", command1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, stderr = p.communicate()
            if 'ErrorId' in str(stderr):
                print(str(stderr))
                failure_count += 1
            else:
                print(local_user['username'] + " user removed from server: " + server['server_fqdn'])
            print("")
        except Exception as e:
            print("Exception:", e)
            failure_count += 1
            print("User creation failed on server: " + server['server_fqdn'])

    return failure_count


def process_user_remove_for_servers(cmf_servers, args):
    failure_count = 0
    for account in cmf_servers:
        if len(account["servers_windows"]) > 0:
            failure_count += process_user_remove_for_windows_servers(
                account["servers_windows"],
                args.SecretWindows,
                args.RemoveSecretWindows,
                args.NoPrompts
            )

        if len(account["servers_linux"]) > 0:
            failure_count += process_user_remove_for_linux_servers(
                account["servers_linux"],
                args.SecretLinux,
                args.RemoveSecretLinux,
                args.NoPrompts
            )

    return failure_count


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--AppIds', default=None)
    parser.add_argument('--ServerIds', default=None)
    parser.add_argument('--NoPrompts', default=False, type=mfcommon.parse_boolean,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--RemoveSecretWindows', default=None)
    parser.add_argument('--RemoveSecretLinux', default=None)
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    args = parser.parse_args(arguments)

    print("*Login to Migration factory*")
    token = mfcommon.factory_login()

    print("*Getting Server List*", flush=True)
    get_servers, _, _ = mfcommon.get_factory_servers(
        waveid=args.Waveid,
        app_ids=mfcommon.parse_list(args.AppIds),
        server_ids=mfcommon.parse_list(args.ServerIds),
        token=token,
        os_split=True,
        rtype='Rehost'

    )
    remove_user_failure_count = process_user_remove_for_servers(get_servers, args)

    if remove_user_failure_count > 0:
        print("User deletion failed on one or more servers. Check log for details.", flush=True)
        return 1
    else:
        print("User deletion completed successfully all servers.", flush=True)
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
