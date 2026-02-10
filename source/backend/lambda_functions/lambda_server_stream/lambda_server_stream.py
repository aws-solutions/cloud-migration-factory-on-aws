#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, _):
    logger.info("MGH and ADS integration has been deprecated and removed from CMF")
    logger.info("Server tracking functionality is no longer available")
    
    # Log the event for debugging purposes but take no action
    for record in event.get('Records', []):
        dynamodb_record = record.get('dynamodb', {})
        
        if 'NewImage' in dynamodb_record:
            logger.info("DynamoDB event received but MGH tracking is disabled")
            new_image = dynamodb_record['NewImage']
            if 'migration_status' in new_image:
                server_name = new_image.get('server_name', {}).get('S', 'unknown')
                migration_status = new_image.get('migration_status', {}).get('S', 'unknown')
                logger.info(f"Server {server_name} status updated to {migration_status} (not tracked in MGH)")
