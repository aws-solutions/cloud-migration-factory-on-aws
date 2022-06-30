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

import json
import boto3
import os
from json import JSONEncoder
import datetime

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

# subclass JSONEncoder
class DateTimeEncoder(JSONEncoder):
  # Override the default method
  def default(self, obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
      return obj.isoformat()


def get_user_groups(client, username):
  response = client.admin_list_groups_for_user(
    Username=username,
    UserPoolId=os.environ['userpool_id'],
  )

  groups = []
  for group in response['Groups']:
    groups.append({
      'group_name': group['GroupName']

    })

  return groups


def lambda_handler(event, context):
  client = boto3.client('cognito-idp')
  response = client.list_users(
    UserPoolId=os.environ['userpool_id']
  )

  # Create MF formatted response with required data.
  users = []
  for user in response['Users']:
    newuser = {}
    newuser['userRef'] = user['Username']

    # Build MF history object for user.
    history = {
      'createdTimestamp': user['UserCreateDate'],
      'lastModifiedTimestamp': user['UserLastModifiedDate']
    }

    # Add standard Cognito data..
    newuser['_history'] = history
    newuser['enabled'] = user['Enabled']
    newuser['status'] = user['UserStatus']

    newuser['groups'] = get_user_groups(client, user['Username'])

    for attrib in user['Attributes']:
      if attrib['Name'] == 'email':
        newuser['email'] = attrib['Value']

    if 'MFAOptions' in user and len(user['MFAOptions']) > 0:
      newuser['mfaEnabled'] = True
    else:
      newuser['mfaEnabled'] = False

    users.append(newuser)
  return {'headers': {**default_http_headers},
          'statusCode': 200,
          'body': json.dumps(users, cls=DateTimeEncoder)
          }