#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os

import cmf_boto
from cmf_utils import cors, default_http_headers


def lambda_handler(event, _):

    body = json.loads(event['body'])    
    userid = body['username']
    oldpassword = body['oldpassword']
    newpassword = body['newpassword']
    client = cmf_boto.client('cognito-idp')
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
