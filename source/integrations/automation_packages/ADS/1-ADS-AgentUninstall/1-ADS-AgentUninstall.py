#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 17MAY2021.01

from __future__ import print_function
import sys
import argparse
import subprocess
import time
import boto3
import botocore.exceptions
import mfcommon

POWERSHELL_EXE = "powershell.exe"

linuxpkg = __import__("1-ADS-Uninstall-Linux")


def add_window_servers_to_uninstall_queue(
    account,
    agent_windows_download_url,
    windows_secret_name,
    hard_uninstall_str='No',
    no_user_prompts=True,
    windows_use_ssl=False
):
    # Uninstalling agent on Windows servers
    if len(account['servers_windows']) > 0:
        mfcommon.add_windows_servers_to_trusted_hosts(account["servers_windows"])

        for server in account['servers_windows']:
            windows_credentials = mfcommon.get_server_credentials("", "", server,
                                                                  windows_secret_name, no_user_prompts)
            if windows_credentials['username'] != "":
                if "\\" not in windows_credentials['username'] and "@" not in windows_credentials['username']:
                    # Assume local account provided, prepend server name to user ID.
                    server_name_only = server["server_fqdn"].split(".")[0]
                    windows_credentials['username'] = server_name_only + "\\" + windows_credentials['username']
                    print("INFO: Using local account to connect: " + windows_credentials['username'])
                else:
                    print("INFO: Using domain account to connect: " + windows_credentials['username'])

                command = [POWERSHELL_EXE,
                           ".\\1-Uninstall-Windows.ps1",
                           "-Servername",
                           server['server_fqdn'],
                           "-windowsuser",
                           "'" + windows_credentials['username'] + "'",
                           "-windowspwd",
                           "'" + windows_credentials['password'] + "'",
                           "-harduninstall",
                           hard_uninstall_str,
                           "-agent_download_url",
                           agent_windows_download_url,
                           "-usessl",
                           "$" + str(windows_use_ssl).lower()
                           ]

                p = subprocess.Popen(command,
                                     stdout=sys.stdout)
            else:
                # User credentials of user executing the script (from remote execution jobs this will be localsystem account and so will not be able to access remote servers)
                p = subprocess.Popen(["powershell.exe",
                                      ".\\1-Uninstall-Windows.ps1", server['server_fqdn']],
                                     stdout=sys.stdout)
            p.communicate()


def add_linux_servers_to_uninstall_queue(account, linux_secret_name, no_user_prompts=True):
    # Uninstalling agent on Linux servers
    if len(account['servers_linux']) > 0:
        for server in account['servers_linux']:
            linux_credentials = mfcommon.get_server_credentials("", "", server,
                                                                linux_secret_name, no_user_prompts)

            linuxpkg.uninstall_ads(server['server_fqdn'], linux_credentials['username'],
                                   linux_credentials['password'],
                                   linux_credentials['private_key'])


def uninstall_ads_agents(get_servers, linux_secret_name=None, windows_secret_name=None, no_user_prompts=False,
                         hard_uninstall=False, windows_use_ssl=False):
    print(hard_uninstall)
    hard_uninstall_str = 'No'
    agent_windows_download_url = ''
    if hard_uninstall:
        hard_uninstall_str = 'Yes'
        agent_windows_download_url = ("https://s3.us-west-2.amazonaws.com/"
                                      "aws-discovery-agent.us-west-2/windows/latest/AWSDiscoveryAgentInstaller.exe")

    try:
        for account in get_servers:
            print("######################################################")
            print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
            print("######################################################")

            add_window_servers_to_uninstall_queue(
                account,
                agent_windows_download_url,
                windows_secret_name,
                hard_uninstall_str,
                no_user_prompts,
                windows_use_ssl
            )

            add_linux_servers_to_uninstall_queue(
                account,
                linux_secret_name,
                no_user_prompts=no_user_prompts
            )

            print("")

    except botocore.exceptions.ClientError as error:
        if ":" in str(error):
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            msg = "ERROR: " + err
            print(msg)
            sys.exit()
        else:
            msg = "ERROR: " + str(error)
            print(msg)
            sys.exit()


def parse_boolean(value):
    value = value.lower()

    if value in ["true", "yes", "y", "1", "t"]:
        return True
    elif value in ["false", "no", "n", "0", "f"]:
        return False

    return False


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--NoPrompts', default=False, type=parse_boolean,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    parser.add_argument('--HardUninstall', default=False, type=parse_boolean)
    parser.add_argument('--UseSSL', default=False, type=parse_boolean)

    args = parser.parse_args(arguments)

    print("")
    print("*Login to Migration factory*")
    token = mfcommon.factory_login()

    print("*** Getting Server List ***")
    get_servers, _, _ = mfcommon.get_factory_servers(args.Waveid, token)

    print("****************************")
    print("****Uninstalling Agents *****")
    print("****************************")
    print("")
    uninstall_ads_agents(
        get_servers,
        args.SecretLinux,
        args.SecretWindows,
        args.NoPrompts,
        args.HardUninstall,
        args.UseSSL
    )

    time.sleep(5)
    print("All servers have had ADS Agent uninstallation run. Check logs for details.")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
