import os
import json
from typing import Any, Dict, List
from boto3 import client as boto3_client
from botocore.config import Config
from botocore.exceptions import ClientError

from cmf_logger import logger
from cmf_utils import send_anonymous_usage_data
from shared.header_mapping import process_map_headers_request

model = os.environ["model"]

# Initialize clients once outside handler for better performance
bedrock_runtime = boto3_client(
    "bedrock-runtime",
    config=Config(
        connect_timeout=5,  # Connection timeout in seconds
        read_timeout=60,  # Read timeout in seconds
    ),
)

def lambda_handler(event: Dict[str, Any], _) -> Dict[str, Any]:
    """Process SQS messages for WebSocket communication.

    Args:
        event: Lambda event containing SQS records
        _: Lambda context (unused)

    Returns:
        Response dictionary
    """

    # Follows https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html
    results = {
        "batchItemFailures": [],
    }

    for message in event.get("Records", []):
        message_id = message.get("messageId")
        try:
            process_message(message)
        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {str(e)}")
            results["batchItemFailures"].append({"itemIdentifier": message_id})
    return results


def process_message(message: Dict[str, Any]):
    """Process a single SQS message.

    Args:
        message: SQS message dictionary

    Raises:
        ValueError: For invalid message format or unknown action
        ClientError: For AWS service errors
        Exception: For other processing errors
    """
    connection_id = None
    api_gateway_management_api = None
    action = None
    
    try:
        # Parse the message body
        message_data = json.loads(message["body"])

        # Validate required fields
        _validate_message_structure(message_data)

        # Extract connection information
        connection = message_data["connection"]
        domain = connection["domain_name"]
        stage = connection["stage"]
        connection_id = connection["connection_id"]
        action = message_data["action"]

        logger.info(f"Processing {action} action for connection {connection_id}")

        # Initialize API Gateway client
        api_gateway_management_api = boto3_client("apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}")

        # Check model availability
        if model == "Not Supported":
            raise ValueError("No preferred model was available. Confirm Bedrock is available in your deployed AWS Region")

        # Process based on action type
        if action == "MAP_HEADERS":
            request = message_data.get("request", {})
            if not request:
                raise ValueError("Request data is missing")
            result = process_map_headers_request(request, bedrock_runtime, model)
            send_anonymous_usage_data('HeaderMappingComplete_Async')
        else:
            raise ValueError(f"Unknown action: {action}")

        response = {"action": action, "result": result}
        post_to_connection(api_gateway_management_api, connection_id, response)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message body: {e}")
        _send_error_response(api_gateway_management_api, connection_id, action, f"Invalid JSON in message body: {str(e)}")
        raise ValueError(f"Invalid JSON in message body: {str(e)}")
    except KeyError as e:
        logger.error(f"Missing required field in message: {e}")
        _send_error_response(api_gateway_management_api, connection_id, action, f"Missing required field in message: {str(e)}")
        raise ValueError(f"Missing required field in message: {str(e)}")
    except ClientError as e:
        logger.error(f"AWS service error: {e}")
        _send_error_response(api_gateway_management_api, connection_id, action, f"AWS service error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        _send_error_response(api_gateway_management_api, connection_id, action, f"Processing error: {str(e)}")
        raise


def _validate_message_structure(message_data: Dict[str, Any]) -> None:
    """Validate the message has all required fields.

    Args:
        message_data: Parsed message data

    Raises:
        ValueError: If required fields are missing
    """
    if "connection" not in message_data:
        raise ValueError("Missing 'connection' field in message")

    connection = message_data["connection"]
    required_conn_fields = ["connection_id", "stage", "domain_name"]
    for field in required_conn_fields:
        if field not in connection:
            raise ValueError(f"Missing '{field}' in connection information")

    if "action" not in message_data:
        raise ValueError("Missing 'action' field in message")


def post_to_connection(api_gateway_management_api: Any, connection_id: str, data: Any) -> None:
    """
    Post data to a WebSocket connection.

    Args:
        api_gateway_management_api: API Gateway management client
        connection_id: The WebSocket connection ID
        data: The data to send

    Raises:
        RuntimeError: If posting to the connection fails
    """
    try:
        api_gateway_management_api.post_to_connection(ConnectionId=connection_id, Data=json.dumps(data))
    except Exception as e:
        logger.warning(f"Error posting to connection {connection_id}: {str(e)}")
        raise RuntimeError(f"Failed to post to connection: {str(e)}")


def _send_error_response(api_gateway_management_api: Any, connection_id: str, action: str, error_message: str) -> None:
    """
    Send an error response back to the WebSocket client.

    Args:
        api_gateway_management_api: API Gateway management client
        connection_id: The WebSocket connection ID
        action: The action that failed
        error_message: The error message to send
    """
    if not api_gateway_management_api or not connection_id:
        return
    
    try:
        error_response = {
            "action": action or "UNKNOWN",
            "error": error_message
        }
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id, 
            Data=json.dumps(error_response)
        )
        logger.info(f"Error response sent to connection {connection_id}")
    except Exception as e:
        logger.warning(f"Failed to send error response to connection {connection_id}: {str(e)}")
