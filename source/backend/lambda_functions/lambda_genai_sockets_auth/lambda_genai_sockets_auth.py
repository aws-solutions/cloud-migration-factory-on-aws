#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import json
import time
import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode
from datetime import datetime, timedelta

from cmf_logger import logger, log_event_received

# Environment variables
USER_POOL_ID = os.environ['user_pool_id']
APP_CLIENT_ID = os.environ['app_client_id']
AWS_REGION = os.environ['aws_region']

# Globals
verify_url = f'https://cognito-idp.{AWS_REGION}.amazonaws.com/{USER_POOL_ID}'
keys_url = f'{verify_url}/.well-known/jwks.json'

# Key cache with expiration time (24 hours by default)
key_cache = {
    'keys': {},
    'expiration': datetime.now(),
    'last_refresh': None
}

def get_public_keys():
    """
    Fetch and cache the public keys from Cognito jwks_uri endpoint.
    Refreshes the cache if it's expired or if a key is not found.
    """
    now = datetime.now()
    
    # If cache is expired or empty, refresh it
    if now >= key_cache['expiration'] or not key_cache['keys']:
        logger.info("Refreshing public keys cache")
        try:
            with urllib.request.urlopen(keys_url) as f: # nosec B310
                response = f.read()
            
            keys_data = json.loads(response.decode('utf-8'))['keys']
            
            # Update the cache
            key_cache['keys'] = {key['kid']: key for key in keys_data}
            key_cache['last_refresh'] = now
            key_cache['expiration'] = now + timedelta(hours=24)
            
            logger.info(f"Public keys cache refreshed with {len(key_cache['keys'])} keys")
        except Exception as e:
            logger.warning(f"Error refreshing public keys: {str(e)}")
            # If we have existing keys, keep using them
            if not key_cache['keys']:
                raise
    
    return key_cache['keys']

def lambda_handler(event, _):
    log_event_received(event)
    
    # Get the token from Sec-WebSocket-Protocol header (see https://stackoverflow.com/questions/4361173/http-headers-in-websockets-client-api)
    # It assumes it is the only protocol provided
    protocol_header = event.get('headers', {}).get('Sec-WebSocket-Protocol', '')
    token = protocol_header.replace('Bearer ', '') if protocol_header.startswith('Bearer ') else protocol_header

    if not token:
        logger.warning("No token provided")
        return generate_policy('user', 'Deny', event['methodArn'])
    
    # Verify the token
    claims = verify_token(token)
    if not claims:
        logger.warning("Invalid token")
        return generate_policy('user', 'Deny', event['methodArn'])
    
    # Check for admin scope
    if 'cognito:groups' not in claims or 'admin' not in claims['cognito:groups']:
        logger.warning("User does not have admin scope")
        return generate_policy(claims['sub'], 'Deny', event['methodArn'])
    
    # Generate policy
    policy = generate_policy(
        claims['sub'], 
        'Allow', 
        event['methodArn'],
        context={
            'user_id': claims['sub'],
            'email': claims.get('email', ''),
            'groups': " ".join(claims.get('cognito:groups', []))
        }
    )

    logger.debug(f'Policy: {policy}')
    return policy

# Using https://github.com/awslabs/aws-support-tools/blob/master/Cognito/decode-verify-jwt/decode-verify-jwt.py
# PyJWT was running into issues regarding cryptography despite being specified in requirements.txt or in layers
def verify_token(token):
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']

    # Get cached keys
    keys_dict = get_public_keys()
    
    # Check if the kid exists in our cache
    if kid not in keys_dict:
        logger.info(f"Key ID {kid} not found in cache, refreshing keys")
        # Force refresh the keys
        key_cache['expiration'] = datetime.now()
        keys_dict = get_public_keys()
        
        # Check again after refresh
        if kid not in keys_dict:
            logger.warning(f"Public key with kid {kid} not found even after refresh")
            return False
    
    # Construct the public key
    public_key = jwk.construct(keys_dict[kid])

    # Get the last two sections of the token,
    # message and signature (encoded in base64)
    message, encoded_signature = str(token).rsplit('.', 1)

    # Decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

    # Verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        logger.warning('Signature verification failed')
        return False
    logger.info('Signature successfully verified')

    # Since we passed the verification, we can now safely
    # use the unverified claims
    claims = jwt.get_unverified_claims(token)
    
    # Verify the token expiration
    if time.time() > claims['exp']:
        logger.warning('Token is expired')
        return False
        
    if claims['aud'] != APP_CLIENT_ID:
        logger.warning('Token was not issued for this audience')
        return False
    
    # Now we can use the claims
    logger.debug(claims)
    return claims

def generate_policy(principal_id, effect, resource, context=None):
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    if context:
        policy['context'] = context
    
    return policy
