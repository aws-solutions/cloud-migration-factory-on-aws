import json
import boto3
import os
import time
import urllib
import datetime
from jose import jwk, jwt
from jose.utils import base64url_decode
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
dynamodb = boto3.resource("dynamodb")
connectionIds_table_name = '{}-{}-ssm-connectionIds'.format(application, environment)


def _get_response(status_code, body):
    if not isinstance(body, str):
        body = json.dumps(body)
    return {"statusCode": status_code, "body": body}


def verify_token(token):
    # get the kid from the headers prior to verification
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    # search for the kid in the downloaded public keys
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            key_index = i
            break
    if key_index == -1:
        logger.error('Public key not found in jwks.json')
        return False
    # construct the public key
    public_key = jwk.construct(keys[key_index])
    # get the last two sections of the token,
    # message and signature (encoded in base64)
    message, encoded_signature = str(token).rsplit('.', 1)
    # decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        logger.error('Signature verification failed')
        return False
    logger.debug('Signature successfully verified')
    # since we passed the verification, we can now safely
    # use the unverified claims
    claims = jwt.get_unverified_claims(token)
    # additionally we can verify the token expiration
    if time.time() > claims['exp']:
        logger.error('Token has expired')
        return False
    # and the Audience  (use claims['client_id'] if verifying an access token)
    if claims['aud'] != app_client_id:
        logger.error('Token was not issued for this audience')
        return False
    # now we can use the claims
    logger.debug('Claims: %s', claims)
    logger.info('Token verified.')
    return claims


def lambda_handler(event, context):
    logger.debug(event)
    if event["requestContext"]["eventType"] == "CONNECT":
        if "connectionId" in event["requestContext"]:
            logger.info('CONNECT: %s', event["requestContext"].get("connectionId"))
        return _get_response(200, "Connection successful, authentication required.")

    elif event["requestContext"]["eventType"] == "DISCONNECT":
        if "connectionId" in event["requestContext"]:
            logger.info('DISCONNECT: %s', event["requestContext"].get("connectionId"))
        connectionId = event["requestContext"].get("connectionId")
        table = dynamodb.Table(connectionIds_table_name)
        table.delete_item(Key={"connectionId": connectionId})
        return _get_response(200, "Disconnect successful")

    elif event["requestContext"]["eventType"] == "MESSAGE":
        if "connectionId" in event["requestContext"]:
            logger.info('MESSAGE: %s', event["requestContext"].get("connectionId"))
        try:
            message = json.loads(event['body'])
            logger.debug('MESSAGE: %s' + ' - ' + event['body'], event["requestContext"].get("connectionId"))
            if 'type' not in message and ('message' not in message or 'token' not in message):
                error_message = "Invalid message format"
                logger.error('MESSAGE: %s' + ' - ' + error_message, event["requestContext"].get("connectionId"))
                return _get_response(400, error_message)
        except Exception as e:
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
                connectionId = event["requestContext"].get("connectionId")
                table = dynamodb.Table(connectionIds_table_name)
                table.put_item(Item={"connectionId": connectionId, "date/time": datetime.datetime.now().strftime("%c"),
                                     "email": claims['email'], "topics": []})
                logger.info('MESSAGE: %s' + ' - ' + info_message, event["requestContext"].get("connectionId"))
                return _get_response(200, info_message)

        error_message = "Unsupported message type, full message:"
        logger.error('MESSAGE: %s' + ' - ' + error_message + event['body'], event["requestContext"].get("connectionId"))
        return _get_response(400, error_message)
    else:
        # Unsupported eventType
        connectionId = event["requestContext"].get("connectionId")
        return _get_response(400, "Unsupported event type.")
