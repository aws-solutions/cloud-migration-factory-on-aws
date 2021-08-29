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

# Version: 17MAY2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import subprocess
import time
import boto3
import botocore.exceptions
import mfcommon

linuxpkg = __import__("1-Install-Linux")

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

def assume_role(account_id, region):

    sts_client = boto3.client('sts')
    role_arn = 'arn:aws:iam::' + account_id + ':role/Factory-ExeServer'
    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.
    try:
        user = sts_client.get_caller_identity()['Arn']
        sessionname = user.split('/')[1]
        response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=sessionname)
        credentials = response['Credentials']
        session = boto3.Session(
            region_name = region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        return session
    except botocore.exceptions.ClientError as e:
        print(str(e))

def install_mgn_agents(force, get_servers, region, windows_user_name, windows_password, linux_user_name, linux_pass_key, linux_key_exist):
    try:
        if region != '':
            reinstall = 'No'
            if force == True:
                reinstall = 'Yes'
            for account in get_servers:
                print("######################################################")
                print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
                print("######################################################")
                target_account_session = assume_role(str(account['aws_accountid']), region)
                secretsmanager_client = target_account_session.client('secretsmanager', region)
                agent_install_secrets = json.loads(secretsmanager_client.get_secret_value(SecretId='MGNAgentInstallUser')['SecretString'])
                # Installing agent on Windows servers
                server_string = ""
                if len(account['servers_windows']) > 0:
                    agent_windows_download_url = "https://aws-application-migration-service-{}.s3.amazonaws.com/latest/windows/AwsReplicationWindowsInstaller.exe".format(account['aws_region'])
                    for server in account['servers_windows']:
                        server_string = server_string + server['server_fqdn'] + ','
                    server_string = server_string[:-1]
                    if windows_user_name != "":
                        #Add server to Exec Server to trustedhosts.
                        p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server['server_fqdn'] + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        p = subprocess.Popen(["powershell.exe",
                                ".\\1-Install-Windows.ps1", reinstall, agent_windows_download_url, account['aws_region'], agent_install_secrets['AccessKeyId'], agent_install_secrets['SecretAccessKey'], server_string, windows_user_name, windows_password],
                                stdout=sys.stdout)
                    else:
                        p = subprocess.Popen(["powershell.exe",
                                ".\\1-Install-Windows.ps1", reinstall, agent_windows_download_url, account['aws_region'], agent_install_secrets['AccessKeyId'], agent_install_secrets['SecretAccessKey'], server_string],
                                stdout=sys.stdout)
                    p.communicate()
                # Installing agent on Linux servers
                if len(account['servers_linux']) > 0:
                    agent_linux_download_url = "https://aws-application-migration-service-{}.s3.amazonaws.com/latest/linux/aws-replication-installer-init.py".format(account['aws_region'])
                    for server in account['servers_linux']:
                        install_linux = linuxpkg.install_mgn(agent_linux_download_url, account['aws_region'], server['server_fqdn'], linux_user_name, linux_pass_key, linux_key_exist, agent_install_secrets['AccessKeyId'], agent_install_secrets['SecretAccessKey'])
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

def AgentCheck(get_servers, UserHOST, token):
    try:
        auth = {"Authorization": token}
        for account in get_servers:
            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            mgn_client = target_account_session.client("mgn", account['aws_region'])
            mgn_sourceservers = mgn_client.describe_source_servers(filters={})
            all_servers = account['servers_windows'] + account['servers_linux']
            for factoryserver in all_servers:
                serverattr = {}
                isServerExist = False

                sourceserver = mfcommon.get_MGN_Source_Server(factoryserver, mgn_sourceservers['items'])

                if sourceserver is not None:
                   print("-- SUCCESS: Agent installed on server: " + factoryserver['server_fqdn'])
                   serverattr = {"migration_status": "Agent Install - Success"}
                else:
                   print("-- FAILED: Agent install failed on server: " + factoryserver['server_fqdn'])
                   serverattr = {"migration_status": "Agent Install - Failed"}

                update_server_status = requests.put(UserHOST + serverendpoint + '/' + factoryserver['server_id'], headers=auth, data=json.dumps(serverattr))

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
    parser.add_argument('--Force', action='store_true')
    parser.add_argument('--WindowsUser', default="")
    args = parser.parse_args(arguments)

    UserHOST = ""
    region = ""
    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit()

    # Get region value from FactoryEndpoint.json file if migration execution server is on prem

    if 'Region' in endpoints:
        region = endpoints['Region']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update region")
        sys.exit()
    print("Factory region: " + region)

    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ***")
    print("****************************")
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST)
    linux_user_name = ''
    linux_pass_key = ''
    linux_key_exist = False
    if linux_exist == True:
        linux_user_name, linux_pass_key, linux_key_exist = mfcommon.get_linux_password()

    windows_password = ''
    if windows_exist == True and args.WindowsUser != "":
        windows_password = mfcommon.GetWindowsPassword()

    print("****************************")
    print("**** Installing Agents *****")
    print("****************************")
    print("")
    install_agents = install_mgn_agents(args.Force, get_servers, region, args.WindowsUser, windows_password, linux_user_name, linux_pass_key, linux_key_exist)

    print("")
    print("********************************")
    print("*Checking Agent install results*")
    print("********************************")
    print("")

    time.sleep(5)
    AgentCheck(get_servers, UserHOST, token)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
