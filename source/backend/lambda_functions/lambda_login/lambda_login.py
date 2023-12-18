#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os

import cmf_boto
from cmf_logger import logger
from cmf_utils import cors, default_http_headers


def lambda_handler(event, _):
    response = {}
    try:
        body = json.loads(event['body'])
        client = cmf_boto.client('cognito-idp')

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
