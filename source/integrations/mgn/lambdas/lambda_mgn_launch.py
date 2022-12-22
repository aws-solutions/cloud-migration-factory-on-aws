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

from __future__ import print_function
import requests
import datetime
import json
import os
import boto3
import lambda_mgn
import botocore.exceptions
from boto3.dynamodb.conditions import Key, Attr
import logging
import multiprocessing

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

# Launch test servers in application migration service
def launch_test_servers(account, mgn_client):
  try:
    # Enable multithreading
    processes = []
    manager = multiprocessing.Manager()
    log.info("*** Launching Test Servers in account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + " ***")
    action_result = mgn_client.start_test(sourceServerIDs=account['source_server_ids'])
    log.info(action_result)
    if action_result['ResponseMetadata']['HTTPStatusCode'] != 202 :
        msg = "ERROR: Launch test servers failed for account: " + account['aws_accountid'] + ", Region: " + account['aws_region']
        log.error(msg)
        return msg
    else:
        msg = "SUCCESS: created test launch job for account: " + account['aws_accountid'] + ", Region: " + account['aws_region']  + " - Job Id is: " + action_result['job']['jobID']
        log.info(msg)
        for server in account['servers']:
            launch_type = "Test"
            p = multiprocessing.Process(target=multiprocessing_usage, args=(server, launch_type))
            processes.append(p)
            p.start()
        # Waiting for all processes to finish
        for process in processes:
            process.join()
        return  action_result['job']['jobID']
  except Exception as error:
        if ":" in str(error):
            log.error(str(error))
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            return "ERROR: " + err + " - in account: " + account['aws_accountid'] + ", Region: " + account['aws_region']
        else:
            log.error(str(error))
            return "ERROR: " + str(error) + " - in account: " + account['aws_accountid'] + ", Region: " + account['aws_region']

# Launch cutover servers in application migration service
def launch_cutover_servers(account, mgn_client):
  try:
    # Enable multithreading
    processes = []
    manager = multiprocessing.Manager()
    log.info("*** Launching Cutover Servers in account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + " ***")
    action_result = mgn_client.start_cutover(sourceServerIDs=account['source_server_ids'])
    log.info(action_result)
    if action_result['ResponseMetadata']['HTTPStatusCode'] != 202 :
        msg = "ERROR: Launch cutover servers failed for account: " + account['aws_accountid'] + ", Region: " + account['aws_region']
        log.error(msg)
        return msg
    else:
        msg = "SUCCESS: created cutover launch job for account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + " - Job Id is: " + action_result['job']['jobID']
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
        if ":" in str(error):
            log.error(str(error))
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            return "ERROR: " + err + " - in account: " + account['aws_accountid'] + ", Region: " + account['aws_region']
        else:
            log.error(str(error))
            return "ERROR: " + str(error) + " - in account: " + account['aws_accountid'] + ", Region: " + account['aws_region']

def multiprocessing_usage(server, launch_type):
    existing_attr = servers_table.get_item(Key={'server_id': server['server_id']})
    existing_attr['Item']['migration_status'] = launch_type + " instance launched"
    resp = servers_table.put_item(Item=existing_attr['Item'])
    log.info("Pid: " + str(os.getpid()) + " - This is " + launch_type + " Launch, migration_status updated")
    if AnonymousUsageData == "Yes":
        usage_data = {"Solution": "SO0097",
                    "UUID": s_uuid,
                    "Status": "Migrated",
                    "TimeStamp": str(datetime.datetime.now()),
                    "Region": region
                    }
        send_anonymous_data = requests.post(url, data = json.dumps(usage_data), headers = {'content-type': 'application/json'})
        url_ce = "https://s20a21yvzd.execute-api.us-east-1.amazonaws.com/prod/launch"
        mgn_data = {"UUID": s_uuid,
                   "version": "MGN-v3"
                  }
        server_migrated = requests.post(url_ce, data = json.dumps(mgn_data))

# This function will terminate all launched instances
def terminate_launched_instances(account, mgn_client):
  try:
    log.info("*** Terminating Test Servers in account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + " ***")
    action_result = mgn_client.terminate_target_instances(sourceServerIDs=account['source_server_ids'])
    log.info(action_result)
    if action_result['ResponseMetadata']['HTTPStatusCode'] != 202 :
        msg = "ERROR: Terminate test servers failed for account: " + account['aws_accountid'] + ", Region: " + account['aws_region']
        log.error(msg)
        return msg
    else:
        msg = "SUCCESS: Successfully created terminate server job for account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + " - Job Id is: " + action_result['job']['jobID']
        log.info(msg)
        return msg
  except Exception as error:
        if ":" in str(error):
            log.error(str(error))
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            return "ERROR: " + err + " - in account: " + account['aws_accountid'] + ", Region: " + account['aws_region']
        else:
            log.error(str(error))
            return "ERROR: " + str(error) + " - in account: " + account['aws_accountid'] + ", Region: " + account['aws_region']

def multiprocessing_action(serverlist, creds, region, action, return_dict, status_list, aws_accountid, aws_region):
  try:
    session = lambda_mgn.get_session(creds, region)
    mgn_client = session.client("mgn", region)
    validated_count = 0
    for factoryserver in serverlist:
        if action.strip() == 'Mark as Ready for Cutover':
            log.info("*** Mark as Ready for Cutover in account: " + aws_accountid + ", Region: " + aws_region + " ***")
            state = {'state':'READY_FOR_CUTOVER'}
            action_result = mgn_client.change_server_life_cycle_state(lifeCycle=state, sourceServerID=factoryserver['source_server_id'])
        elif action.strip() == 'Finalize Cutover':
            log.info("*** Finalize Cutover in account: " + aws_accountid + ", Region: " + aws_region + " ***")
            action_result = mgn_client.disconnect_from_service(sourceServerID=factoryserver['source_server_id'])
            state = {'state':'CUTOVER'}
            action_result = mgn_client.change_server_life_cycle_state(lifeCycle=state, sourceServerID=factoryserver['source_server_id'])
        elif action.strip() == '- Revert to ready for testing':
            log.info("*** Revert to ready for testing in account: " + aws_accountid + ", Region: " + aws_region + " ***")
            state = {'state':'READY_FOR_TEST'}
            action_result = mgn_client.change_server_life_cycle_state(lifeCycle=state, sourceServerID=factoryserver['source_server_id'])
        elif action.strip() == '- Revert to ready for cutover':
            log.info("*** Revert to ready for cutover in account: " + aws_accountid + ", Region: " + aws_region + " ***")
            state = {'state':'READY_FOR_CUTOVER'}
            action_result = mgn_client.change_server_life_cycle_state(lifeCycle=state, sourceServerID=factoryserver['source_server_id'])
        elif action.strip() == '- Disconnect from AWS':
            log.info("*** Disconnect from AWS in account: " + aws_accountid + ", Region: " + aws_region + " ***")
            action_result = mgn_client.disconnect_from_service(sourceServerID=factoryserver['source_server_id'])
        elif action.strip() == '- Mark as archived':
            log.info("*** Mark as archived in account: " + aws_accountid + ", Region: " + aws_region + " ***")
            action_result = mgn_client.mark_as_archived(sourceServerID=factoryserver['source_server_id'])
        
        if action_result['ResponseMetadata']['HTTPStatusCode'] != 200:
            msg = "Pid: " + str(os.getpid()) + " - ERROR: " + action.strip() + " failed for server: " + factoryserver['server_name'] + " - in account: " + aws_accountid + ", Region: " + aws_region
            log.error(msg)
            return_dict[factoryserver['server_name']] = msg
        else:
            msg = "Pid: " + str(os.getpid()) + " - SUCCESS: " + action.strip() + " for server: " + factoryserver['server_name'] + " - in account: " + aws_accountid + ", Region: " + aws_region
            log.info(msg)
            validated_count = validated_count + 1
    status_list.append(validated_count)
  except Exception as error:
        if ":" in str(error):
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + err)
            return_dict[factoryserver['server_name']] = "ERROR: " + err
        else:
            log.error("Pid: " + str(os.getpid()) + " - ERROR: " + str(error))
            return_dict[factoryserver['server_name']] = "ERROR: " + str(error)

def manage_action(factoryservers, action):
  try:
    if action.strip() == 'Launch Test Instances' or action.strip() == 'Launch Cutover Instances' or action.strip() == '- Terminate Launched instances':
        final_result = []
        for account in factoryservers:
            action_result = None
            target_account_creds = lambda_mgn.assume_role(str(account['aws_accountid']))
            target_account_session = lambda_mgn.get_session(target_account_creds, account['aws_region'])
            mgn_client_base = target_account_session.client("mgn", account['aws_region'])
            if action.strip() == 'Launch Test Instances':
                action_result = launch_test_servers(account, mgn_client_base)
                if action_result is not None and "ERROR" in action_result:
                   account['job_id'] = action_result
            elif action.strip() == 'Launch Cutover Instances':
                action_result = launch_cutover_servers(account, mgn_client_base)
                if action_result is not None and "ERROR" in action_result:
                   account['job_id'] = action_result
            elif action.strip() == '- Terminate Launched instances':
                action_result = terminate_launched_instances(account, mgn_client_base)
            final_result.append(action_result)
            if action_result is not None and "ERROR" in action_result:
                log.error(str(action_result))
                return action_result
        isSuccess = True
        for result in final_result:
            if result is not None and 'ERROR' in result:
                isSuccess = False
        if isSuccess == True:
            msg = 'SUCCESS: ' + action.strip() + ' was completed for all servers in this Wave'
            log.info(msg)
            return msg
        else:
            msg = 'ERROR: ' + action.strip() + ' failed'
            log.error(msg)
            return msg
    else:
        # Enable multithreading
        processes = []
        manager = multiprocessing.Manager()
        status_list = manager.list()
        return_dict = manager.dict()
        total_servers_count = 0
        max_threads = 30
        for account in factoryservers:
            total_servers_count = total_servers_count + len(account['servers'])
            target_account_creds = lambda_mgn.assume_role(str(account['aws_accountid']))
            print("##################################################################################")
            print("### Multithread processing Action, in Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + " ###")
            print("##################################################################################")
            # Splitting the list into smaller chunks, max 30 chunks
            if len(account['servers']) < max_threads:
                for serverlist in chunks(account['servers'], len(account['servers'])):
                    print(serverlist)
                    p = multiprocessing.Process(target=multiprocessing_action, args=(serverlist, target_account_creds, account['aws_region'], action, return_dict, status_list, account['aws_accountid'], account['aws_region']))
                    processes.append(p)
                    p.start()
            else:
                for serverlist in chunks(account['servers'], max_threads):               
                    print(serverlist)   
                    p = multiprocessing.Process(target=multiprocessing_action, args=(serverlist, target_account_creds, account['aws_region'], action, return_dict, status_list, account['aws_accountid'], account['aws_region']))
                    processes.append(p)
                    p.start()
     
        # Waiting for all processes to finish
        for process in processes:
            process.join()
        final_status = 0
        for item in status_list:
            final_status += item
        print("")

        # Check if any errors in the updating process
        if len(return_dict.values()) > 0:
            log.error("ERROR: "  + action.strip() + " failed")
            print(return_dict.values())
            return str(return_dict.values()[0])
        else:
            if final_status == total_servers_count:
                msg = "SUCCESS: " + action.strip() + " for all servers in this Wave"
                log.info(msg)
                return msg
            else:
                msg = "ERROR: "  + action.strip() + " failed"
                log.error(msg)
                return msg

  except Exception as error:
        if ":" in str(error):
            log.error(str(error))
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            return "ERROR: " + err
        else:
            log.error(str(error))
            return "ERROR: " + str(error)

def chunks(l, n):
    for i in range(0, n):
        yield l[i::n]