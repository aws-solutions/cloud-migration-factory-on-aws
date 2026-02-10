"""
Lambda Client Module

This module handles direct Lambda function invocations for S3 import operations,
including request creation, response processing, and error handling.

Author: AWS Migration Factory Team
"""

import json
import os
import boto3
from decimal import Decimal
from typing import Dict, List, Any

from cmf_logger import logger
from s3_import_exceptions import APIError, ValidationError

EntityData = List[Dict[str, Any]]
AuthInfo = Dict[str, Any]

def decimal_serializer(obj):
    """JSON serializer for Decimal objects from DynamoDB"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name=os.environ['region'])
application = os.environ.get('application', 'migration-factory')
environment = os.environ.get('environment', 'test')

def invoke_lambda_function(method: str, entity_name: str, data: EntityData, auth_info: AuthInfo) -> Dict[str, Any]:
    """
    Invoke Lambda function directly for S3 import operations.
    
    Creates and sends a Lambda invocation request that mimics API Gateway events.
    Validates input data and response for errors.
    
    Args:
        method: HTTP method ('POST' for creation, 'PUT' for updates)
        entity_name: Name of the entity type (e.g., 'app', 'server')
        data: List of entity objects to process
        auth_info: Authentication info from original upload
        
    Returns:
        dict: Response dictionary with success status and data
    """
    validate_lambda_request_inputs(method, entity_name, data, auth_info)
    
    function_name = get_function_name(method)
    payload = create_lambda_payload(method, entity_name, data, auth_info)
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload, default=decimal_serializer)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        # Check for Lambda function errors
        if response.get('FunctionError'):
            error_msg = f"Lambda function error: {response_payload}"
            logger.error(f"Lambda invocation failed for {method} {entity_name}: {error_msg}")
            raise APIError(error_msg, entity_type=entity_name)
        
        # Validate Lambda response and extract body
        response_data = validate_lambda_response(response_payload, method, entity_name)
        
        return create_lambda_response(entity_name, data, response_payload, response_data)
            
    except Exception as e:
        if isinstance(e, APIError):
            raise
        error_msg = f"Failed to invoke Lambda function {function_name}: {str(e)}"
        logger.error(error_msg)
        raise APIError(error_msg, entity_type=entity_name) from e

def validate_lambda_request_inputs(method: str, entity_name: str, data: EntityData, auth_info: AuthInfo) -> None:
    """Validate Lambda request inputs before making the request."""
    if not method or method not in ['POST', 'PUT']:
        raise ValidationError(f"Invalid HTTP method: {method}")
    
    if not entity_name or not entity_name.replace('_', '').replace('-', '').isalnum():
        raise ValidationError(f"Invalid entity name: {entity_name}")
    
    if not data or not isinstance(data, list):
        raise ValidationError(f"Invalid data provided for {method} {entity_name}: data must be a non-empty list")
    
    if not isinstance(auth_info, dict):
        logger.error(f"auth_info is not a dict for {method} {entity_name}, this may cause authentication issues")

def get_function_name(method: str) -> str:
    """Get Lambda function name based on HTTP method."""
    if method == 'POST':
        return f"{application}-{environment}-items"
    elif method == 'PUT':
        return f"{application}-{environment}-item"
    else:
        raise ValidationError(f"Unsupported HTTP method: {method}")

def create_lambda_payload(method: str, entity_name: str, data: EntityData, auth_info: AuthInfo) -> Dict[str, Any]:
    """Create Lambda payload that mimics API Gateway event structure."""
    return {
        'httpMethod': method,
        'pathParameters': {'schema': entity_name},
        'body': json.dumps({
            'data': data,
            'auth_info': auth_info
        }, default=decimal_serializer),
        'requestContext': {
            'identity': {
                'userArn': 'arn:aws:iam::account:user/lambda-import'
            }
        }
    }

def validate_lambda_response(response_payload: Dict[str, Any], method: str, entity_name: str) -> str:
    """Validate Lambda response status and extract body data."""
    status_code = response_payload.get('statusCode', 200)
    
    # Check for HTTP error status codes
    if status_code >= 500:
        response_body = response_payload.get('body', '')[:500]
        error_msg = f"Server error HTTP {status_code}: {response_body}"
        logger.error(f"Lambda server error for {method} {entity_name}: {error_msg}")
        raise APIError(error_msg, status_code=status_code, entity_type=entity_name)
    elif status_code >= 400:
        response_body = response_payload.get('body', '')[:500]
        error_msg = f"Client error HTTP {status_code}: {response_body}"
        logger.error(f"Lambda client error for {method} {entity_name}: {error_msg}")
        raise APIError(error_msg, status_code=status_code, entity_type=entity_name)
    
    return response_payload.get('body', '{}')

def validate_lambda_response_body(response_data: str, method: str, entity_name: str) -> None:
    """Validate Lambda response body for errors even on successful HTTP status codes."""
    try:
        api_json = json.loads(response_data)
        check_lambda_response_errors(api_json, method, entity_name)
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse Lambda response for {method} {entity_name}: {e}"
        logger.error(error_msg)
        raise APIError(error_msg, entity_type=entity_name) from e
    except Exception as e:
        if isinstance(e, APIError):
            raise
        error_msg = f"Unexpected error validating Lambda response for {method} {entity_name}: {e}"
        logger.error(error_msg)
        raise APIError(error_msg, entity_type=entity_name) from e

def check_lambda_response_errors(api_json: Dict[str, Any], method: str, entity_name: str) -> None:
    """Check for errors in the Lambda response body."""
    if 'errors' not in api_json or not api_json['errors']:
        return
    
    errors = api_json['errors']
    
    if isinstance(errors, list) and errors:
        error_msg = f"Lambda returned errors for {method} {entity_name}: {', '.join(str(e) for e in errors)}"
        logger.error(error_msg)
        raise APIError(error_msg, entity_type=entity_name)
    elif isinstance(errors, dict) and errors:
        error_details = build_lambda_error_details(errors)
        if error_details:
            error_msg = f"Lambda returned errors for {method} {entity_name}: {'; '.join(error_details)}"
            logger.error(error_msg)
            raise APIError(error_msg, entity_type=entity_name)

def build_lambda_error_details(errors: Dict[str, Any]) -> List[str]:
    """Build detailed error messages from error dictionary."""
    error_details = []
    for error_type, error_list in errors.items():
        if error_list:
            if isinstance(error_list, list):
                error_details.append(f"{error_type}: {', '.join(str(e) for e in error_list)}")
            else:
                error_details.append(f"{error_type}: {error_list}")
    return error_details

def create_lambda_response(entity_name: str, data: EntityData, response_payload: Dict[str, Any], response_data: str) -> Dict[str, Any]:
    """Create a response dictionary from Lambda response data."""
    response = {
        'success': True,
        'status_code': response_payload.get('statusCode', 200),
        'items_submitted': len(data),
        'new_items': [],
        'api_errors': {}
    }
    
    try:
        # Validate response body for errors
        validate_lambda_response_body(response_data, 'Lambda', entity_name)
        
        api_json = json.loads(response_data)
        response['new_items'] = api_json.get('newItems', [])
        response['api_errors'] = api_json.get('errors', {})
        
        # Check if there were errors that indicate failure
        if response['api_errors']:
            response['success'] = False
        
    except json.JSONDecodeError:
        response['success'] = False
        response['api_errors'] = {'parse_error': 'Could not parse Lambda response'}
        logger.warning(f"Unexpected JSON decode error for {entity_name} after validation")
    except APIError:
        # Error already logged and raised by validation
        raise
    
    return response