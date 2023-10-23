#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
from policy import MFAuth
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, _):
    if 'methodArn' in event:
        logger.info('Authenticating API Gateway request' + event['methodArn'])
    else:
        logger.info('Authenticating non-API Gateway request')
    auth = MFAuth()
    auth_response = auth.getAdminResourcePolicy(event)
    logger.info(auth_response)
    return auth_response
