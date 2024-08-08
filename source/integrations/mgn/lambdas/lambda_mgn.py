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
import json
import os
import botocore.exceptions
import logging
import multiprocessing
import lambda_mgn_template
import lambda_mgn_launch
import lambda_mgn_utils
from policy import MFAuth
import cmf_boto

MGN_ACTIONS = [
    'Validate Launch Template',
    'Launch Test Instances',
    'Mark as Ready for Cutover',
    'Launch Cutover Instances',
    'Finalize Cutover',
    '- Revert to ready for testing',
    '- Revert to ready for cutover',
    '- Terminate Launched instances',
    '- Disconnect from AWS',
    '- Mark as archived'
]

log = logging.getLogger()
log.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}
application = os.environ['application']
environment = os.environ['environment']

servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)

servers_table = cmf_boto.resource('dynamodb').Table(servers_table_name)
apps_table = cmf_boto.resource('dynamodb').Table(apps_table_name)


# Pagination for server DynamoDB table scan
def scan_dynamodb_server_table():
    response = servers_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        log.info("Last Evaluate key for server is   " + str(response['LastEvaluatedKey']))
        response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response['Items'])
    return (scan_data)


# Pagination for app DynamoDB table scan
def scan_dynamodb_app_table():
    response = apps_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        log.info("Last Evaluate key for app is   " + str(response['LastEvaluatedKey']))
        response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response['Items'])
    return (scan_data)


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


def is_valid_aws_account_id(account_id):
    if len(str(account_id).strip()) == 12 and str(account_id).isdigit():
        return True
    else:
        return False


def add_target_account(target_aws_accounts, target_aws_account):
    if target_aws_account not in target_aws_accounts:
        target_aws_accounts.append(target_aws_account)


def get_valid_account(app, account_id, aws_accounts, app_ids):
    target_account = {
        'aws_accountid': str(app['aws_accountid']).strip(),
        'aws_region': app['aws_region'].lower().strip(),
        'servers': []
    }
    # If account Id is all accounts, skip the check
    if account_id.strip() == 'All Accounts':
        add_target_account(aws_accounts, target_account)
    else:
        # Check what parameter is used. If account Id is used, a specific
        # account will be added to the list. If app_ids is used,
        # AWS account Id of that specific app will be added to the list
        if account_id != '' and \
                str(app['aws_accountid']).strip() == str(account_id).strip():
            add_target_account(aws_accounts, target_account)
        elif len(app_ids) > 0 and app['app_id'] in app_ids:
            add_target_account(aws_accounts, target_account)

    return aws_accounts


def get_target_aws_accounts(wave_id, apps, account_id, app_ids):
    aws_accounts = []
    errors = []
    for app in apps:
        if is_valid_app(app) and str(app['wave_id']) == str(wave_id):
            if is_valid_aws_account_id(app['aws_accountid']):
                aws_accounts = get_valid_account(
                    app, account_id, aws_accounts, app_ids)
            else:
                msg = f"Incorrect AWS Account Id specified in : {app['app_name']}"
                log.error(msg)
                errors.append(msg)

    if len(aws_accounts) == 0:
        msg = (f"WARNING: No Target AWS accounts for wave id {wave_id}, "
               f"this could be due to no applications in the wave, "
               f"or that there are no servers with a Rehost Migration Strategy.")
        log.error(msg)
        errors.append(msg)
        return [], errors

    return aws_accounts, errors


def add_servers_to_target_account_matching_app(servers, account, app_id):
    for server in servers:
        if 'r_type' in server and server['r_type'] == 'Rehost' and 'app_id' in server and server['app_id'] == app_id:
            account['servers'].append(server)


def is_valid_app(app):
    if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app and 'app_id' in app:
        return True
    else:
        return False


def is_app_same_account_and_region(account, app):
    app_account_id = clean_value(app['aws_accountid'])
    app_region = clean_value(app['aws_region'])
    account_id = clean_value(account['aws_accountid'])
    account_region = clean_value(account['aws_region'])

    if app_account_id == account_id and app_region == account_region:
        return True
    else:
        return False


def add_servers_to_target_accounts(target_aws_accounts, applications, servers, wave_id):
    errors = []
    for account in target_aws_accounts:
        for app in applications:
            if is_valid_app(app) and str(app['wave_id']) == str(wave_id):
                if is_app_same_account_and_region(account, app):
                    add_servers_to_target_account_matching_app(servers, account, app['app_id'])
        if len(account['servers']) == 0:
            msg = f"ERROR: No servers found in wave {wave_id} and AWS account:{account['aws_accountid']} " \
                  f"region: {account['aws_region']} with a Rehost migration strategy."
            log.error(msg)
            errors.append(msg)

    return errors


def add_rehost_servers_to_target_account(target_account, servers, app_id):
    for server in servers:
        if server['r_type'] == 'Rehost' and server['app_id'] == app_id:
            target_account['servers'].append(server)


def get_servers(target_aws_accounts, filtered_apps,
                waveid, servers):
    errors = []
    for account in target_aws_accounts:
        for app in filtered_apps:
            if is_valid_app(app) and str(app['wave_id']) == str(waveid):
                if is_app_same_account_and_region(account, app):
                    add_rehost_servers_to_target_account(account, servers, app['app_id'])
        if len(account['servers']) == 0:
            msg = (f"WARNING: Server list for wave id {waveid} and account: {account['aws_accountid']} "
                   f"region: {account['aws_region']} is empty, "
                   f"no servers with a 'Rehost' Migration Strategy found.")
            log.error(msg)
            errors.append(msg)

    return target_aws_accounts, errors


def get_factory_servers(waveid, accountid, appidlist, server_ids=None):
    errors = []
    try:
        # Get all Apps and servers from migration factory
        cmf_servers = scan_dynamodb_server_table()

        cmf_servers = filter_items(cmf_servers, 'server_id', server_ids)
        cmf_servers = sorted(cmf_servers, key=lambda i: i['server_name'])

        cmf_app = scan_dynamodb_app_table()
        cmf_app = filter_items(cmf_app, 'app_id', appidlist)
        cmf_app = sorted(cmf_app, key=lambda i: i['app_name'])
        if accountid == '' and len(appidlist) == 0:
            msg = "ERROR: Either AWS Account Id or Application Id List must be provided"
            log.error(msg)
            errors.append(msg)
            return [], errors

        # Get Unique target AWS account and region
        target_aws_accounts, target_aws_accounts_errors = get_target_aws_accounts(waveid, cmf_app, accountid, appidlist)
        if target_aws_accounts_errors:
            errors.extend(target_aws_accounts_errors)
            return [], errors

        # Get server list
        target_aws_accounts, get_servers_errors = get_servers(
            target_aws_accounts, cmf_app,
            waveid, cmf_servers)

        errors.extend(get_servers_errors)

        return target_aws_accounts, errors
    except botocore.exceptions.ClientError as error:
        msg = handle_client_error(error)
        errors.append(msg)
        return [], errors


def handle_client_error(error):
    log.error(error)
    if ":" in str(error):
        err = ''
        msgs = str(error).split(":")[1:]
        for msg in msgs:
            err = err + msg
        msg = "ERROR: " + err
        log.error(msg)
    else:
        msg = "ERROR: " + str(error)
        log.error(msg)

    return msg


def clean_value(value):
    return value.lower().strip()


def is_cmf_server_match_for_mgn_ip_address(interface, cmf_server):
    cmf_server_name = clean_value(cmf_server['server_name'])
    cmf_server_fqdn = clean_value(cmf_server['server_fqdn'])

    if interface['isPrimary'] is True:
        for ip_address in interface['ips']:
            if cmf_server_name == clean_value(ip_address) or cmf_server_fqdn == clean_value(ip_address):
                return True

    return False


def is_cmf_server_match_for_mgn_hostname(mgn_source_server, cmf_server):
    cmf_server_name = clean_value(cmf_server['server_name'])
    cmf_server_fqdn = clean_value(cmf_server['server_fqdn'])
    mgn_server_hostname = clean_value(mgn_source_server['sourceProperties']['identificationHints']['hostname'])
    mgn_server_fqdn = clean_value(mgn_source_server['sourceProperties']['identificationHints']['fqdn'])

    if cmf_server_name == mgn_server_hostname or cmf_server_name == mgn_server_fqdn \
            or cmf_server_fqdn == mgn_server_hostname or cmf_server_fqdn == mgn_server_fqdn:
        return True

    return False


def is_cmf_server_matching_mgn_source_server(cmf_server, mgn_source_server):
    # Check if any IP addresses in MGN record match with CMF.
    if 'networkInterfaces' in mgn_source_server['sourceProperties']:
        for interface in mgn_source_server['sourceProperties']['networkInterfaces']:
            if is_cmf_server_match_for_mgn_ip_address(interface, cmf_server):
                return True

    if is_cmf_server_match_for_mgn_hostname(mgn_source_server, cmf_server):
        return True

    return False


def add_mgn_launch_template_id_to_cmf_servers(verified_servers, multiprocessing_launch_template_ids):
    for account in verified_servers:
        for factoryserver in account['servers']:
            if factoryserver['server_name'] in multiprocessing_launch_template_ids:
                factoryserver['launch_template_id'] = multiprocessing_launch_template_ids[factoryserver['server_name']]


def verify_account_server(account, mgn_sourceservers, processes, errors,
                          source_server_ids, target_account_creds,
                          mgn_source_server_launch_template_ids):
    msg = ""
    for factoryserver in account['servers']:
        if 'server_fqdn' not in factoryserver:
            msg = "ERROR: server_fqdn does not exist for server: " + factoryserver['server_name']
            log.error(msg)
            return msg, account, source_server_ids
        else:
            is_server_exist, is_mgn_server_archived, mgn_sourceservers = \
                verify_server(
                    mgn_sourceservers, factoryserver,
                    source_server_ids, target_account_creds,
                    account, mgn_source_server_launch_template_ids,
                    processes)

            errors = validate_server_exist_and_archived(
                is_server_exist, is_mgn_server_archived,
                factoryserver, account, errors)

            errors = validate_mgn_server_archived(
                is_mgn_server_archived,
                factoryserver, account, errors)

    return msg, account, source_server_ids


def verify_server(mgn_sourceservers, factoryserver,
                  source_server_ids, target_account_creds,
                  account, mgn_source_server_launch_template_ids,
                  processes):
    is_server_exist = False
    is_mgn_server_archived = False
    for sourceserver in mgn_sourceservers:
        # Check if the factory server exist in Application Migration Service
        is_server_exist = is_cmf_server_matching_mgn_source_server(factoryserver, sourceserver)
        if not is_server_exist:
            # moved to next mgn source server.
            continue

        # Get EC2 launch template Id for the source server in Application Migration Service
        if sourceserver['isArchived']:
            is_mgn_server_archived = True
            factoryserver['source_server_id'] = sourceserver['sourceServerID']
        else:
            is_mgn_server_archived = False
            factoryserver['source_server_id'] = sourceserver['sourceServerID']
            source_server_ids.append(factoryserver['source_server_id'])
            if sourceserver['dataReplicationInfo']['dataReplicationState'].lower() != 'disconnected':
                p = multiprocessing.Process(
                    target=get_mgn_launch_template_id,
                    args=(target_account_creds,
                          account['aws_region'],
                          factoryserver,
                          mgn_source_server_launch_template_ids)
                )
                processes.append(p)
                p.start()
                break

    return is_server_exist, is_mgn_server_archived, mgn_sourceservers


def validate_server_exist_and_archived(is_server_exist, is_mgn_server_archived,
                                       factoryserver, account, errors):
    if not is_server_exist and not is_mgn_server_archived:
        msg = f"ERROR: Server: {factoryserver['server_name']} does not exist in " \
              f"Application Migration Service (Account: {account['aws_accountid']}, Region: " \
              f"{account['aws_region']}). Please install the MGN agent."
        log.error(msg)
        errors.append(msg)

    return errors


def validate_mgn_server_archived(is_mgn_server_archived,
                                 factoryserver, account, errors):
    if is_mgn_server_archived:
        msg = f"ERROR: Server: {factoryserver['server_name']} ({factoryserver['source_server_id']})" + \
              f" is archived in Application Migration Service (Account: {account['aws_accountid']}, " \
              f"Region: {account['aws_region']}). Please reinstall the MGN agent."
        log.error(msg)
        errors.append(msg)

    return errors


def verify_target_account_servers(serverlist):
    # Check each AWS account and region one by one
    verified_servers = serverlist
    processes = []
    errors = []
    try:
        # Enable multithreading
        manager = multiprocessing.Manager()
        mgn_source_server_launch_template_ids = manager.dict()
        for account in verified_servers:
            source_server_ids = []
            log.info(f"Establishing session with AWS account "
                     f"{lambda_mgn_utils.obfuscate_account_id(account['aws_accountid'])} in {str(account['aws_region'])}")
            target_account_creds = lambda_mgn_utils.assume_role(
                account_id=str(account['aws_accountid']),
                region=str(account['aws_region'])
            )
            # has session returned an error.
            if 'ERROR' in target_account_creds:
                errors.append(
                    f"Account: {str(account['aws_accountid'])}, region {str(account['aws_region'])}. {str(target_account_creds['ERROR'])}")
                continue
            target_account_session = lambda_mgn_utils.get_session(target_account_creds,
                                                                  str(account['aws_region']))
            mgn_client_base = cmf_boto.session_client(target_account_session, "mgn", account['aws_region'])
            mgn_sourceservers = get_mgn_source_servers(mgn_client_base)

            msg, account, source_server_ids = verify_account_server(
                account, mgn_sourceservers, processes, errors,
                source_server_ids, target_account_creds,
                mgn_source_server_launch_template_ids)

            if msg != "":
                return msg

            account['source_server_ids'] = source_server_ids
        # Waiting for all processes to finish
        for process in processes:
            process.join()

        add_mgn_launch_template_id_to_cmf_servers(
            verified_servers, mgn_source_server_launch_template_ids)

        return verified_servers, errors
    except botocore.exceptions.ClientError as error:
        msg = handle_client_error(error)
        # prepend account and region to the error message if defined.
        if 'account' in locals():
            msg = f"Account: {str(account['aws_accountid'])}, region {str(account['aws_region'])}. {msg}"

        errors.append(msg)
        return verified_servers, errors


def get_mgn_launch_template_id(creds, region, factoryserver, mgn_source_server_launch_template_ids):
    msg_process_id = f"PID: {str(os.getpid())}"
    session = lambda_mgn_utils.get_session(creds, region)
    mgn_client = cmf_boto.session_client(session, "mgn", region_name=region)
    log.info(msg_process_id + " - Getting EC2 Launch template Id for " + factoryserver['server_name'])
    log.info(msg_process_id + " - " + str(factoryserver))
    ec2_launch_template_id = mgn_client.get_launch_configuration(sourceServerID=factoryserver['source_server_id'])[
        'ec2LaunchTemplateID']
    log.info(msg_process_id + " - " + factoryserver['server_name'] + " - " + ec2_launch_template_id)
    mgn_source_server_launch_template_ids[factoryserver['server_name']] = ec2_launch_template_id


def is_valid_action(action):
    if action in MGN_ACTIONS:
        return True

    return False


def validate_input_parameters(body):
    errors = []
    if 'waveid' not in body:
        msg = 'waveid is required.'
        log.error(msg)
        errors.append(msg)
    if 'accountid' not in body and 'appidlist' not in body:
        msg = 'Either AWS Account Id or Application Id List must be provided.'
        log.error(msg)
        errors.append(msg)

    if 'accountid' in body and 'appidlist' in body:
        msg = 'Only one parameter is allowed, please provide either AWS Account Id or Application Id List.'
        log.error(msg)
        errors.append(msg)

    if 'action' not in body:
        msg = 'ERROR: test and cutover action is required.'
        log.error(msg)
        errors.append(msg)
    else:
        if not is_valid_action(body['action'].strip()):
            msg = 'Incorrect test or cutover action.'
            log.error(msg)
            errors.append(msg)

    if 'accountid' in body and body['accountid'].strip() == '':
        msg = 'accountid cannot be empty string.'
        log.error(msg)
        errors.append(msg)
    elif 'appidlist' in body and len(body['appidlist']) == 0:
        msg = 'appidlist cannot be empty.'
        log.error(msg)
        errors.append(msg)

    if errors:
        return {'headers': {**default_http_headers},
                'statusCode': 400,
                'body': 'ERROR: ' + ','.join(errors)
                }

    return {'headers': {**default_http_headers},
            'statusCode': 200
            }


def get_status_response(status_code, body, headers):
    return {'headers': headers,
            'statusCode': status_code,
            'body': json.dumps(body)}


def get_server_list(body):
    account_id = ''
    app_ids = []
    server_ids = None
    status_response = {}
    if 'accountid' in body:
        account_id = str(body['accountid']).strip()
    elif 'appidlist' in body:
        app_ids = body['appidlist']

    if 'server_ids' in body and body['server_ids']:
        server_ids = body['server_ids']

    cmf_servers, errors = get_factory_servers(
        waveid=body['waveid'],
        accountid=account_id,
        appidlist=app_ids,
        server_ids=server_ids
    )
    if errors:
        log.error(errors)
        status_response = get_status_response(
            400, errors, {**default_http_headers})
        return cmf_servers, status_response

    log.debug(cmf_servers)

    return cmf_servers, status_response


def verify_servers(cmf_servers):
    status_response = {}
    verified_servers, verify_server_errors = \
        verify_target_account_servers(cmf_servers)
    if verify_server_errors:
        log.error(str(verified_servers))
        status_response = get_status_response(
            400, verify_server_errors, {**default_http_headers})
        return verified_servers, status_response
    log.debug("*** Verified Servers ***")
    log.debug(verified_servers)

    return verified_servers, status_response


def update_ec2_launch_template(verified_servers, body):
    status_response = {}
    update_ec2_template = lambda_mgn_template.update_launch_template(
        verified_servers, body['action'])
    if update_ec2_template is not None and 'ERROR' in update_ec2_template:
        log.error(str(update_ec2_template))
        status_response = get_status_response(
            400, update_ec2_template, {**default_http_headers})
        return status_response
    if update_ec2_template is not None and 'SUCCESS' in update_ec2_template:
        log.info(str(update_ec2_template))
        status_response = get_status_response(
            200, update_ec2_template, {**default_http_headers})
        return status_response

    return status_response


def manage_mgn_actions(verified_servers, body):
    status_response = {}
    if body['action'].strip() != 'Validate Launch Template':
        manage_mgn_servers = lambda_mgn_launch.manage_action(
            verified_servers, body['action'])
        if manage_mgn_servers is not None and 'ERROR' in manage_mgn_servers:
            log.error(str(manage_mgn_servers))
            status_response = get_status_response(
                400, manage_mgn_servers, {**default_http_headers})
            return status_response
        if manage_mgn_servers is not None and 'SUCCESS' in manage_mgn_servers:
            log.info(str(manage_mgn_servers))
            status_response = get_status_response(
                200, manage_mgn_servers, {**default_http_headers})
            return status_response

    return status_response


def lambda_handler(event, _):
    try:
        auth = MFAuth()
        auth_response = auth.get_user_resource_creation_policy(event, 'mgn')
        if auth_response['action'] != 'allow':
            status_response = get_status_response(
                401, auth_response, {**default_http_headers})
            return status_response

        body = json.loads(event['body'])

        # Check input parameters
        validation_result = validate_input_parameters(body)
        if validation_result['statusCode'] != 200:
            return validation_result

        # Get server list
        cmf_servers, status_response = get_server_list(body)
        if status_response != {}:
            return status_response

        # Verify servers
        verified_servers, status_response = verify_servers(cmf_servers)
        if status_response != {}:
            return status_response

        # Update EC2 Launch template
        status_response = update_ec2_launch_template(verified_servers, body)
        if status_response != {}:
            return status_response

        # Manage MGN Actions
        status_response = manage_mgn_actions(verified_servers, body)
        if status_response != {}:
            return status_response

    except Exception as e:
        log.error(str(e))
        status_response = get_status_response(
            400, str(e), {**default_http_headers})
        return status_response


def filter_items(items, key, item_ids=None):
    if item_ids:
        return [item for item in items if item[key] in item_ids]
    else:
        return items
