#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from __future__ import print_function
import requests
import datetime
import json
import os
import boto3
import logging
import multiprocessing
import lambda_mgn_utils

log = logging.getLogger()
log.setLevel(logging.INFO)

application = os.environ['application']
environment = os.environ['environment']
AnonymousUsageData = os.environ['AnonymousUsageData']
servers_table_name = '{}-{}-servers'.format(application, environment)
servers_table = boto3.resource('dynamodb').Table(servers_table_name)
s_uuid = os.environ['solutionUUID']
region = os.environ['region']
url = 'https://metrics.awssolutionsbuilder.com/generic'

REQUESTS_DEFAULT_TIMEOUT = 60

ACCOUNT_MESSAGE_PREFIX = " - in account: "

# Launch test servers in application migration service
def launch_test_servers(account, mgn_client):
    try:
        # Enable multithreading
        processes = []
        multiprocessing.Manager()

        message_suffix = lambda_mgn_utils.build_logging_message(
            "", account['aws_accountid'], account['aws_region'], "")

        log.info(f"*** Launching Test Servers in account: {message_suffix} ***")
        action_result = mgn_client.start_test(sourceServerIDs=account['source_server_ids'])
        log.info(action_result)
        if action_result['ResponseMetadata']['HTTPStatusCode'] != 202:
            msg = f"ERROR: Launch test servers failed for account: {message_suffix}"
            log.error(msg)
            return msg
        else:
            message_suffix = lambda_mgn_utils.build_logging_message(
                "", account['aws_accountid'], account['aws_region'],
                action_result['job']['jobID'])
            msg = f"SUCCESS: created test launch job for account: {message_suffix}"
            log.info(msg)
            for server in account['servers']:
                launch_type = "Test"
                p = multiprocessing.Process(target=multiprocessing_usage, args=(server, launch_type))
                processes.append(p)
                p.start()
            # Waiting for all processes to finish
            for process in processes:
                process.join()
            return action_result['job']['jobID']
    except Exception as error:
        message_suffix = lambda_mgn_utils.build_logging_message(
            ACCOUNT_MESSAGE_PREFIX, account['aws_accountid'],
            account['aws_region'], "")
        error_message = lambda_mgn_utils.handle_error(
            error, "ERROR: ", message_suffix, False)
        return error_message


# Launch cutover servers in application migration service
def launch_cutover_servers(account, mgn_client):
    try:
        # Enable multithreading
        processes = []
        multiprocessing.Manager()

        message_suffix = lambda_mgn_utils.build_logging_message(
            "", account['aws_accountid'], account['aws_region'], "")
        
        log.info(f"*** Launching Cutover Servers in account: {message_suffix} ***")
        action_result = mgn_client.start_cutover(sourceServerIDs=account['source_server_ids'])
        log.info(action_result)
        if action_result['ResponseMetadata']['HTTPStatusCode'] != 202:
            msg = f"ERROR: Launch cutover servers failed for account: {message_suffix}"
            log.error(msg)
            return msg
        else:
            message_suffix = lambda_mgn_utils.build_logging_message(
                "", account['aws_accountid'], account['aws_region'],
                action_result['job']['jobID'])
            msg = f"SUCCESS: created cutover launch job for account: {message_suffix}"
            log.info(msg)
            for server in account['servers']:
                launch_type = "Cutover"
                p = multiprocessing.Process(target=multiprocessing_usage, args=(server, launch_type))
                processes.append(p)
                p.start()
            # Waiting for all processes to finish
            for process in processes:
                process.join()
            return action_result['job']['jobID']
    except Exception as error:
        message_suffix = lambda_mgn_utils.build_logging_message(
            ACCOUNT_MESSAGE_PREFIX, account['aws_accountid'],
            account['aws_region'], "")
        error_message = lambda_mgn_utils.handle_error(
            error, "ERROR: ", message_suffix, False)
        return error_message


def multiprocessing_usage(server, launch_type):
    existing_attr = servers_table.get_item(Key={'server_id': server['server_id']})
    existing_attr['Item']['migration_status'] = launch_type + " instance launched"
    servers_table.put_item(Item=existing_attr['Item'])
    log.info("Pid: " + str(os.getpid()) + " - This is " + launch_type + " Launch, migration_status updated")
    if AnonymousUsageData == "Yes":
        usage_data = {"Solution": "SO0097",
                      "UUID": s_uuid,
                      "Status": "Migrated",
                      "TimeStamp": str(datetime.datetime.now()),
                      "Region": region
                      }
        requests.post(url,
                      data=json.dumps(usage_data),
                      headers={'content-type': 'application/json'},
                      timeout=REQUESTS_DEFAULT_TIMEOUT)
        url_ce = "https://s20a21yvzd.execute-api.us-east-1.amazonaws.com/prod/launch"
        mgn_data = {"UUID": s_uuid,
                    "version": "MGN-v3"
                    }
        requests.post(url_ce,
                      data=json.dumps(mgn_data),
                      timeout=REQUESTS_DEFAULT_TIMEOUT)


# This function will terminate all launched instances
def terminate_launched_instances(account, mgn_client):
    try:
        message_suffix = lambda_mgn_utils.build_logging_message(
            "", account['aws_accountid'], account['aws_region'], "")

        log.info(f"*** Terminating Test Servers in account: {message_suffix} ***")
        action_result = mgn_client.terminate_target_instances(
            sourceServerIDs=account['source_server_ids'])
        log.info(action_result)
        if action_result['ResponseMetadata']['HTTPStatusCode'] != 202:
            msg = f"ERROR: Terminate test servers failed for account: {message_suffix}"
            log.error(msg)
            return msg
        else:
            message_suffix = lambda_mgn_utils.build_logging_message(
                "", account['aws_accountid'], account['aws_region'],
                action_result['job']['jobID'])
            msg = f"SUCCESS: Successfully created terminate server job for account: {message_suffix}"
            log.info(msg)
            return msg
    except Exception as error:
        message_suffix = lambda_mgn_utils.build_logging_message(
            ACCOUNT_MESSAGE_PREFIX, account['aws_accountid'],
            account['aws_region'], "")
        error_message = lambda_mgn_utils.handle_error(
            error, "ERROR: ", message_suffix, False)
        return error_message


def multiprocessing_action(
        serverlist, creds, region, action, return_dict,
        status_list, aws_accountid, aws_region):
    try:
        session = lambda_mgn_utils.get_session(creds, region)
        mgn_client = session.client("mgn", region)
        validated_count = 0

        message_suffix = lambda_mgn_utils.build_logging_message(
            "", aws_accountid, aws_region, "")

        for factoryserver in serverlist:
            if action.strip() == 'Mark as Ready for Cutover':
                log.info(
                    f"*** Mark as Ready for Cutover in account: {message_suffix} ***")
                state = {'state': 'READY_FOR_CUTOVER'}
                action_result = mgn_client.change_server_life_cycle_state(
                    lifeCycle=state, sourceServerID=factoryserver[
                    'source_server_id'])
            elif action.strip() == 'Finalize Cutover':
                log.info(f"*** Finalize Cutover in account: {message_suffix} ***")
                action_result = mgn_client.disconnect_from_service(
                    sourceServerID=factoryserver['source_server_id'])
                state = {'state': 'CUTOVER'}
                action_result = mgn_client.change_server_life_cycle_state(
                    lifeCycle=state, sourceServerID=factoryserver[
                    'source_server_id'])
            elif action.strip() == '- Revert to ready for testing':
                log.info(
                    f"*** Revert to ready for testing in account: {message_suffix} ***")
                state = {'state': 'READY_FOR_TEST'}
                action_result = mgn_client.change_server_life_cycle_state(
                    lifeCycle=state, sourceServerID=factoryserver[
                    'source_server_id'])
            elif action.strip() == '- Revert to ready for cutover':
                log.info(
                    f"*** Revert to ready for cutover in account: {message_suffix} ***")
                state = {'state': 'READY_FOR_CUTOVER'}
                action_result = mgn_client.change_server_life_cycle_state(
                    lifeCycle=state, sourceServerID=factoryserver[
                    'source_server_id'])
            elif action.strip() == '- Disconnect from AWS':
                log.info(f"*** Disconnect from AWS in account: {message_suffix} ***")
                action_result = mgn_client.disconnect_from_service(
                    sourceServerID=factoryserver['source_server_id'])
            elif action.strip() == '- Mark as archived':
                log.info(f"*** Mark as archived in account: {message_suffix} ***")
                action_result = mgn_client.mark_as_archived(
                    sourceServerID=factoryserver['source_server_id'])

            message_suffix = lambda_mgn_utils.build_logging_message(
                ACCOUNT_MESSAGE_PREFIX, aws_accountid, aws_region, "")
            message_suffix = f"{factoryserver['server_name']}{message_suffix}"

            if action_result['ResponseMetadata']['HTTPStatusCode'] != 200:
                msg = f"Pid: {str(os.getpid())} - ERROR: {action.strip()} failed for server: \
                      {message_suffix}"
                log.error(msg)
                return_dict[factoryserver['server_name']] = msg
            else:
                msg = f"Pid: {str(os.getpid())} - SUCCESS: {action.strip()} for server: \
                      {message_suffix}"
                log.info(msg)
                validated_count = validated_count + 1
        status_list.append(validated_count)
    except Exception as error:
        error_message = lambda_mgn_utils.handle_error_with_pid(error,"")
        return_dict[factoryserver['server_name']] = error_message


def set_account_job_id(account, action_result):
    if action_result is not None and "ERROR" in action_result:
        account['job_id'] = action_result

    return account


def get_action_result(factoryservers, action):
    final_result = []
    for account in factoryservers:
        action_result = None
        target_account_creds = lambda_mgn_utils.assume_role(str(account['aws_accountid']), str(account['aws_region']))
        target_account_session = lambda_mgn_utils.get_session(target_account_creds, account['aws_region'])
        mgn_client_base = target_account_session.client("mgn", account['aws_region'])
        if action.strip() == 'Launch Test Instances':
            action_result = launch_test_servers(account, mgn_client_base)
            account = set_account_job_id(account, action_result)
        elif action.strip() == 'Launch Cutover Instances':
            action_result = launch_cutover_servers(account, mgn_client_base)
            account = set_account_job_id(account, action_result)
        elif action.strip() == '- Terminate Launched instances':
            action_result = terminate_launched_instances(account, mgn_client_base)
        final_result.append(action_result)
        if action_result is not None and "ERROR" in action_result:
            log.error(str(action_result))
            return action_result, final_result

    return action_result, final_result


def verify_result(final_result, action):
    is_success = True
    for result in final_result:
        if result is not None and 'ERROR' in result:
            is_success = False
    if is_success == True:
        msg = 'SUCCESS: ' + action.strip() + ' was completed for all servers in this Wave'
        log.info(msg)
    else:
        msg = 'ERROR: ' + action.strip() + ' failed'
        log.error(msg)

    return msg


def verify_final_status(return_dict, action, final_status, total_servers_count):
    if len(return_dict.values()) > 0:
        log.error("ERROR: " + action.strip() + " failed")
        print(return_dict.values())
        msg = str(return_dict.values()[0])
    else:
        if final_status == total_servers_count:
            msg = "SUCCESS: " + action.strip() + " for all servers in this Wave"
            log.info(msg)
        else:
            msg = "ERROR: " + action.strip() + " failed"
            log.error(msg)

    return msg


def multithread_processing(factoryservers, action):
    # Enable multithreading
    processes = []
    manager = multiprocessing.Manager()
    status_list = manager.list()
    return_dict = manager.dict()
    total_servers_count = 0
    max_threads = 30
    for account in factoryservers:
        total_servers_count = total_servers_count + len(account['servers'])
        target_account_creds = lambda_mgn_utils.assume_role(
            str(account['aws_accountid']), str(account['aws_region']))

        message_suffix = lambda_mgn_utils.build_logging_message(
            "", account['aws_accountid'], account['aws_region'], "")

        print("##################################################################################")
        print(f"### Multithread processing Action, in Account: {message_suffix} ###")
        print("##################################################################################")
        # Splitting the list into smaller chunks, max 30 chunks
        if len(account['servers']) < max_threads:
            for serverlist in lambda_mgn_utils.chunks(
                account['servers'], len(account['servers'])):
                print(serverlist)
                p = multiprocessing.Process(target=multiprocessing_action, args=(
                    serverlist, target_account_creds, account['aws_region'], 
                    action, return_dict, status_list, account['aws_accountid'],
                    account['aws_region']))
                processes.append(p)
                p.start()
        else:
            for serverlist in lambda_mgn_utils.chunks(
                account['servers'], max_threads):
                print(serverlist)
                p = multiprocessing.Process(target=multiprocessing_action, args=(
                    serverlist, target_account_creds, account['aws_region'],
                    action, return_dict, status_list, account['aws_accountid'],
                    account['aws_region']))
                processes.append(p)
                p.start()
        
    return processes, status_list, return_dict, total_servers_count
    

def get_final_status(processes, status_list):
    for process in processes:
        process.join()
    final_status = 0
    for item in status_list:
        final_status += item
    print("")

    return final_status


def manage_action(factoryservers, action):
    try:
        actions = ['Launch Test Instances', 
                   'Launch Cutover Instances', 
                   '- Terminate Launched instances']
        if action.strip() in actions:
            action_result, final_result = get_action_result(
                factoryservers, action)
            if action_result is not None and "ERROR" in action_result:
                return action_result
            msg = verify_result(final_result, action)
            return msg
        else:
            # multithread processing
            processes, status_list, return_dict, total_servers_count = \
                multithread_processing(factoryservers, action) 

            # Waiting for all processes to finish
            final_status = get_final_status(processes, status_list)

            # Check if any errors in the updating process
            msg = verify_final_status(return_dict, action,
                                      final_status, total_servers_count)
            return msg
    except Exception as error:
        error_message = lambda_mgn_utils.handle_error(
            error, "ERROR: ", "", False)
        return error_message
