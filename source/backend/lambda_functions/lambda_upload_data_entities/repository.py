#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import boto3
from datetime import datetime, timezone
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Dict, List, Optional, Any
from cmf_logger import logger

class UploadEntitiesRepository:
    """
    Repository class for managing upload entities metadata in DynamoDB.
    Handles all database operations for the upload entities functionality.
    """
    
    def __init__(self, table_name: str):
        """
        Initialize the repository with DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table for upload metadata
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.client = boto3.client("dynamodb", config=Config(
            retries={
                'mode': 'standard',
                'total_max_attempts': 3
            }
        ))

    def create_audit_info(self, auth_response):
        """Create audit information for new items."""
        audit = {}
        if 'user' in auth_response:
            audit['createdBy'] = auth_response['user']
            audit['createdTimestamp'] = datetime.now(timezone.utc).isoformat()
        return audit
        
    def create_upload_record(self, upload_metadata: Dict[str, Any], auth_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new upload record in DynamoDB.
        
        Args:
            upload_metadata: Dictionary containing upload metadata
            
        Returns:
            item: The item it upserted into the db
        """
        audit = self.create_audit_info(auth_response)
        try:
            # Add required keys for the record
            record = {
                **upload_metadata,
                '_history': audit
            }
            self.table.put_item(Item=record)
            logger.info(f'Successfully created upload record for ID: {upload_metadata.get("upload_id", "unknown")}')
            return record
        except Exception as e:
            logger.error(f'Failed to create upload record: {str(e)}')
            raise e
    
    def get_upload_record(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an upload record by ID
        
        Args:
            upload_id: The unique upload identifier
            
        Returns:
            Dict containing upload data if found, None otherwise
        """
        try:
            response = self.table.get_item(Key={'upload_id': upload_id})
            
            if 'Item' in response:
                logger.info(f'Successfully retrieved upload record for ID: {upload_id}')
                return response['Item']
            else:
                logger.warning(f'Upload record not found for ID: {upload_id}')
                return None
                
        except ClientError as e:
            logger.error(f'AWS error retrieving upload record for ID {upload_id}: {str(e)}')
            raise e
        except Exception as e:
            logger.error(f'Unexpected error retrieving upload record for ID {upload_id}: {str(e)}')
            raise e

    def list_uploads(self, limit: int = 50, 
                           last_evaluated_key: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        List uploads with pagination support.
        
        Args:
            limit: Maximum number of items to return (default: 50, max: 100)
            last_evaluated_key: Pagination token from previous request
            
        Returns:
            Dict containing uploads list, count, and pagination info
        """
        try:
            # Validate limit
            limit = min(max(1, limit), 100)
            
            # Build scan parameters
            scan_params = {
                'Limit': limit
            }
            
            # Add pagination token if provided
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            # Execute scan operation
            response = self.table.scan(**scan_params)
            
            items = response.get('Items', [])
            
            result = {
                'items': items,
                'count': len(items)
            }
            
            # Add pagination info if there are more items
            if 'LastEvaluatedKey' in response:
                result['last_evaluated_key'] = response['LastEvaluatedKey']
            
            logger.info(f'Successfully scanned {len(items)} uploads')
            return result
            
        except ClientError as e:
            logger.error(f'AWS error scanning uploads: {str(e)}')
            raise e
        except Exception as e:
            logger.error(f'Unexpected error scanning uploads: {str(e)}')
            raise e

    def list_uploads_by_user(self, user: str, limit: int = 50, 
                           last_evaluated_key: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        List uploads for a specific user with pagination support using UserIdIndex GSI.
        
        Args:
            user: User identifier to filter uploads
            limit: Maximum number of items to return (default: 50, max: 100)
            last_evaluated_key: Pagination token from previous request
            
        Returns:
            Dict containing uploads list, count, and pagination info
        """
        try:
            # Validate limit
            limit = min(max(1, limit), 100)
            
            # Build query parameters for UserIdIndex GSI
            query_params = {
                'IndexName': 'uploaded_by_upload_id-index',
                'KeyConditionExpression': 'uploaded_by = :user',
                'ExpressionAttributeValues': {':user': user},
                'Limit': limit,
                'ScanIndexForward': False  # Sort by sort key descending (most recent first)
            }
            
            # Add pagination token if provided
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            # Execute query on GSI
            response = self.table.query(**query_params)
            
            items = response.get('Items', [])
            
            result = {
                'items': items,
                'count': len(items)
            }
            
            # Add pagination info if there are more items
            if 'LastEvaluatedKey' in response:
                result['last_evaluated_key'] = response['LastEvaluatedKey']
            
            logger.info(f'Successfully queried {len(items)} uploads for user: {user} using uploaded_by_upload_id-index GSI')
            return result
            
        except ClientError as e:
            logger.error(f'AWS error querying uploads for user {user} using uploaded_by_upload_id-index GSI: {str(e)}')
            raise e
        except Exception as e:
            logger.error(f'Unexpected error querying uploads for user {user} using uploaded_by_upload_id-index GSI: {str(e)}')
            raise e


def create_repository() -> UploadEntitiesRepository:
    """
    Factory function to create a repository instance with environment configuration.
    
    Returns:
        UploadEntitiesRepository: Configured repository instance
    """
    table_name = os.environ.get("UPLOAD_ENTITIES_METADATA_TABLE_NAME")
    if not table_name:
        raise ValueError("UPLOAD_ENTITIES_METADATA_TABLE_NAME environment variable is required")
    
    return UploadEntitiesRepository(table_name)