#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Version: 1SEP2023.00

from __future__ import print_function
import sys
import argparse
import json
import subprocess
import time
import boto3
import botocore.exceptions
import mfcommon
import os
import multiprocessing

POWERSHELL_EXE = "powershell.exe"

LOG_PADDING = 50
LOG_PADDING_CHAR = '*'

MSG_QUEUED_TASK = "Queued task for"
MSG_AGENT_INSTALL_FAILED = "Agent Install - Failed"

lock = multiprocessing.Lock()
queue = multiprocessing.Queue()

linuxpkg = __import__("1-Install-Linux")

cmf_api_access_token = None
user_api_url = None
servers = {}

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

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


def assume_role_mgn_install(account_id, region):
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
            ]
        )
        credentials = response['Credentials']
        return credentials
    except botocore.exceptions.ClientError as e:
        print(str(e))
        return None


# Pagination for describe MGN source servers
def get_unfiltered_mgn_source_servers(mgn_client_base):
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


def add_vpc_endpoints_to_command(parameters, command):
    if 's3_endpoint' in parameters and parameters['s3_endpoint'] is not None:
        command.append("-s3endpoint")
        command.append(parameters['s3_endpoint'])

    if 'mgn_endpoint' in parameters and parameters['mgn_endpoint'] is not None:
        command.append("-mgnendpoint")
        command.append(parameters['mgn_endpoint'])


def add_windows_credentials_to_command(parameters, command, final_output):
    # User credentials of user running the script added to the powershell command, without this the
    # powershell script will run under localsystem.
    if parameters["windows_user_name"] != "":
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
    else:
        final_output['messages'].append("INFO: Using current process credentials to connect to perform install.")


def run_task_windows(parameters):
    final_output = {'messages': []}
    pid = multiprocessing.current_process()
    final_output['pid'] = str(pid)
    final_output['host'] = parameters["server"]['server_fqdn']
    final_output['messages'].append("Installing MGN Agent on :  " + parameters["server"]['server_fqdn'])

    command = [POWERSHELL_EXE,
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
               "$" + str(parameters["windows_use_ssl"]).lower(),
               "-noreplication",
               "$" + str(parameters["mgn_no_replication"]).lower(),
               "-replicationdrives",
               f'"{parameters["mgn_replication_devices"]}"'
               ]

    if 'SessionToken' in parameters["agent_install_secrets"] and parameters["agent_install_secrets"][
        'SessionToken'] is not None:
        command.append("-sessiontoken")
        command.append(parameters["agent_install_secrets"]['SessionToken'])

    add_vpc_endpoints_to_command(parameters, command)

    try:
        add_windows_credentials_to_command(parameters, command, final_output)

        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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

    try:
        final_output = (
                linuxpkg.install_mgn(
                agent_linux_download_url=task_params["agent_linux_download_url"],
                region=task_params["region"],
                host= task_params["server"]['server_fqdn'],
                username=task_params["linux_user_name"],
                key_pwd=task_params['linux_pass_key'],
                using_key=task_params["linux_key_exist"],
                aws_agent_secret=task_params["agent_install_secrets"],
                s3_endpoint=task_params["s3_endpoint"],
                mgn_endpoint=task_params["mgn_endpoint"],
                no_replication=task_params["mgn_no_replication"],
                replication_devices=task_params["mgn_replication_devices"]
            )
        )

        # Add any output processing here on task completion.
        return final_output

    except Exception as error:
        final_output['messages'].append("ERROR (run_task_linux): %s" % error)
        final_output['return_code'] = 1
        return final_output


def add_linux_servers_to_install_queue(account, pool, linux_secret_name, s3_endpoint, base_parameters, no_user_prompts):
    if len(account['servers_linux']) == 0:
        return

    if s3_endpoint:
        agent_linux_download_url = f"https://{s3_endpoint}/aws-application-migration-service-{account['aws_region']}/" \
                                   f"latest/linux/aws-replication-installer-init.py"
    else:
        agent_linux_download_url = f"https://aws-application-migration-service-{account['aws_region']}." \
                                   f"s3.amazonaws.com/latest/linux/aws-replication-installer-init.py"
    for server in account['servers_linux']:
        linux_credentials = mfcommon.get_server_credentials('', '', server,
                                                            linux_secret_name, no_user_prompts)

        server_parameters = base_parameters.copy()
        server_parameters["server"] = server
        server_parameters["agent_linux_download_url"] = agent_linux_download_url
        server_parameters["server_fqdn"] = server['server_fqdn']
        server_parameters["linux_user_name"] = linux_credentials['username']
        server_parameters["linux_pass_key"] = linux_credentials['password']
        server_parameters["linux_key_exist"] = linux_credentials['private_key']
        server_parameters["region"] = account['aws_region']
        server_parameters["mgn_replication_devices"] = server.get('mgn_replication_devices', None)

        print(MSG_QUEUED_TASK, server['server_fqdn'], flush=True)

        pool.apply_async(run_task_linux,
                         args=(server_parameters,),
                         callback=log_result,
                         error_callback=error_result
                         )


def add_windows_server_to_install_queue(pool, server_parameters):
    # If server record has winrm_use_ssl key then override use ssl value with the server.
    if 'winrm_use_ssl' in server_parameters["server"]:
        if server_parameters["server"]['winrm_use_ssl'] is True:
            server_parameters["windows_use_ssl"] = True
        else:
            server_parameters["windows_use_ssl"] = False

    print(MSG_QUEUED_TASK, server_parameters["server"]['server_fqdn'], flush=True)

    pool.apply_async(run_task_windows,
                     args=(server_parameters,),
                     callback=log_result,
                     error_callback=error_result
                     )


def add_window_servers_to_install_queue(account, pool, windows_secret_name, s3_endpoint, base_parameters,
                                        no_user_prompts):
    if len(account['servers_windows']) == 0:
        return

    if s3_endpoint:
        agent_windows_download_url = f"https://{s3_endpoint}/aws-application-migration-service" \
                                     f"-{account['aws_region']}/latest/windows/AwsReplicationWindowsInstaller.exe"
    else:
        agent_windows_download_url = f"https://aws-application-migration-service" \
                                     f"-{account['aws_region']}.s3.amazonaws.com/latest/windows/" \
                                     f"AwsReplicationWindowsInstaller.exe"

    mfcommon.add_windows_servers_to_trusted_hosts(account['servers_windows'])

    for server in account['servers_windows']:
        windows_credentials = mfcommon.get_server_credentials('', '', server,
                                                              windows_secret_name, no_user_prompts)

        server_parameters = base_parameters.copy()
        server_parameters["server"] = server
        server_parameters["agent_windows_download_url"] = agent_windows_download_url
        server_parameters["server_fqdn"] = server['server_fqdn']
        server_parameters["windows_user_name"] = windows_credentials['username']
        server_parameters["windows_password"] = windows_credentials['password']
        server_parameters["region"] = account['aws_region']
        server_parameters["mgn_replication_devices"] = server.get('mgn_replication_devices', '')

        add_windows_server_to_install_queue(pool, server_parameters)


def get_agent_install_secrets(use_iam_user_aws_credentials, account, mgn_iam_user_secret_name=None):
    if use_iam_user_aws_credentials:
        if mgn_iam_user_secret_name is None:
            print("No MGN IAM user secret name provided, this is required when 'use IAM user' is selected.")
            return None
        # Get AWS credentials from secret provided in mgn_iam_user_secret_name parameter in target account.
        print(
            f"Using AWS IAM User credentials for MGN agent installation from secret ({mgn_iam_user_secret_name}).",
            flush=True)
        secret = mfcommon.get_credentials(mgn_iam_user_secret_name)
        if secret:
            return {"AccessKeyId": secret.get("secret_key"), "SecretAccessKey": secret.get("secret_value")}
        else:
            return secret
    else:
        # get temporary credentials from target account for agent installation.
        print("Using temporary AWS credentials for MGN agent installation.", flush=True)
        temporary_agent_install_credentials = assume_role_mgn_install(str(account['aws_accountid']),
                                                                      account['aws_region'])
        if temporary_agent_install_credentials is None:
            # Assume role failed continue to next account, as cannot access role for install.
            print("Unable to assume role CMF-AutomationServer in AWS account %s in region %s."
                  % (account['aws_accountid'], account['aws_region']))
            return None
        return temporary_agent_install_credentials


def install_mgn_agents(reinstall, get_servers, linux_secret_name=None, windows_secret_name=None, no_user_prompts=False,
                       concurrency=10, use_iam_user_aws_credentials=False, s3_endpoint=None, mgn_endpoint=None,
                       windows_use_ssl=False, mgn_iam_user_secret_name=None, mgn_no_replication=False):
    # Create worker pool
    pool = multiprocessing.Pool(concurrency)

    if reinstall:
        print("Forced reinstall selected if applicable.")

    if windows_use_ssl:
        print("Forced use SSL for WINRM (windows only).")

    # task parameters
    parameters = {
        "windows_user_name": '',
        "windows_password": '',
        "windows_secret_name": windows_secret_name,
        "linux_user_name": '',
        "linux_pass_key": '',
        "linux_key_exist": False,
        "linux_secret_name": linux_secret_name,
        "no_user_prompts": no_user_prompts,
        "reinstall": reinstall,
        "s3_endpoint": s3_endpoint,
        "mgn_endpoint": mgn_endpoint,
        "mgn_no_replication": mgn_no_replication,
        "windows_use_ssl": windows_use_ssl
    }

    for account in get_servers:
        print("######################################################")
        print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
        print("######################################################", flush=True)

        parameters["agent_install_secrets"] = get_agent_install_secrets(
            use_iam_user_aws_credentials,
            account,
            mgn_iam_user_secret_name
        )

        if parameters["agent_install_secrets"] is None:
            continue

        add_window_servers_to_install_queue(account, pool, windows_secret_name, s3_endpoint, parameters,
                                            no_user_prompts)

        add_linux_servers_to_install_queue(account, pool, linux_secret_name, s3_endpoint, parameters, no_user_prompts)

    # Close pool for new requests.
    pool.close()

    # Wait for all processes to complete.
    pool.join()


def is_server_registered_with_mgn(cmf_server, mgn_source_servers, update_status=False):
    is_registered = False
    try:
        sourceserver = mfcommon.get_mgn_source_server(
            cmf_server, mgn_source_servers)

        if sourceserver is not None:
            print("-- SUCCESS: MGN Agent verified in MGN console for server: " + cmf_server['server_fqdn'])
            migration_status = "Agent Install - Success"
            is_registered = True
        else:
            print("-- FAILED: MGN Agent not found in MGN console for server: " + cmf_server['server_fqdn'])
            migration_status = MSG_AGENT_INSTALL_FAILED

        if update_status:
            mfcommon.update_server_migration_status(cmf_api_access_token,
                                                    cmf_server['server_id'],
                                                    migration_status)
        print("", flush=True)
    except botocore.exceptions.ClientError as error:
        is_registered = False
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
        print("-- FAILED: %s, %s" % (cmf_server['server_id'], str(error)))

        if update_status:
            mfcommon.update_server_migration_status(cmf_api_access_token,
                                                    cmf_server['server_id'],
                                                    MSG_AGENT_INSTALL_FAILED)

    return is_registered


def get_mgn_source_servers(aws_target_account_id,
                           aws_target_account_region,
                           target_account_cmf_servers,
                           update_status=False):
    failures = 0
    mgn_source_servers = []
    try:
        target_account_session = assume_role(aws_target_account_id, aws_target_account_region)
        mgn_client = target_account_session.client("mgn", aws_target_account_region)
        mgn_source_servers = get_unfiltered_mgn_source_servers(mgn_client)
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

        for cmf_server in target_account_cmf_servers:
            print(
                "-- FAILED: AWS Account MGN Error (%s in %s): %s for server %s" % (aws_target_account_id,
                                                                                   aws_target_account_region,
                                                                                   msg,
                                                                                   cmf_server['server_fqdn'])
            )
            if update_status:
                mfcommon.update_server_migration_status(cmf_api_access_token,
                                                        cmf_server['server_id'],
                                                        f"Agent Install - Failed - {msg}")
        failures += len(target_account_cmf_servers)

    return mgn_source_servers, failures


def agent_check(get_servers):
    failures = 0
    for target_account in get_servers:
        target_account_cmf_servers = target_account['servers_windows'] + target_account['servers_linux']

        mgn_source_servers, target_account_failures = get_mgn_source_servers(str(target_account['aws_accountid']),
                                                                             target_account['aws_region'],
                                                                             target_account_cmf_servers,
                                                                             True)

        failures += target_account_failures
        for cmf_server in target_account_cmf_servers:
            if not is_server_registered_with_mgn(cmf_server, mgn_source_servers, True):
                failures += 1

    return failures


# Callback function for returning processes, this function will add the result to the print queue for processing.
def log_result(result):
    outcome = 'SUCCESSFUL'
    if 'return_code' in result:
        if result['return_code'] == 0:
            outcome = 'SUCCESSFUL'
        else:
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
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR))
    print("")
    print('          RESULTS START: ' + hostname)
    print("")
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR), flush=True)
    if 'messages' in process:
        for message in process['messages']:
            print(message)
    else:
        print(process)
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR))
    print("")
    print('          RESULTS END: ' + hostname)
    print("")
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR), flush=True)
    lock.release()
    process['printed'] = True


def is_successful_message(process):
    if 'return_code' in process:
        if process['return_code'] == 0:
            return True
        else:
            return False


def process_message(process):
    if 'printed' in process and not process['printed']:
        print_result(process)
        return is_successful_message(process)


# Main process queue handler responsible for processing output requests from completed jobs/processes.
# All output is held in this function from all processes until the TERMINATE message is received, then all results are
# printed to stdout. And the final message for the total job completion is also printed with summary data.
def process_msg_recv(output_message_queue, failure_count):
    messages = []
    while True:
        message = output_message_queue.get()
        if message == 'TERMINATE':
            break
        else:
            message['printed'] = False
            messages.append(message)

    successful = 0
    failures = 0
    for process in messages:
        if process_message(process):
            successful += 1
        else:
            failures += 1

    failure_count.value = failures
    print(
        "All servers task '%s' completed. %d failures, %d successful, total attempted %d. Check logs "
        "for details." % (
            task_name, failures, successful, len(messages)), flush=True)


def main(arguments):
    global cmf_api_access_token
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--AppIds', default=None)
    parser.add_argument('--ServerIds', default=None)
    parser.add_argument('--Force', default=False, type=mfcommon.parse_boolean)
    parser.add_argument('--NoPrompts', default=False, type=mfcommon.parse_boolean,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    parser.add_argument('--AWSUseIAMUserCredentials', default=False, type=mfcommon.parse_boolean)
    parser.add_argument('--Concurrency', default=10, type=int,
                        help='Specify if the task should be run in parallel. Default = 10')
    parser.add_argument('--S3Endpoint', default=None)
    parser.add_argument('--MGNEndpoint', default=None)
    parser.add_argument('--UseSSL', default=False, type=mfcommon.parse_boolean)
    parser.add_argument('--MGNIAMUser', default=None)
    parser.add_argument('--NoReplication', default=False, type=mfcommon.parse_boolean)
    args = parser.parse_args(arguments)

    # Get region value from FactoryEndpoint.json file if migration execution server is on prem

    if 'Region' in endpoints and endpoints['Region'].strip() != '':
        region = endpoints['Region']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update region")
        sys.exit()
    print("Factory region: " + region)

    print("")
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR))
    print("Login to Migration factory".center(LOG_PADDING, LOG_PADDING_CHAR))
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR), flush=True)
    cmf_api_access_token = mfcommon.factory_login()

    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR))
    print("Getting Server List".center(LOG_PADDING, LOG_PADDING_CHAR))
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR), flush=True)
    get_servers, _, _ = mfcommon.get_factory_servers(
        waveid=args.Waveid,
        app_ids=mfcommon.parse_list(args.AppIds),
        server_ids=mfcommon.parse_list(args.ServerIds),
        token=cmf_api_access_token,
        os_split=True,
        rtype='Rehost'
    )

    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR))
    print(task_name.center(LOG_PADDING, LOG_PADDING_CHAR))
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR), flush=True)
    print("")

    # Start print message queue thread.
    failure_count = multiprocessing.Value("i", 0, lock=False)
    process_print_queue = multiprocessing.Process(target=process_msg_recv, args=(queue, failure_count,))
    process_print_queue.start()

    try:
        install_mgn_agents(args.Force, get_servers,
                           args.SecretLinux, args.SecretWindows, args.NoPrompts, args.Concurrency,
                           args.AWSUseIAMUserCredentials, args.S3Endpoint, args.MGNEndpoint, args.UseSSL,
                           args.MGNIAMUser, args.NoReplication)
    except Exception as e:
        print(e, flush=True)

    # Close message queue thread.
    queue.put('TERMINATE')

    # Wait for all print processing to complete.
    process_print_queue.join()

    print("")
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR))
    print("Checking Agent install results within MGN Console".center(LOG_PADDING, LOG_PADDING_CHAR))
    print("".rjust(LOG_PADDING, LOG_PADDING_CHAR))
    print("", flush=True)

    time.sleep(5)
    mgn_failure_count = agent_check(get_servers)

    if mgn_failure_count > 0 and failure_count.value > 0:
        print(f"{str(failure_count.value)} agents reported issues during installation, and {str(mgn_failure_count)} "
              f"server agents could not be validated with the MGN console. Check log for details.")
        return 1
    elif mgn_failure_count == 0 and failure_count.value > 0:
        print(f"{str(failure_count.value)} server agents reported issues during installation. Check log for details.")
        return 1
    elif mgn_failure_count > 0 and failure_count.value == 0:
        print(f"{str(mgn_failure_count)} "
              f"server agents could not be validated with the MGN console. Check log for details.")
        return 1
    else:
        print("All servers have had MGN Agents installed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
