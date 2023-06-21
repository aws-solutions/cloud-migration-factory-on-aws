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

# Version: 1SEP2022.00

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
import os
import multiprocessing

lock = multiprocessing.Lock()
queue = multiprocessing.Queue()

linuxpkg = __import__("1-Install-Linux")

token = None
user_api_url = None
servers = {}

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

if "CMF_SCRIPTS_BUCKET" in os.environ:
    scripts_bucket = os.environ["CMF_SCRIPTS_BUCKET"]
    output_bucket_name = scripts_bucket.replace('-ssm-scripts', '-ssm-outputs')
else:
    output_bucket_name = None

task_name = "AWS MGN install agents"


def assume_role(account_id, region):
    sts_client = boto3.client('sts', region_name=region)
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


def assume_role_mgn_install(account_id, region, cmf_user_name):
    sts_client = boto3.client('sts', region_name=region)
    role_arn = 'arn:aws:iam::' + account_id + ':role/CMF-AutomationServer'
    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.
    try:
        user = sts_client.get_caller_identity()['Arn']
        sessionname = user.split('/')[1]
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=sessionname,
            PolicyArns=[
                {
                    'arn': 'arn:aws:iam::aws:policy/AWSApplicationMigrationAgentInstallationPolicy'
                },
            ],
            #             Tags=[
            #                 {
            #                     'Key': 'CMFTask',
            #                     'Value': 'InstallMGNAgents'
            #                 },
            #                 {
            #                     'Key': 'CMFInitiatingUser',
            #                     'Value': cmf_user_name
            #                 },
            #             ]
        )
        credentials = response['Credentials']
        return credentials
    except botocore.exceptions.ClientError as e:
        print(str(e))
        return None


# Pagination for describe MGN source servers
def get_mgn_source_servers(mgn_client_base):
    token = None
    source_server_data = []
    paginator = mgn_client_base.get_paginator('describe_source_servers')
    while True:
        response = paginator.paginate(filters={},
                                      PaginationConfig={
                                          'StartingToken': token})
        for page in response:
            source_server_data.extend(page['items'])
        try:
            token = page['NextToken']
            print(token)
        except KeyError:
            return source_server_data


def run_task_windows(parameters):
    final_output = {'messages': []}
    pid = multiprocessing.current_process()
    final_output['pid'] = str(pid)
    final_output['host'] = parameters["server"]['server_fqdn']
    final_output['messages'].append("Installing MGN Agent on :  " + parameters["server"]['server_fqdn'])

    command = ["powershell.exe",
               ".\\1-Install-Windows.ps1",
               "-reinstall",
               "$" + str(parameters["reinstall"]).lower(),
               "-agent_download_url",
               parameters["agent_windows_download_url"],
               "-region",
               parameters["region"],
               "-accesskeyid",
               parameters["agent_install_secrets"]['AccessKeyId'],
               "-secretaccesskey",
               parameters["agent_install_secrets"]['SecretAccessKey'],
               "-Servername",
               parameters["server"]['server_fqdn'],
               "-usessl",
               "$" + str(parameters["windows_use_ssl"]).lower()
               ]

    if 'SessionToken' in parameters["agent_install_secrets"] and parameters["agent_install_secrets"][
        'SessionToken'] is not None:
        command.append("-sessiontoken")
        command.append(parameters["agent_install_secrets"]['SessionToken'])

    if 's3_endpoint' in parameters and parameters['s3_endpoint'] is not None:
        command.append("-s3endpoint")
        command.append(parameters['s3_endpoint'])

    if 'mgn_endpoint' in parameters and parameters['mgn_endpoint'] is not None:
        command.append("-mgnendpoint")
        command.append(parameters['mgn_endpoint'])

    try:
        if parameters["windows_user_name"] != "":
            # User credentials of user executing the script added to the powershell command, without this the powershell script will run under localsystem.
            if "\\" not in parameters["windows_user_name"] and "@" not in parameters["windows_user_name"]:
                # Assume local account provided, prepend server name to user ID.
                server_name_only = parameters["server"]["server_fqdn"].split(".")[0]
                parameters["windows_user_name"] = server_name_only + "\\" + parameters["windows_user_name"]
                final_output['messages'].append("INFO: Using local account to connect: "
                                                + parameters["windows_user_name"])
            else:
                final_output['messages'].append("INFO: Using domain account to connect: "
                                                + parameters["windows_user_name"])
            command.append("-windowsuser")
            command.append("'" + parameters["windows_user_name"] + "'")
            command.append("-windowspwd")
            command.append("'" + parameters["windows_password"] + "'")

        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        for line in p.stdout.readlines():
            final_output['messages'].append(line)

        for line in p.stderr.readlines():
            final_output['messages'].append(line)
        retval = p.wait()

        p.communicate()

        # Add any output processing here on task completion.
        for message in final_output['messages']:
            # Check logs for errors.
            if 'Installation failed' in message or 'Error details:' in message or 'error message' in message:
                # error found change return code to a failure.
                retval = 1

        final_output['return_code'] = retval

        return final_output
    except Exception as error:
        final_output['messages'].append("ERROR (run_task_linux): " % error)
        final_output['return_code'] = 1
        return final_output


def run_task_linux(task_params):
    final_output = {'messages': []}
    pid = multiprocessing.current_process()
    final_output['pid'] = str(pid)
    final_output['host'] = task_params["server"]['server_fqdn']
    final_output['messages'].append("Installing MGN Agent on :  " + task_params["server"]['server_fqdn'])

    if 'SessionToken' in task_params["agent_install_secrets"]:
        sesssion_token = task_params["agent_install_secrets"]['SessionToken']
    else:
        sesssion_token = ""

    try:
        final_output = install_linux_output_queue = linuxpkg.install_mgn(task_params["agent_linux_download_url"],
                                                                         task_params["region"],
                                                                         task_params["server"]['server_fqdn'],
                                                                         task_params["linux_user_name"],
                                                                         task_params['linux_pass_key'],
                                                                         task_params["linux_key_exist"],
                                                                         task_params["agent_install_secrets"]
                                                                         ['AccessKeyId'],
                                                                         task_params["agent_install_secrets"]
                                                                         ['SecretAccessKey'],
                                                                         sesssion_token,
                                                                         task_params["s3_endpoint"],
                                                                         task_params["mgn_endpoint"])
        # Add any output processing here on task completion.

        return final_output
    except Exception as error:
        final_output['messages'].append("ERROR (run_task_linux): %s" % error)
        final_output['return_code'] = 1
        return final_output


def install_mgn_agents(reinstall, get_servers, region, windows_user_name, windows_password, linux_user_name, linux_pass_key,
                       linux_key_exist, linux_secret_name=None, windows_secret_name=None, no_user_prompts=False,
                       concurrency=10, use_iam_user_aws_credentials=False, s3_endpoint=None, mgn_endpoint=None,
                       windows_use_ssl=False):
    # Create worker pool
    pool = multiprocessing.Pool(concurrency)

    if reinstall:
        print("Forced reinstall selected if applicable.")

    if windows_use_ssl:
        print("Forced use SSL for WINRM (windows only).")

    # task parameters
    parameters = {
        "windows_user_name": windows_user_name,
        "windows_password": windows_password,
        "windows_secret_name": windows_secret_name,
        "linux_user_name": linux_user_name,
        "linux_pass_key": linux_pass_key,
        "linux_key_exist": linux_key_exist,
        "linux_secret_name": linux_secret_name,
        "no_user_prompts": no_user_prompts,
        "reinstall": reinstall,
        "s3_endpoint": s3_endpoint,
        "mgn_endpoint": mgn_endpoint,
        "windows_use_ssl": windows_use_ssl
    }

    for account in get_servers:
        print("######################################################")
        print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
        print("######################################################", flush=True)
        if use_iam_user_aws_credentials:
            # Get AWS credentials from secret called MGNAgentInstallUser in target account.
            print("Using AWS credentials for MGN agent installation from target account secret (MGNAgentInstallUser).",
                  flush=True)
            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            if target_account_session is None:
                # Assume role failed continue to next account, as cannot access IAM user for install.
                print("Unable to assume role CMF-AutomationServer in AWS account %s in region %s."
                      % (account['aws_accountid'], account['aws_region']))
                continue
            secretsmanager_client = target_account_session.client('secretsmanager', region)
            parameters["agent_install_secrets"] = json.loads(secretsmanager_client.get_secret_value
                                                             (SecretId='MGNAgentInstallUser')['SecretString'])
        else:
            # get temporary credentials from target account for agent installation.
            print("Using temporary AWS credentials for MGN agent installation.", flush=True)
            temporary_agent_install_credentials = assume_role_mgn_install(str(account['aws_accountid']), region, "")
            if temporary_agent_install_credentials is None:
                # Assume role failed continue to next account, as cannot access role for install.
                print("Unable to assume role CMF-AutomationServer in AWS account %s in region %s."
                      % (account['aws_accountid'], account['aws_region']))
                continue
            parameters["agent_install_secrets"] = temporary_agent_install_credentials

        # Installing agent on Windows servers
        server_string = ""
        if len(account['servers_windows']) > 0:

            if s3_endpoint:
                agent_windows_download_url = "https://%s/aws-application-migration-service-%s/latest/windows/" \
                                             "AwsReplicationWindowsInstaller.exe" % (s3_endpoint, account['aws_region'])
            else:
                agent_windows_download_url = "https://aws-application-migration-service-{}.s3.amazonaws.com/latest/" \
                                             "windows/AwsReplicationWindowsInstaller.exe".format(account['aws_region'])

            # Get all servers FQDNs into csv for trusted hosts update.
            for server in account['servers_windows']:
                server_string = server_string + server['server_fqdn'] + ','
            server_string = server_string[:-1]
            # Add servers to local trusted hosts to allow authentication if different domain.
            p_trustedhosts = subprocess.Popen(["powershell.exe",
                                               "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '"
                                               + server_string + "' -Concatenate -Force"],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            for server in account['servers_windows']:
                windows_credentials = mfcommon.getServerCredentials(windows_user_name, windows_password, server,
                                                                    windows_secret_name, no_user_prompts)

                server_parameters = parameters.copy()
                server_parameters["server"] = server
                server_parameters["agent_windows_download_url"] = agent_windows_download_url
                server_parameters["server_fqdn"] = server['server_fqdn']
                server_parameters["windows_user_name"] = windows_credentials['username']
                server_parameters["windows_password"] = windows_credentials['password']
                server_parameters["region"] = account['aws_region']

                # If server record has winrm_use_ssl key then override use ssl value with the server.
                if 'winrm_use_ssl' in server:
                    if server['winrm_use_ssl'] is True:
                        server_parameters["windows_use_ssl"] = True
                    else:
                        server_parameters["windows_use_ssl"] = False

                print("Queued task for", server['server_fqdn'], flush=True)

                pool.apply_async(run_task_windows,
                                 args=(server_parameters,),
                                 callback=log_result,
                                 error_callback=error_result
                                 )

        # Creating task for all Linux servers.
        if len(account['servers_linux']) > 0:

            if s3_endpoint:
                agent_linux_download_url = "https://%s/aws-application-migration-service-%s/latest/linux/" \
                                           "aws-replication-installer-init.py" % (s3_endpoint, account['aws_region'])
            else:
                agent_linux_download_url = "https://aws-application-migration-service-{" \
                                           "}.s3.amazonaws.com/latest/linux/aws-replication-installer-init.py".format(
                    account['aws_region'])
            for server in account['servers_linux']:
                linux_credentials = mfcommon.getServerCredentials(linux_user_name, linux_pass_key, server,
                                                                  linux_secret_name, no_user_prompts)

                server_parameters = parameters.copy()
                server_parameters["server"] = server
                server_parameters["agent_linux_download_url"] = agent_linux_download_url
                server_parameters["server_fqdn"] = server['server_fqdn']
                server_parameters["linux_user_name"] = linux_credentials['username']
                server_parameters["linux_pass_key"] = linux_credentials['password']
                server_parameters["linux_key_exist"] = linux_credentials['private_key']
                server_parameters["region"] = account['aws_region']

                print("Queued task for", server['server_fqdn'], flush=True)

                pool.apply_async(run_task_linux,
                                 args=(server_parameters,),
                                 callback=log_result,
                                 error_callback=error_result
                                 )

    # Close pool for new requests.
    pool.close()

    # Wait for all processes to complete.
    pool.join()


def AgentCheck(get_servers, UserHOST, token):
    failures = 0
    auth = {"Authorization": token}
    for account in get_servers:
        all_servers = account['servers_windows'] + account['servers_linux']
        try:
            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            mgn_client = target_account_session.client("mgn", account['aws_region'])
            mgn_sourceservers = get_mgn_source_servers(mgn_client)
        except botocore.exceptions.ClientError as error:
            # Error getting account MGN
            if ":" in str(error):
                err = ''
                msgs = str(error).split(":")[1:]
                for msg in msgs:
                    err = err + msg
                msg = str(err)
            else:
                msg = str(error)

            for factoryserver in all_servers:
                print("-- FAILED: AWS Account MGN Error (%s in %s): %s for server %s" % (str(account['aws_accountid']),
                                                                                         account['aws_region'],
                                                                                         msg,
                                                                                         factoryserver['server_fqdn'])
                      )
                serverattr = {"migration_status": "Agent Install - Failed - %s" % msg}
                update_server_status = requests.put(UserHOST + serverendpoint + '/' + factoryserver['server_id'],
                                                    headers=auth,
                                                    data=json.dumps(serverattr),
                                                    timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
            failures += len(all_servers)
            continue

        for factoryserver in all_servers:
            serverattr = {}
            isServerExist = False
            try:
                sourceserver = mfcommon.get_MGN_Source_Server(factoryserver, mgn_sourceservers)

                if sourceserver is not None:
                    print("-- SUCCESS: MGN Agent verified in MGN console for server: " + factoryserver['server_fqdn'])
                    serverattr = {"migration_status": "Agent Install - Success"}
                else:
                    print("-- FAILED: MGN Agent not found in MGN console for server: " + factoryserver['server_fqdn'])
                    serverattr = {"migration_status": "Agent Install - Failed"}
                    failures += 1

                update_server_status = requests.put(UserHOST + serverendpoint + '/' + factoryserver['server_id'],
                                                    headers=auth,
                                                    data=json.dumps(serverattr),
                                                    timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
                print("", flush=True)
            except botocore.exceptions.ClientError as error:
                if ":" in str(error):
                    err = ''
                    msgs = str(error).split(":")[1:]
                    for msg in msgs:
                        err = err + msg
                    msg = "ERROR: " + err
                    print(msg)
                else:
                    msg = "ERROR: " + str(error)
                    print(msg)
                print("-- FAILED: %s, %s" % (factoryserver['server_id'], str(error)))
                failures += 1

    return failures


# Callback function for returning processes, this function will add the result to the print queue for processing.
def log_result(result):
    outcome = 'SUCCESSFUL'
    if 'return_code' in result:
        if result['return_code'] == 0:
            successful = + 1
            outcome = 'SUCCESSFUL'
        else:
            failures = + 1
            outcome = 'FAILED'

    print('Task result returned for %s as %s, detailed logs to follow.' % (result['host'], outcome), flush=True)
    queue.put(result)


def error_result(error):
    result = {'return_code': 1, 'messages': [str(error)], 'host': 'unknown'}
    queue.put(result)


# prints result of process completion to the stdout/print, used my print queue once TERMINATE messages is queued.
def print_result(process):
    lock.acquire()
    if 'host' in process:
        hostname = process['host']
    else:
        hostname = 'unknown'
    print("--------------------------------------------------------------")
    print("")
    print('          RESULTS START: ' + hostname)
    print("")
    print("--------------------------------------------------------------", flush=True)
    if 'messages' in process:
        for message in process['messages']:
            print(message)
    else:
        print(process)
    print("--------------------------------------------------------------")
    print("")
    print('          RESULTS END: ' + hostname)
    print("")
    print("--------------------------------------------------------------", flush=True)
    lock.release()
    process['printed'] = True


# Main process queue handler responsible for processing output requests from completed jobs/processes.
# All output is held in this function from all processes until the TERMINATE message is received, then all results are
# printed to stdout. And the final message for the total job completion is also printed with summary data.
def process_msg_recv(queue, failure_count):
    messages = []
    while True:
        message = queue.get()
        if message == 'TERMINATE':
            break
        else:
            message['printed'] = False
            messages.append(message)

    successful = 0
    failures = 0
    for process in messages:
        if 'printed' in process and not process['printed']:
            print_result(process)
            if 'return_code' in process:
                if process['return_code'] == 0:
                    successful += 1
                else:
                    failures += 1

    failure_count.value = failures
    print(
        "All servers task '%s' completed. %d failures, %d successful, total attempted %d. Check logs "
        "for details." % (
            task_name, failures, successful, len(messages)), flush=True)


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
    parser.add_argument('--Force', default=False, type=parse_boolean)
    parser.add_argument('--NoPrompts', default=False, type=parse_boolean,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    parser.add_argument('--AWSUseIAMUserCredentials', default=False, type=parse_boolean)
    parser.add_argument('--Concurrency', default=10, type=int,
                        help='Specify if the task should be run in parallel. Default = 10')
    parser.add_argument('--S3Endpoint', default=None)
    parser.add_argument('--MGNEndpoint', default=None)
    parser.add_argument('--UseSSL', default=False, type=parse_boolean)
    args = parser.parse_args(arguments)

    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit()

    # Get region value from FactoryEndpoint.json file if migration execution server is on prem

    if 'Region' in endpoints and endpoints['Region'].strip() != '':
        region = endpoints['Region']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update region")
        sys.exit()
    print("Factory region: " + region)

    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************", flush=True)
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ***")
    print("****************************", flush=True)
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST, True, 'Rehost')
    linux_user_name = ''
    linux_pass_key = ''
    linux_key_exist = False

    print("****************************")
    print("*****  %s  *****" % task_name)
    print("****************************", flush=True)
    print("")

    # Start print message queue thread.
    failure_count = multiprocessing.Value("i", 0, lock=False)
    process_print_queue = multiprocessing.Process(target=process_msg_recv, args=(queue, failure_count,))
    process_print_queue.start()

    try:
        install_mgn_agents(args.Force, get_servers, region, "", "", linux_user_name, linux_pass_key, linux_key_exist,
                           args.SecretLinux, args.SecretWindows, args.NoPrompts, args.Concurrency,
                           args.AWSUseIAMUserCredentials, args.S3Endpoint, args.MGNEndpoint, args.UseSSL)
    except Exception as e:
        print(e, flush=True)

    # Close message queue thread.
    queue.put('TERMINATE')

    # Wait for all print processing to complete.
    process_print_queue.join()
    # if failure_count.value > 0:
    #     return 1
    # else:
    #     return 0

    print("")
    print("*************************************************")
    print("*Checking Agent install results with MGN Console*")
    print("*************************************************")
    print("", flush=True)

    time.sleep(5)
    mgn_failure_count = AgentCheck(get_servers, UserHOST, token)

    if mgn_failure_count > 0 or failure_count.value > 0:
        print(str(mgn_failure_count) + " server agents could not be validated with the MGN console. "
                                       "Check log for details.")
        return 1
    else:
        print("All servers have had MGN Agents installed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
