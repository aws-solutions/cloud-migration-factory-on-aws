#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import boto3
import os

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}


def lambda_handler(event, _):

    body = json.loads(event['body'])    
    userid = body['username']
    oldpassword = body['oldpassword']
    newpassword = body['newpassword']
    client = boto3.client('cognito-idp')
    try:
        response = client.initiate_auth(
            ClientId=os.environ['clientId'],
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': userid,
                'PASSWORD': oldpassword
            }
        )
    except Exception as e:
        if "NotAuthorizedException" in str(e) or "UserNotFoundException" in str(e):
            return {'headers': {**default_http_headers},
                    'statusCode': 400,
                    'body': 'Incorrect old username or password'
                  }
        
    challenge_name = response['ChallengeName']
    if challenge_name == "NEW_PASSWORD_REQUIRED":
        response = client.respond_to_auth_challenge(
            ClientId=os.environ['clientId'],
            ChallengeName='NEW_PASSWORD_REQUIRED',
            Session=response['Session'],
            ChallengeResponses={
                'NEW_PASSWORD': newpassword,
                'USERNAME' : userid
 
            }
        )

    return {
        'headers': {**default_http_headers},
        'statusCode': 200,
        'body': json.dumps(response)
    }
