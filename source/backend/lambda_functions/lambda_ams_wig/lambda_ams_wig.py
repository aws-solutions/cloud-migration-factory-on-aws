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
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT≤ OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################

from __future__ import print_function
import boto3
import botocore
import json
import sys
import os
import requests
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

HOST = 'https://console.cloudendure.com'
headers = {'Content-Type': 'application/json'}
session = {}
endpoint = '/api/latest/{}'

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}
application = os.environ['application']
environment = os.environ['environment']
servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)
servers_table = boto3.resource('dynamodb').Table(servers_table_name)
apps_table = boto3.resource('dynamodb').Table(apps_table_name)


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        if 'userapitoken' not in body:
            logger.error('userapitoken is required')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'userapitoken is required'}
        if 'projectname' not in body:
            logger.error('rojectname is required')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'projectname is required'}
        if 'waveid' not in body:
            logger.error('waveid is required')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'waveid is required'}
        if 'key_id' not in body:
            logger.error('key_id is required')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'AWS Credentials is required'}
        if 'secret' not in body:
            logger.error('secret is required')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'AWS Credentials is required'}
    except Exception as e:
        logger.error('malformed json input')
        logger.error(e)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    logger.info('Login to CloudEndure')
    r = CElogin(body['userapitoken'], endpoint)

    if r is not None and "ERROR" in r:
        logger.error('CloudEndure Login Failed')
        logger.error(r)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': r}

    ServerList = GetServerList(body['projectname'], body['waveid'], body['key_id'], body['secret'], session, headers,
                               endpoint, HOST)
    logger.debug(ServerList)
    logger.info('Creating a workload ingest RFC....')
    success_servers = ""
    failed_servers = ""
    for server in ServerList:
        if 'InstanceId' in server:
            if 'ams_vpc_id' not in server:
                msg = 'ams_vpc_id attribute for ' + server['server_name'] + ' does not exist'
                logger.error(msg)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': msg}
            if 'ams_subnet_id' not in server:
                msg = 'ams_subnet_id attribute for ' + server['server_name'] + ' does not exist'
                logger.error(msg)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': msg}
            if 'ams_securitygroup_ids' not in server:
                msg = 'ams_securitygroup_ids attribute for ' + server['server_name'] + ' does not exist'
                logger.error(msg)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': msg}
            msg = "WIG for " + server['server_name'] + '-' + server['InstanceId']
            para = {
                "InstanceId": server['InstanceId'],
                "TargetVpcId": server['ams_vpc_id'],
                "TargetSubnetId": server['ams_subnet_id'],
                "Name": msg,
                "Description": msg,
                "TargetInstanceType": server['instanceType'],
                "TargetSecurityGroupIds": server['ams_securitygroup_ids']
            }
            try:
                logger.info('Submitting the workload ingest RFC....')
                ams_client = boto3.client('amscm', aws_access_key_id=body['key_id'],
                                          aws_secret_access_key=body['secret'])
                rfc = ams_client.create_rfc(ChangeTypeId="ct-257p9zjk14ija", ChangeTypeVersion="1.0",
                                            Title=msg, ExecutionParameters=json.dumps(para))
                result = ams_client.submit_rfc(RfcId=rfc['RfcId'])
                if result['ResponseMetadata']['HTTPStatusCode'] == 200:
                    success_servers = success_servers + server["server_name"] + ","
                else:
                    failed_servers = failed_servers + server["server_name"] + ","
            except Exception as e:
                logger.error(e)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': str(e)}
        else:
            msg = 'Target Instance for Server ' + server['server_name'] + ' does not exist'
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msg}
    message1 = ""
    message2 = ""
    if len(failed_servers) > 0:
        failed_servers = failed_servers[:-1]
        message1 = "ERROR: " + " AMS Workload Ingest RFC submission failed for server: " + failed_servers
        if len(success_servers) > 0:
            success_servers = success_servers[:-1]
            message2 = "The AMS Workload Ingest RFC submission was successful for server: " + success_servers
            msg = message1 + ' | ' + message2
            logger.error(msg)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msg}
        else:
            logger.error(message1)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': message1}
    elif len(success_servers) > 0:
        success_servers = success_servers[:-1]
        message2 = "The AMS Workload Ingest RFC submission was successful for server: " + success_servers
        logger.info(message2)
        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': message2}


def CElogin(userapitoken, endpoint):
    login_data = {'userApiToken': userapitoken}
    r = requests.post(HOST + endpoint.format('login'),
                      data=json.dumps(login_data), headers=headers)
    if r.status_code == 200:
        logger.info("CloudEndure : You have successfully logged in")
    if r.status_code != 200 and r.status_code != 307:
        if r.status_code == 401 or r.status_code == 403:
            logger.error('The CloudEndure login credentials provided cannot be authenticated....')
            return 'ERROR: The CloudEndure login credentials provided cannot be authenticated....'
        elif r.status_code == 402:
            logger.error('There is no active license configured for this CloudEndure account....')
            return 'ERROR: There is no active license configured for this CloudEndure account....'
        elif r.status_code == 429:
            logger.error('CloudEndure Authentication failure limit has been reached. The service will become '
                         'available for additional requests after a timeout....')
            return 'ERROR: CloudEndure Authentication failure limit has been reached. The service will become ' \
                   'available for additional requests after a timeout.... '

    # check if need to use a different API entry point
    if r.history:
        endpoint = '/' + '/'.join(r.url.split('/')[3:-1]) + '/{}'
        r = requests.post(HOST + endpoint.format('login'),
                          data=json.dumps(login_data), headers=headers)

    session['session'] = r.cookies['session']
    try:
        headers['X-XSRF-TOKEN'] = r.cookies['XSRF-TOKEN']
    except:
        pass


def GetServerList(projectname, waveid, access_key_id, secret_access_key, session, headers, endpoint, HOST):
    r = requests.get(HOST + endpoint.format('projects'), headers=headers, cookies=session)
    if r.status_code != 200:
        logger.error('Failed to fetch the project.')
        return "ERROR: Failed to fetch the project...."
    try:
        # Get Project ID
        projects = json.loads(r.text)["items"]
        project_exist = False
        for project in projects:
            if project["name"] == projectname:
                project_id = project["id"]
                project_exist = True
        if project_exist == False:
            logger.error('Project Name does not exist in CloudEndure.')
            return "ERROR: Project Name does not exist in CloudEndure...."

        # Get Machine List from CloudEndure
        m = requests.get(HOST + endpoint.format('projects/{}/machines').format(project_id), headers=headers,
                         cookies=session)
        if "sourceProperties" not in m.text:
            logger.error('Failed to fetch the machines.')
            return "ERROR: Failed to fetch the machines...."
        InstanceIdList = {}
        logger.info('Getting Target instance Ids')
        for machine in json.loads(m.text)["items"]:
            if 'replica' in machine:
                if machine['replica'] != '':
                    logger.debug(machine['replica'])
                    target_replica = requests.get(
                        HOST + endpoint.format('projects/{}/replicas').format(project_id) + '/' + machine['replica'],
                        headers=headers, cookies=session)
                    logger.debug(json.loads(target_replica.text))
                    InstanceIdList[machine['sourceProperties']['name'].lower()] = json.loads(target_replica.text)[
                        'machineCloudId']

        # Get all Apps and servers from migration factory

        getserver = scan_dynamodb_table('server')
        servers = sorted(getserver, key=lambda i: i['server_name'])

        getapp = scan_dynamodb_table('app')
        apps = sorted(getapp, key=lambda i: i['app_name'])

        # Get App list
        applist = []
        for app in apps:
            if 'wave_id' in app and 'cloudendure_projectname' in app:
                if str(app['wave_id']) == str(waveid) and str(app['cloudendure_projectname']) == str(projectname):
                    applist.append(app['app_id'])
        # Get Server List
        serverlist = []
        for app in applist:
            for server in servers:
                if "app_id" in server:
                    if app == server['app_id']:
                        newserver = server
                        if server['server_name'].lower() in InstanceIdList:
                            newserver['InstanceId'] = InstanceIdList[server['server_name'].lower()]
                        serverlist.append(newserver)
        if len(serverlist) == 0:
            logger.error('Serverlist for wave " + waveid + " in Migration Factory is empty.')
            return "ERROR: Serverlist for wave " + waveid + " in Migration Factory is empty...."
        logger.debug(serverlist)
        return serverlist
    except:
        logger.error('Getting server list failed.')
        return "ERROR: Getting server list failed...."


# Pagination for DDB table scan
def scan_dynamodb_table(datatype):
    if datatype == 'server':
        response = servers_table.scan(ConsistentRead=True)
    elif datatype == 'app':
        response = apps_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        logger.debug('Last Evaluate key is  ' + str(response['LastEvaluatedKey']))
        if datatype == 'server':
            response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        elif datatype == 'app':
            response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response['Items'])
    return (scan_data)
