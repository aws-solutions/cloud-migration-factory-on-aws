#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0 
	
import json
import os
import time
import traceback
from typing import Any, Dict, Optional, Tuple
from boto3 import client as boto3_client
from botocore.exceptions import ClientError

import cmf_boto
from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers

# Initialize global resources once for better cold start performance
application = os.environ.get('application')
environment = os.environ.get('environment')

if not application or not environment:
    logger.error("Required environment variables 'application' or 'environment' not set")
    raise EnvironmentError("Required environment variables not set")

# Initialize AWS clients
try:
    sqs = boto3_client('sqs')
    queue_url = sqs.get_queue_url(QueueName=f'{application}-{environment}-genai_socket_queue')['QueueUrl']
    connections_table_name = f'{application}-{environment}-genai_socket_connections'
    connections_table = cmf_boto.resource('dynamodb').Table(connections_table_name)
except Exception as e:
    logger.error(f"Failed to initialize AWS resources: {str(e)}")
    raise

def lambda_handler(event: Dict[str, Any], _) -> Dict[str, Any]:
    """
    Main handler for WebSocket events.
    
    Handles connection, disconnection, and forwarding messages to
    SQS for async operation.
    
    Args:
        event: The Lambda event object containing WebSocket event details
        _: The Lambda context object (unused)
        
    Returns:
        API Gateway response object with status code and message
    """
    try:
        log_event_received(event)
        token = event.get('headers', {}).get('Sec-WebSocket-Protocol', None)

        # Validate and extract request context
        request_context, validation_response = _validate_request_context(event)
        if validation_response:
            return validation_response
        
        # Extract connection details
        connection_id = request_context.get("connectionId")
        domain_name = request_context.get("domainName")
        stage = request_context.get("stage")
        
        # Process based on event type
        event_type = request_context.get("eventType")
        logger.info(f'Processing event type: {event_type}')

        if event_type == "CONNECT":
            # Extract user_id from the authorizer context
            user_id = request_context.get("authorizer", {}).get("user_id")
            if not user_id:
                logger.error("user_id not found in authorizer context")
                return _get_response(401, "Unauthorized: user_id not found")
            return process_connect(connection_id, user_id, token)
            
        elif event_type == "DISCONNECT":
            return process_disconnect(connection_id)
            
        elif event_type == "MESSAGE":
            return process_message(event, connection_id, domain_name, stage)
            
        else:
            logger.error(f'Unexpected event type: {event_type}')
            return _get_response(400, f"Unexpected event type: {event_type}")
    except Exception as e:
        logger.error(f"Unhandled exception in lambda_handler: {str(e)}")
        logger.debug(traceback.format_exc())
        return _get_response(500, f"Internal server error: {str(e)}")

def _validate_request_context(event: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Validates the request context from the event.
    
    Args:
        event: The Lambda event object
        
    Returns:
        Tuple containing the request context and an optional error response
    """
    request_context = event.get("requestContext", {})
    if not request_context:
        logger.error("requestContext is empty")
        return {}, _get_response(400, "requestContext is required")
    
    # Extract connection details
    connection_id = request_context.get("connectionId")
    domain_name = request_context.get("domainName")
    stage = request_context.get("stage")
    
    if not all([connection_id, domain_name, stage]):
        logger.error("connectionId, domainName, and stage are required")
        return request_context, _get_response(400, "connectionId, domainName, and stage are required")
    
    return request_context, None

def process_message(event: Dict[str, Any], connection_id: str, domain: str, stage: str) -> Dict[str, Any]:
    """
    Process a WebSocket message by sending it to SQS for async handling.
    
    Args:
        event: The Lambda event object
        connection_id: The web socket connection ID
        domain: The domain name for the web socket connection
        stage: The stage for the web socket connection
        
    Returns:
        API Gateway response object
    """
    try:
        # Parse and validate message body
        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in message body")
            return _get_response(400, "Invalid JSON in message body")
    
        action = body.get("action")
        if not action:
            logger.error("Action not specified in message body")
            return _get_response(400, "Action must be specified in the body")
        
        logger.info(f'Processing action type: {action}')
        
        # Prepare message for SQS
        message = {
            "connection": {
                "connection_id": connection_id,
                "stage": stage,
                "domain_name": domain
            },
            "action": action,
            "request": {k:v for k,v in body.items() if k != 'action'},
            "timestamp": int(time.time())
        }

        # Send to SQS
        response = sqs.send_message(
            QueueUrl=queue_url, 
            MessageBody=json.dumps(message),
            MessageAttributes={
                'Action': {
                    'DataType': 'String',
                    'StringValue': action
                }
            }
        )
        logger.debug(f"Message sent to SQS with MessageId: {response.get('MessageId')}")
        return _get_response(200, "Message sent for processing")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"SQS error ({error_code}): {str(e)}")
        return _get_response(500, "Failed to send message to queue")
    except Exception as e:
        logger.error(f"Unexpected error in process_message: {str(e)}")
        logger.debug(traceback.format_exc())
        return _get_response(500, "Failed to process message")
        
def process_connect(connection_id: str, user_id: str, token: str) -> Dict[str, Any]:
    """
    Process a new WebSocket connection.
    
    Stores connection details in DynamoDB with TTL for automatic cleanup.
    
    Args:
        connection_id: The WebSocket connection ID
        user_id: The authenticated user ID
        
    Returns:
        API Gateway response object
    """
    logger.info(f'Processing CONNECT for connection: {connection_id}, user: {user_id}')

    # Add TTL for automatic cleanup (24 hours)
    current_time = int(time.time())
    ttl = current_time + (24 * 60 * 60)
    
    try:
        # Store the new connection
        connections_table.put_item(Item={
            "connection_id": connection_id,
            "user_id": user_id,
            "connected_at": current_time,
            "ttl": ttl
        })
        logger.info(f"Connection {connection_id} stored successfully")
        return _get_response(200, "Connection successful", { "Sec-WebSocket-Protocol" : token })
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"DynamoDB error ({error_code}) storing connection: {str(e)}")
        return _get_response(500, "Failed to establish connection")
    except Exception as e:
        logger.error(f"Unexpected error in process_connect: {str(e)}")
        return _get_response(500, "Failed to establish connection")

def process_disconnect(connection_id: str) -> Dict[str, Any]:
    """
    Process a WebSocket disconnection.

    Removes the connection from DynamoDB.
    
    Args:
        connection_id: The WebSocket connection ID
        
    Returns:
        API Gateway response object
    """
    logger.info(f'Processing DISCONNECT for connection: {connection_id}')
    try:
        response = connections_table.delete_item(
            Key={"connection_id": connection_id},
            ReturnValues="ALL_OLD"
        )
        
        # Check if the item was actually deleted
        if "Attributes" in response:
            logger.info(f"Connection {connection_id} deleted successfully")
        else:
            logger.warning(f"Connection {connection_id} not found in table")
            
        return _get_response(200, "Disconnect successful")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"DynamoDB error ({error_code}) deleting connection: {str(e)}")
        return _get_response(500, "Failed to process disconnection")
    except Exception as e:
        logger.error(f"Unexpected error in process_disconnect: {str(e)}")
        return _get_response(500, "Failed to process disconnection")
    
def _get_response(status_code: int, body: Any, headers: Any = None) -> Dict[str, Any]:
    """
    Create a standardized API Gateway response.
    
    Args:
        status_code: HTTP status code
        body: Response body (will be converted to JSON string if not already)
        headers: Optional additional headers to merge with defaults
        
    Returns:
        Formatted API Gateway response
    """
    if not isinstance(body, str):
        body = json.dumps(body)
    
    response_headers = {**default_http_headers}
    if headers:
        response_headers.update(headers)
    
    return {
        "headers": response_headers,
        "statusCode": status_code,
        "body": body
    }