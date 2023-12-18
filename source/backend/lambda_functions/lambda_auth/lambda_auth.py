#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from policy import MFAuth
from cmf_logger import logger


def lambda_handler(event, _):
    if 'methodArn' in event:
        logger.info('Authenticating API Gateway request' + event['methodArn'])
    else:
        logger.info('Authenticating non-API Gateway request')
    auth = MFAuth()
    auth_response = auth.get_admin_resource_policy(event)
    logger.info(auth_response)
    return auth_response
