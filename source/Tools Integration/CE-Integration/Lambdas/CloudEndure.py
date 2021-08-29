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
import Machine
import requests
import json
import StatusCheck
import Cleanup
import os

HOST = 'https://console.cloudendure.com'
headers = {'Content-Type': 'application/json'}
session = {}
endpoint = '/api/latest/{}'

def login(userapitoken, endpoint):
    login_data = {'userApiToken': userapitoken}
    r = requests.post(HOST + endpoint.format('login'),
                  data=json.dumps(login_data), headers=headers)
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
                      data=json.dumps(login_data), headers=headers)
                      
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
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'userapitoken is required'}
        if 'projectname' not in body:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'projectname is required'}
        if 'waveid' not in body:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'waveid is required'}
        if 'launchtype' not in body:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'launchtype is required'}
    except Exception as e:
        print(e)
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 400, 'body': 'malformed json input'}
    print("")
    print("************************")
    print("* Login to CloudEndure *")
    print("************************")
    r = login(body['userapitoken'], endpoint)

    if r is not None and "ERROR" in r:
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 400, 'body': r}

    if 'relaunch' in body:
        relaunch = body['relaunch']
    
    if 'dryrun' in body:
        if body['dryrun'].lower() != "yes":
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': "ERROR: the only valid value for dryrun is 'Yes'"}
        else:
            dryrun = body['dryrun']
    
    if 'cleanup' in body:
       if body['cleanup'].lower() != "yes":
           return {'headers': {'Access-Control-Allow-Origin': '*'},
                   'statusCode': 400, 'body': "ERROR: the only valid value for cleanup is 'Yes'"}
       else:
            r = Cleanup.remove(session, headers, endpoint, HOST, body['projectname'], body['waveid'])
            if r is not None and "ERROR" in r:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': r}
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 200, 'body': r}
    if 'cleanup' not in body:
        if body['launchtype'] == "test" or body['launchtype'] =="cutover":
           if 'statuscheck' not in body:
               r = Machine.execute(body['launchtype'], session, headers, endpoint, HOST, body['projectname'], dryrun, body['waveid'], relaunch)
               if r is not None and "ERROR" in r:
                  return {'headers': {'Access-Control-Allow-Origin': '*'},
                          'statusCode': 400, 'body': r}
               return {'headers': {'Access-Control-Allow-Origin': '*'},
                       'statusCode': 200, 'body': r}
           else:
               if body['statuscheck'].lower() =="yes":
                   r = StatusCheck.check(body['launchtype'], session, headers, endpoint, HOST, body['projectname'], body['waveid'])
                   if r is not None and "ERROR" in r:
                      return {'headers': {'Access-Control-Allow-Origin': '*'},
                              'statusCode': 400, 'body': r}
                   return {'headers': {'Access-Control-Allow-Origin': '*'},
                           'statusCode': 200, 'body': r}
               else:
                   return {'headers': {'Access-Control-Allow-Origin': '*'},
                           'statusCode': 400, 'body': "ERROR: the only valid value for statuscheck is 'Yes'...."}
        else:
           return {'headers': {'Access-Control-Allow-Origin': '*'},
                   'statusCode': 400, 'body': 'ERROR: Please use the valid launch type: test|cutover....'}