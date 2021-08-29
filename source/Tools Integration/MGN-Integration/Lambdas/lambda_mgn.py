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
import sys
import json
import os
import boto3
import botocore.exceptions
import lambda_mgn_template
import lambda_mgn_launch
import logging
import multiprocessing
from botocore import config

log = logging.getLogger()
log.setLevel(logging.INFO)

if 'solution_identifier' in os.environ:
    solution_identifier= json.loads(os.environ['solution_identifier'])
    user_agent_extra_param = {"user_agent_extra":solution_identifier}
    boto_config = config.Config(**user_agent_extra_param)
else:
    boto_config = None

application = os.environ['application']
environment = os.environ['environment']

servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)

servers_table = boto3.resource('dynamodb').Table(servers_table_name)
apps_table = boto3.resource('dynamodb').Table(apps_table_name)

# Pagination for server DynamoDB table scan
def scan_dynamodb_server_table():
    response = servers_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        log.info("Last Evaluate key for server is   " + str(response['LastEvaluatedKey']))
        response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])
    return(scan_data)

#Pagination for app DynamoDB table scan
def scan_dynamodb_app_table():
    response = apps_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        log.info("Last Evaluate key for app is   " + str(response['LastEvaluatedKey']))
        response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])
    return(scan_data)

def assume_role(account_id):

    sts_client = boto3.client('sts')
    role_arn = 'arn:aws:iam::' + account_id + ':role/Factory-Automation'
    log.info("Creating new session with role: {}".format(role_arn))

    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.

    try:
        user = sts_client.get_caller_identity()['Arn']
        log.info('Logged in as: ' + user)
        sessionname = user.split('/')[1]
        response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=sessionname)
        credentials = response['Credentials']
        return credentials
    except botocore.exceptions.ClientError as e:
        log.error(str(e))
        return {"ERROR": e}

def get_session(creds, region):
    try:
        session = boto3.Session(
            region_name = region,
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']
        )
        return session
    except botocore.exceptions.ClientError as e:
        log.error(str(e))
        return {"ERROR": e}

def get_factory_servers(waveid, accountid):
    try:
        # Get all Apps and servers from migration factory
        getserver = scan_dynamodb_server_table()
        servers = sorted(getserver, key = lambda i: i['server_name'])
        getapp = scan_dynamodb_app_table()
        apps = sorted(getapp, key = lambda i: i['app_name'])

        # Get Unique target AWS account and region
        aws_accounts = []
        for app in apps:
            if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                if str(app['wave_id']) == str(waveid):
                    if len(str(app['aws_accountid']).strip()) == 12 and str(app['aws_accountid']).isdigit():
                        target_account = {}
                        target_account['aws_accountid'] = str(app['aws_accountid']).strip()
                        target_account['aws_region'] = app['aws_region'].lower().strip()
                        target_account['servers'] = []
                        if accountid.strip() == 'All Accounts':
                            if target_account not in aws_accounts:
                                aws_accounts.append(target_account)
                        else:
                            if str(app['aws_accountid']).strip() == str(accountid).strip():
                                if target_account not in aws_accounts:
                                    aws_accounts.append(target_account)
                    else:
                        msg = "ERROR: Incorrect AWS Account Id for app: " + app['app_name']
                        log.error(msg)
                        return msg
        if len(aws_accounts) == 0:
            msg = "ERROR: Server list for wave " + waveid + " is empty...."
            log.error(msg)
            return msg

        # Get server list
        for account in aws_accounts:
            for app in apps:
                if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                    if str(app['wave_id']) == str(waveid):
                        if str(app['aws_accountid']).strip() == str(account['aws_accountid']):
                            if app['aws_region'].lower().strip() == account['aws_region']:
                                for server in servers:
                                    if 'app_id' in server:
                                        if server['app_id'] == app['app_id']:
                                            account['servers'].append(server)
            if len(account['servers']) == 0:
                msg = "ERROR: Server list for wave " + waveid + " and account: " + account['aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
                log.error(msg)
                return msg
        return aws_accounts
    except botocore.exceptions.ClientError as error:
        if ":" in str(error):
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            msg = "ERROR: " + err
            log.error(msg)
            return msg
        else:
            msg = "ERROR: " + str(error)
            log.error(msg)
            return msg

def verify_target_account_servers(serverlist):
    # Check each AWS account and region one by one
    verified_servers = serverlist
    try:
        # Enable multithreading
        processes = []
        manager = multiprocessing.Manager()
        return_dict_id = manager.dict()
        for account in verified_servers:
            source_server_ids = []
            target_account_creds = assume_role(str(account['aws_accountid']))
            target_account_session = get_session(target_account_creds, account['aws_region'])
            mgn_client_base = target_account_session.client("mgn", region_name=account['aws_region'], config=boto_config)
            mgn_sourceservers = mgn_client_base.describe_source_servers(filters={})
            log.info("Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'])
            print(mgn_sourceservers)
            for factoryserver in account['servers']:
                if 'server_fqdn' not in factoryserver:
                    msg = "ERROR: server_fqdn does not exist for server: " + factoryserver['server_name']
                    log.error(msg)
                    return msg
                else:
                    isServerExist = False
                    for sourceserver in mgn_sourceservers['items']:
                        # Check if the factory server exist in Application Migration Service
                        if factoryserver['server_name'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['hostname'].lower().strip():
                            isServerExist = True
                        elif factoryserver['server_name'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                            isServerExist = True
                        elif factoryserver['server_fqdn'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['hostname'].lower().strip():
                            isServerExist = True
                        elif factoryserver['server_fqdn'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                            isServerExist = True
                        else:
                            continue
                        # Get EC2 launch template Id for the source server in Application Migration Service
                        if isServerExist == True:
                            if sourceserver['isArchived'] == False:
                                factoryserver['source_server_id'] = sourceserver['sourceServerID']
                                source_server_ids.append(factoryserver['source_server_id'])
                                if sourceserver['dataReplicationInfo']['dataReplicationState'].lower() != 'disconnected':
                                    p = multiprocessing.Process(target=multiprocessing_launch_template_id, args=(target_account_creds, account['aws_region'], factoryserver, return_dict_id))
                                    processes.append(p)
                                    p.start()
                                    break
                            else:
                                # Check if there is another server with the same name registered in MGN that is not archived, this can occur if someone archives a server and then redploys the agent to the same server, it then gets a new MGN id.
                                isSecondServerExist = False
                                for sourceserver1 in mgn_sourceservers['items']:
                                    if sourceserver1['isArchived'] == False and sourceserver['sourceServerID'] != sourceserver1['sourceServerID']:
                                        if factoryserver['server_name'].lower().strip() == sourceserver1['sourceProperties']['identificationHints']['hostname'].lower().strip():
                                            isSecondServerExist = True
                                        elif factoryserver['server_name'].lower().strip() == sourceserver1['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                                            isSecondServerExist = True
                                        elif factoryserver['server_fqdn'].lower().strip() == sourceserver1['sourceProperties']['identificationHints']['hostname'].lower().strip():
                                            isSecondServerExist = True
                                        elif factoryserver['server_fqdn'].lower().strip() == sourceserver1['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                                            isSecondServerExist = True
                                        else:
                                            continue
                                if isSecondServerExist:
                                    continue
                                else:
                                    msg = "ERROR: Server: " + factoryserver['server_name'] + " is archived in Application Migration Service (Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + "), Please reinstall the agent"
                                    log.error(msg)
                                    return msg
                    if isServerExist == False:
                        msg = "ERROR: Server: " + factoryserver['server_name'] + " does not exist in Application Migration Service (Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + "), Please reinstall the agent."
                        log.error(msg)
                        return msg
            account['source_server_ids'] = source_server_ids
        # Waiting for all processes to finish
        for process in processes:
            process.join()
        # Get ec2LaunchTemplateID from the dictionary
        for account in verified_servers:
            for factoryserver in account['servers']:
                if factoryserver['server_name'] in return_dict_id:
                    factoryserver['launch_template_id'] = return_dict_id[factoryserver['server_name']]
        return verified_servers
    except botocore.exceptions.ClientError as error:
        if ":" in str(error):
            log.error("ERROR: " + str(error))
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            msg = "ERROR: " + err
            return msg
        else:
            msg = "ERROR: " + str(error)
            log.error(msg)
            return msg

def multiprocessing_launch_template_id(creds, region, factoryserver, return_dict_id):
    session = get_session(creds, region)
    mgn_client = session.client("mgn", region_name=region, config=boto_config)
    log.info("Pid: " + str(os.getpid()) + " - Getting EC2 Launch template Id for " + factoryserver['server_name'])
    log.info("Pid: " + str(os.getpid()) + " - " + str(factoryserver))
    ec2LaunchTemplateID = mgn_client.get_launch_configuration(sourceServerID = factoryserver['source_server_id'])['ec2LaunchTemplateID']
    log.info("Pid: " + str(os.getpid()) + " - " + factoryserver['server_name'] + " - " + ec2LaunchTemplateID)
    return_dict_id[factoryserver['server_name']] = ec2LaunchTemplateID

def lambda_handler(event, context):
    try:
        # Check input parameters
        body = json.loads(event['body'])
        if 'waveid' not in body:
            msg = 'ERROR: wave id is required'
            log.error(msg)
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': json.dumps(msg)}
        if 'accountid' not in body:
            msg = 'ERROR: AWS Account Id is required'
            log.error(msg)
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': json.dumps(msg)}
        if 'action' not in body:
            msg = 'ERROR: test and cutover action is required'
            log.error(msg)
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': json.dumps(msg)}
        else:
            isValidAction = False
            if body['action'].strip() == 'Validate Launch Template':
                isValidAction = True
            elif body['action'].strip() == 'Launch Test Instances':
                isValidAction = True
            elif body['action'].strip() == 'Mark as Ready for Cutover':
                isValidAction = True
            elif body['action'].strip() == 'Launch Cutover Instances':
                isValidAction = True
            elif body['action'].strip() == 'Finalize Cutover':
                isValidAction = True
            elif body['action'].strip() == '- Revert to ready for testing':
                isValidAction = True
            elif body['action'].strip() == '- Revert to ready for cutover':
                isValidAction = True
            elif body['action'].strip() == '- Terminate Launched instances':
                isValidAction = True
            elif body['action'].strip() == '- Disconnect from AWS':
                isValidAction = True
            elif body['action'].strip() == '- Mark as archived':
                isValidAction = True

            if isValidAction == False:
                msg = 'ERROR: Incorrect test or cutover action'
                log.error(msg)
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': json.dumps(msg)}

        # Get server list
        serverlist = get_factory_servers(body['waveid'], str(body['accountid']).strip())
        if serverlist is not None and 'ERROR' in serverlist:
            log.error(str(serverlist))
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': json.dumps(serverlist)}
        print("*** Factory Servers ***")
        print(serverlist)

        # Verify servers
        verified_servers = verify_target_account_servers(serverlist)
        if verified_servers is not None and 'ERROR' in verified_servers:
            log.error(str(verified_servers))
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': json.dumps(verified_servers)}
        print("*** Verified Servers ***")
        print(verified_servers)

        # Update EC2 Launch template
        update_EC2_template = lambda_mgn_template.update_launch_template(verified_servers, body['action'])
        if update_EC2_template is not None and 'ERROR' in update_EC2_template:
            log.error(str(update_EC2_template))
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': json.dumps(update_EC2_template)}
        if update_EC2_template is not None and 'SUCCESS' in update_EC2_template:
            log.info(str(update_EC2_template))
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 200, 'body': json.dumps(update_EC2_template)}

        # Manage MGN Actions
        if body['action'].strip() != 'Validate Launch Template':
            manage_mgn_servers = lambda_mgn_launch.manage_action(verified_servers, body['action'])
            if manage_mgn_servers is not None and 'ERROR' in manage_mgn_servers:
                log.error(str(manage_mgn_servers))
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': json.dumps(manage_mgn_servers)}
            if manage_mgn_servers is not None and 'SUCCESS' in manage_mgn_servers:
                log.info(str(manage_mgn_servers))
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 200, 'body': json.dumps(manage_mgn_servers)}

    except Exception as e:
        log.error(str(e))
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 400, 'body': json.dumps(str(e))}
