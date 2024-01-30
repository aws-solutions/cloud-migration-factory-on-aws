#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import time
import urllib
import datetime
import jwt
from jwt import PyJWKClient

import cmf_boto
from cmf_logger import logger

region = os.environ['region']
userpool_id = os.environ['userpool_id']
app_client_id = os.environ['app_client_id']
keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(region, userpool_id)
# instead of re-downloading the public keys every time
# we download them only on cold start
# https://aws.amazon.com/blogs/compute/container-reuse-in-lambda/
response = urllib.request.urlopen(keys_url)  # nosec B310
keys = json.loads(response.read())['keys']

application = os.environ["application"]
environment = os.environ["environment"]
dynamodb = cmf_boto.resource("dynamodb")
connectionIds_table_name = '{}-{}-ssm-connectionIds'.format(application, environment)


def _get_response(status_code, body):
    if not isinstance(body, str):
        body = json.dumps(body)
    return {"statusCode": status_code, "body": body}


def verify_token(token):
    verify_url = f"https://cognito-idp.{region}.amazonaws.com/{userpool_id}"

    optional_custom_headers = {"User-agent": "custom-user-agent"}
    jwks_client = PyJWKClient(verify_url + '/.well-known/jwks.json', headers=optional_custom_headers)
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except jwt.exceptions.PyJWKClientError as get_keys_error:
        logger.error(get_keys_error)
        logger.error('Invalid Token here')
        return False

    kargs = {"issuer": verify_url, "algorithms": ['RS256'], "audience": app_client_id}
    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            **kargs
        )
    except jwt.exceptions.ExpiredSignatureError as _:
        logger.error('Token has expired')
        return False
    except jwt.exceptions.InvalidAudienceError as _:
        logger.error('Token was not issued for this audience')
        return False
    except jwt.exceptions.InvalidIssuerError as _:
        logger.error('Issuer verification failed')
        return False
    except jwt.exceptions.InvalidSignatureError as _:
        logger.error('Signature verification failed')
        return False

    # now we can use the claims
    logger.debug('Claims: %s', claims)
    logger.info('Token verified.')
    return claims


def process_connect(event):
    if "connectionId" in event["requestContext"]:
        logger.info('CONNECT: %s', event["requestContext"].get("connectionId"))
    return _get_response(200, "Connection successful, authentication required.")


def process_disconnect(event):
    if "connectionId" in event["requestContext"]:
        logger.info('DISCONNECT: %s', event["requestContext"].get("connectionId"))
    connection_id = event["requestContext"].get("connectionId")
    table = dynamodb.Table(connectionIds_table_name)
    table.delete_item(Key={"connectionId": connection_id})
    return _get_response(200, "Disconnect successful")


def process_message(event):
    if "connectionId" in event["requestContext"]:
        logger.info('MESSAGE: %s', event["requestContext"].get("connectionId"))
    try:
        message = json.loads(event['body'])
        logger.debug('MESSAGE: %s' + ' - ' + event['body'], event["requestContext"].get("connectionId"))
        if 'type' not in message and ('message' not in message or 'token' not in message):
            error_message = "Invalid message format"
            logger.error('MESSAGE: %s' + ' - ' + error_message, event["requestContext"].get("connectionId"))
            return _get_response(400, error_message)
    except Exception as e:  # //NOSONAR
        error_message = "Error converting message to JSON"
        logger.error('MESSAGE: %s' + ' - ' + error_message, event["requestContext"].get("connectionId"))
        return _get_response(400, error_message)
    if message['type'] == 'auth':
        claims = verify_token(message['token'])
        if claims is False:
            error_message = "Invalid token"
            logger.error('MESSAGE: %s' + ' - ' + error_message, event["requestContext"].get("connectionId"))
            return _get_response(400, error_message)
        else:
            info_message = "Authentication successful"
            connection_id = event["requestContext"].get("connectionId")
            table = dynamodb.Table(connectionIds_table_name)
            table.put_item(Item={"connectionId": connection_id, "date/time": datetime.datetime.now().strftime("%c"),
                                 "email": claims['email'], "topics": []})
            logger.info('MESSAGE: %s' + ' - ' + info_message, event["requestContext"].get("connectionId"))
            return _get_response(200, info_message)

    error_message = "Unsupported message type, full message:"
    logger.error('MESSAGE: %s' + ' - ' + error_message + event['body'], event["requestContext"].get("connectionId"))
    return _get_response(400, error_message)


def process_unexpected():
    return _get_response(400, "Unsupported event type.")


def lambda_handler(event, _):
    logger.debug(event)
    if event["requestContext"]["eventType"] == "CONNECT":
        return process_connect(event)
    elif event["requestContext"]["eventType"] == "DISCONNECT":
        return process_disconnect(event)
    elif event["requestContext"]["eventType"] == "MESSAGE":
        return process_message(event)
    else:
        return process_unexpected()
