#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from __future__ import print_function
import sys
import Machine
import requests
import json
import StatusCheck
import Cleanup
import os
from policy import MFAuth

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

HOST = 'https://console.cloudendure.com'
headers = {'Content-Type': 'application/json'}
session = {}
endpoint = '/api/latest/{}'

REQUESTS_DEFAULT_TIMEOUT = 60


def login(userapitoken, endpoint):
    login_data = {'userApiToken': userapitoken}
    r = requests.post(HOST + endpoint.format('login'),
                      data=json.dumps(login_data),
                      headers=headers,
                      timeout=REQUESTS_DEFAULT_TIMEOUT)
    if r.status_code == 200:
        print("CloudEndure : You have successfully logged in")
        print("")
    if r.status_code != 200 and r.status_code != 307:
        if r.status_code == 401 or r.status_code == 403:
            return 'ERROR: The CloudEndure login credentials provided cannot be authenticated....'
        elif r.status_code == 402:
            return 'ERROR: There is no active license configured for this CloudEndure account....'
        elif r.status_code == 429:
            return 'ERROR: CloudEndure Authentication failure limit has been reached. The service will become available for additional requests after a timeout....'

    # check if need to use a different API entry point
    if r.history:
        endpoint = '/' + '/'.join(r.url.split('/')[3:-1]) + '/{}'
        r = requests.post(HOST + endpoint.format('login'),
                          data=json.dumps(login_data),
                          headers=headers,
                          timeout=REQUESTS_DEFAULT_TIMEOUT)
                      
    session['session'] = r.cookies['session']
    try:
       headers['X-XSRF-TOKEN'] = r.cookies['XSRF-TOKEN']
    except:
       pass

def lambda_handler(event, context):
    dryrun = "No"
    relaunch = False
    try:
        body = json.loads(event['body'])
        if 'userapitoken' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'userapitoken is required'}
        if 'projectname' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'projectname is required'}
        if 'waveid' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'waveid is required'}
        if 'launchtype' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'launchtype is required'}
    except Exception as e:
        print(e)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    # Verify user has access to run CE migrations.
    auth = MFAuth()
    authResponse = auth.getUserResourceCreationPolicy(event, 'ce')
    if authResponse['action'] != 'allow':
      return {'headers': {**default_http_headers},
              'statusCode': 401,
              'body': json.dumps(authResponse)}

    print("")
    print("************************")
    print("* Login to CloudEndure *")
    print("************************")
    r = login(body['userapitoken'], endpoint)

    if r is not None and "ERROR" in r:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': r}

    if 'relaunch' in body:
        relaunch = body['relaunch']
    
    if 'dryrun' in body:
        if body['dryrun'].lower() != "yes":
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': "ERROR: the only valid value for dryrun is 'Yes'"}
        else:
            dryrun = body['dryrun']
    
    if 'cleanup' in body:
       if body['cleanup'].lower() != "yes":
           return {'headers': {**default_http_headers},
                   'statusCode': 400, 'body': "ERROR: the only valid value for cleanup is 'Yes'"}
       else:
            r = Cleanup.remove(session, headers, endpoint, HOST, body['projectname'], body['waveid'])
            if r is not None and "ERROR" in r:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': r}
            return {'headers': {**default_http_headers},
                    'statusCode': 200, 'body': r}
    if 'cleanup' not in body:
        if body['launchtype'] == "test" or body['launchtype'] =="cutover":
           if 'statuscheck' not in body:
               r = Machine.execute(body['launchtype'], session, headers, endpoint, HOST, body['projectname'], dryrun, body['waveid'], relaunch)
               if r is not None and "ERROR" in r:
                  return {'headers': {**default_http_headers},
                          'statusCode': 400, 'body': r}
               return {'headers': {**default_http_headers},
                       'statusCode': 200, 'body': r}
           else:
               if body['statuscheck'].lower() =="yes":
                   r = StatusCheck.check(body['launchtype'], session, headers, endpoint, HOST, body['projectname'], body['waveid'])
                   if r is not None and "ERROR" in r:
                      return {'headers': {**default_http_headers},
                              'statusCode': 400, 'body': r}
                   return {'headers': {**default_http_headers},
                           'statusCode': 200, 'body': r}
               else:
                   return {'headers': {**default_http_headers},
                           'statusCode': 400, 'body': "ERROR: the only valid value for statuscheck is 'Yes'...."}
        else:
           return {'headers': {**default_http_headers},
                   'statusCode': 400, 'body': 'ERROR: Please use the valid launch type: test|cutover....'}