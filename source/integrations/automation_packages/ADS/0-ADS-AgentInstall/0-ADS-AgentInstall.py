#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 17MAY2021.01

from __future__ import print_function
import sys
import argparse
import json
import subprocess
import time
import boto3
import botocore.exceptions
import mfcommon

linuxpkg = __import__("1-Install-Linux")


def assume_role(account_id, region):
    sts_client = boto3.client('sts')
    role_arn = 'arn:aws:iam::' + account_id + ':role/CMF-AutomationServer'
    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.
    try:
        user = sts_client.get_caller_identity()['Arn']
        sessionname = user.split('/')[1]
        response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=sessionname)
        credentials = response['Credentials']
        session = boto3.Session(
            region_name=region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        return session
    except botocore.exceptions.ClientError as e:
        print(str(e))
        return None


def install_ads_agents(force, get_servers, region, ads_secret_name, windows_user_name, windows_password,
                       linux_user_name, linux_pass_key, linux_secret_name=None,
                       windows_secret_name=None, no_user_prompts=False):
    try:
        if region != '':
            reinstall = 'No'
            if force == True:
                reinstall = 'Yes'
            for account in get_servers:
                print("######################################################")
                print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
                print("######################################################")

                agent_install_secrets = mfcommon.getCredentials(ads_secret_name)

                # Installing agent on Windows servers
                if len(account['servers_windows']) > 0:

                    agent_windows_download_url = "https://s3.us-west-2.amazonaws.com/aws-discovery-agent.us-west-2/windows/latest/AWSDiscoveryAgentInstaller.exe"

                    mfcommon.add_windows_servers_to_trusted_hosts(account["servers_windows"])

                    for server in account['servers_windows']:
                        windows_credentials = mfcommon.getServerCredentials(windows_user_name, windows_password, server,
                                                                            windows_secret_name, no_user_prompts)
                        if windows_credentials['username'] != "":
                            if "\\" not in windows_credentials['username'] and "@" not in windows_credentials[
                                'username']:
                                # Assume local account provided, prepend server name to user ID.
                                server_name_only = server["server_fqdn"].split(".")[0]
                                windows_credentials['username'] = server_name_only + "\\" + windows_credentials[
                                    'username']
                                print("INFO: Using local account to connect: " + windows_credentials['username'])
                            else:
                                print("INFO: Using domain account to connect: " + windows_credentials['username'])

                            p = subprocess.Popen(["powershell.exe",
                                                  ".\\1-Install-Windows.ps1", reinstall, agent_windows_download_url,
                                                  region, agent_install_secrets['secret_key'],
                                                  agent_install_secrets['secret_value'], server['server_fqdn'],
                                                  "'" + windows_credentials['username'] + "'",
                                                  "'" + windows_credentials['password'] + "'"],
                                                 stdout=sys.stdout)
                        else:
                            # User credentials of user executing the script (from remote execution jobs this will be localsystem account and so will not be able to access remote servers)
                            p = subprocess.Popen(["powershell.exe",
                                                  ".\\1-Install-Windows.ps1", reinstall, agent_windows_download_url,
                                                  region, agent_install_secrets['secret_value'],
                                                  agent_install_secrets['secret_key'], server['server_fqdn']],
                                                 stdout=sys.stdout)
                        p.communicate()
                # Installing agent on Linux servers
                if len(account['servers_linux']) > 0:
                    agent_linux_download_url = "https://s3-us-west-2.amazonaws.com/aws-discovery-agent.us-west-2/linux/latest/aws-discovery-agent.tar.gz"
                    for server in account['servers_linux']:
                        linux_credentials = mfcommon.getServerCredentials(linux_user_name, linux_pass_key, server,
                                                                          linux_secret_name, no_user_prompts)

                        linuxpkg.install_ads(agent_linux_download_url, region, server['server_fqdn'],
                                             linux_credentials['username'],
                                             linux_credentials['password'],
                                             linux_credentials['private_key'],
                                             agent_install_secrets['secret_key'],
                                             agent_install_secrets['secret_value'])
                print("")

        else:
            print("ERROR: Invalid or empty factory region")
            sys.exit()

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


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--ADSHomeRegion', required=True)
    parser.add_argument('--Force', default=False)
    parser.add_argument('--NoPrompts', default=False, type=bool,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    parser.add_argument('--SecretADSAgents', required=True)

    args = parser.parse_args(arguments)

    print("")
    print("*Login to Migration factory*")
    token = mfcommon.Factorylogin()

    print("*** Getting Server List ***")
    get_servers, _, _ = mfcommon.get_factory_servers(args.Waveid, token)
    linux_user_name = ''
    linux_pass_key = ''

    print("****************************")
    print("**** Installing Agents *****")
    print("****************************")
    print("")
    install_ads_agents(
        args.Force,
        get_servers,
        args.ADSHomeRegion,
        args.SecretADSAgents,
        "",
        "",
        linux_user_name,
        linux_pass_key,
        args.SecretLinux,
        args.SecretWindows,
        args.NoPrompts
    )

    print("")
    print("********************************")
    print("*Checking Agent install results*")
    print("********************************")
    print("")

    time.sleep(5)
    print("All servers have had ADS Agents installation run. Check logs for details.")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
