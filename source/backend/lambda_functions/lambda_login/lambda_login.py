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
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

def lambda_handler(event, context):
    response = {}
    try:
        body = json.loads(event['body'])
        client = boto3.client('cognito-idp')

        if 'mfacode' in body:
            # This is a response to MFA request on previous login attempt.
            userid = body['username']
            mfacode = body['mfacode']
            session = body['session']
            response = client.respond_to_auth_challenge(
                ClientId=os.environ['clientId'],
                ChallengeName='SMS_MFA',
                Session=session,
                ChallengeResponses={
                    'SMS_MFA_CODE': mfacode,
                    'USERNAME': userid
                }
            )
        else:
            userid = body['username']
            password = body['password']
            response = client.initiate_auth(
                ClientId=os.environ['clientId'],
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': userid,
                    'PASSWORD': password
                }
            )
    except Exception as e:
        if "NotAuthorizedException" in str(e) or "UserNotFoundException" in str(e):
            logger.error('Incorrect username or password: %s', userid)
            return {'headers': {**default_http_headers},
                    'statusCode': 400,
                    'body': 'Incorrect username or password'
                    }
        else:
            logger.error(e)

    if 'AuthenticationResult' in response:
        logger.info('User authenticated: %s', userid)
        return {'headers': {**default_http_headers},
                'statusCode': 200,
                'body': json.dumps(response['AuthenticationResult']['IdToken'])
                }
    elif 'ChallengeName' in response:
        logger.info('User challenge requested: %s', userid)
        return {'headers': {**default_http_headers},
                'statusCode': 200,
                'body': json.dumps(response)
                }
