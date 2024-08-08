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
import subprocess

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


def create_user(host, system_login_username, system_key_pwd, using_key, new_user_name, new_password):
    if not (new_user_name and new_password):
        print("User name or password cannot be null or empty for the new user")
        return
    ssh_client = None
    status = True
    try:
        ssh_client, ssh_error = mfcommon.open_ssh(host, system_login_username, system_key_pwd, using_key)
        if ssh_client is None:
            print(ssh_error)
            return False
        try:
            add_user_cmd = get_add_user_cmd(ssh_client, new_user_name, new_password)
            no_password_sudoers_cmd = "sudo sh -c \"echo '" + new_user_name + " ALL=NOPASSWD: ALL' >> /etc/sudoers\""
            ssh_client.exec_command(add_user_cmd)  # nosec B601
            ssh_client.exec_command("sleep 2")  # nosec B601
            _, stdout, _ = ssh_client.exec_command("cut -d: -f1 /etc/passwd")  # nosec B601
            users_output_str = stdout.read().decode("utf-8")
            users_list = users_output_str.split("\n")
            if new_user_name in users_list:
                print("")
                print("User %s created successfully on host %s" % (new_user_name, host))
                ssh_client.exec_command(no_password_sudoers_cmd)  # nosec B601
                print("Modified sudoers to set NOPASSWORD for user " + new_user_name)
            else:
                print("User %s not created on host %s" % (new_user_name, host))
        except paramiko.SSHException as ssh_exception:
            error = (f"Server fails to execute the AddUser command on host {host}  with username {new_user_name} "
                     f"due to {str(ssh_exception)}")
            print(error)
            status = False
    except Exception as ex:
        error = f"Error while creating user on host {host} with username {new_user_name} due to {str(ex)}"
        print(error)
        status = False
    finally:
        if ssh_client:
            ssh_client.close()
    return status


def process_user_add_for_linux_servers(cmf_servers, current_user_secret, new_user_secret, no_prompts=True):
    failure_count = 0
    for server in cmf_servers:
        status = True
        host = server["server_fqdn"]
        cred = mfcommon.get_server_credentials(
            "", "", server, current_user_secret, no_prompts)
        new_user = mfcommon.get_server_credentials(
            "", "", server, new_user_secret, no_prompts)
        status = create_user(host, cred['username'], cred['password'], cred['private_key'],
                             new_user['username'], new_user['password'])
        if not status:
            failure_count += 1
            print("User creation failed on server: " + server['server_fqdn'])

    return failure_count


def process_user_add_for_windows_servers(cmf_servers, current_user_secret, new_user_secret, no_prompts=True):
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
            new_user = mfcommon.get_server_credentials(
                "", "", server, new_user_secret, no_prompts)
            creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + cred[
                'username'] + "', (ConvertTo-SecureString '" + cred['password'] + "' -AsPlainText -Force)))"

            command1 = f'Invoke-Command -ComputerName {server["server_fqdn"]} -ScriptBlock {{net user "{new_user["username"]}" "{new_user["password"]}" /add}}{creds}'
            print("------------------------------------------------------")
            print("- Creating a local user on: " + server['server_fqdn'] + " -")
            print("------------------------------------------------------")
            p = subprocess.Popen(["powershell.exe", command1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            print(str(stdout))
            print(str(stderr))
            command2 = "Invoke-Command -ComputerName " + server[
                'server_fqdn'] + " -ScriptBlock {net localgroup Administrators " + new_user[
                           'username'] + " /add}" + creds
            print("Adding user to local admin group on server: " + server['server_fqdn'])
            p = subprocess.Popen(["powershell.exe", command2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, stderr = p.communicate()
            if 'ErrorId' in str(stderr):
                print(str(stderr))
                failure_count += 1
            else:
                print("User added for server: " + server['server_fqdn'])
            print("")
        except Exception as e:
            print("Exception:", e)
            failure_count += 1
            print("User creation failed on server: " + server['server_fqdn'])

    return failure_count


def process_user_add_for_servers(cmf_servers, args):
    failure_count = 0
    for account in cmf_servers:
        if len(account["servers_windows"]) > 0:
            failure_count += process_user_add_for_windows_servers(
                account["servers_windows"],
                args.SecretWindows,
                args.NewSecretWindows,
                args.NoPrompts
            )

        if len(account["servers_linux"]) > 0:
            failure_count += process_user_add_for_linux_servers(
                account["servers_linux"],
                args.SecretLinux,
                args.NewSecretLinux,
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
    parser.add_argument('--NewSecretWindows', default=None)
    parser.add_argument('--NewSecretLinux', default=None)
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

    user_add_failure_count = process_user_add_for_servers(get_servers, args)

    if user_add_failure_count > 0:
        print("User creation failed on one or more servers. Check log for details.", flush=True)
        return 1
    else:
        print("User creation completed successfully all servers.", flush=True)
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
