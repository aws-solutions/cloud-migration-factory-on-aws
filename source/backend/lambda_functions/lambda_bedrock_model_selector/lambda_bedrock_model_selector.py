#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Bedrock Model Selector Lambda Function

This CloudFormation custom resource dynamically selects the best available
Bedrock model based on a preference hierarchy and regional availability.

Model Priority (highest to lowest):
1. Sonnet 4 (anthropic.claude-sonnet-4-20250514-v1:0)
2. Sonnet 3.7 (anthropic.claude-3-7-sonnet-20250219-v1:0)
3. Sonnet 3.5v2 (anthropic.claude-3-5-sonnet-20241022-v2:0)
4. Sonnet 3.5 (anthropic.claude-3-5-sonnet-20240620-v1:0)
5. Sonnet 3 (anthropic.claude-3-sonnet-20240229-v1:0)
6. Nova Pro (amazon.nova-pro-v1:0)

Inference Type Priority:
- ON_DEMAND (preferred) - Direct foundation model access
- INFERENCE_PROFILE (fallback) - Cross-region inference profile

Returns:
- {"supported": True, "modelArn": "<arn>"} - When a model is available
- {"supported": False, "modelArn": "Not Supported"} - When no models available
"""

import boto3
import json
import urllib3
import time
from cmf_logger import logger

bedrock = boto3.client('bedrock')

# An ordered list of the preferred models
preferred_models = [
    'anthropic.claude-sonnet-4-20250514-v1:0',     # Sonnet 4
    'anthropic.claude-3-7-sonnet-20250219-v1:0',   # Sonnet 3.7
    'anthropic.claude-3-5-sonnet-20241022-v2:0',   # Sonnet 3.5v2
    'anthropic.claude-3-5-sonnet-20240620-v1:0',   # Sonnet 3.5
    'anthropic.claude-3-sonnet-20240229-v1:0',     # Sonnet 3
    'amazon.nova-pro-v1:0'                         # Nova Pro
]

# Response when no supported models are found in the region
# We cannot create a Condition in CloudFormation that uses the output of a Custom Resource.
# Therefore, we still need to set the modelArn and create the infrastructure.
# However, the UI will remove functionality and the APIs will fast respond based on the `modelArn`
invalid_response = {
    "supported": False,
    "modelArn": "Not Supported"
}

def lambda_handler(event, context):
    """
    CloudFormation custom resource handler for Bedrock model selection.
    
    Args:
        event: CloudFormation event containing RequestType (Create/Update/Delete)
        context: Lambda context object
    
    Returns:
        None - Sends response directly to CloudFormation via ResponseURL
    """
    logger.info(f"Processing {event['RequestType']} request")
    try:
        if event['RequestType'] in ['Create', 'Update']:
            # Only perform model selection on Create/Update events
            result = get_best_model()
            logger.info(f"Model selection result: {result}")
            send_response(event, context, 'SUCCESS', result)
        else:
            # Delete events don't require model selection
            logger.info("Processing DELETE request")
            send_response(event, context, 'SUCCESS')
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        send_response(event, context, 'FAILED')

def get_foundation_models():
    """
    Retrieve all available foundation models in the current region.
    
    Returns:
        dict: Mapping of modelId to model metadata
    """
    foundation_models = {}
    response = bedrock.list_foundation_models()
    for model in response['modelSummaries']:
        foundation_models[model['modelId']] = model
    return foundation_models

def get_inference_profiles():
    """
    Retrieve system-defined inference profiles with their associated models.
    Uses pagination to handle large result sets.
    
    Returns:
        dict: Mapping of inferenceProfileArn to list of model ARNs
    """
    inference_profiles = {}
    paginator = bedrock.get_paginator('list_inference_profiles')
    # Only get system-defined profiles (not custom ones)
    for page in paginator.paginate(typeEquals='SYSTEM_DEFINED'):
        for profile in page['inferenceProfileSummaries']:
            # Map profile ARN to list of model ARNs it supports
            inference_profiles[profile['inferenceProfileArn']] = [m['modelArn'] for m in profile['models']]
    return inference_profiles

def check_model_availability(model_id, model, inference_profiles_cache):
    """
    Check model availability via ON_DEMAND or INFERENCE_PROFILE access.
    Lazy loads inference profiles only when needed for performance.

    Returns:
        dict or None: Model result if available, None otherwise
    """
    inference_types = model.get('inferenceTypesSupported', [])
    logger.debug(f"Model {model_id} supports: {inference_types}")
    
    # Prefer ON_DEMAND access (direct model access)
    if 'ON_DEMAND' in inference_types:
        logger.info(f"Selected ON_DEMAND model: {model_id}")
        return {"supported": True, "modelArn": model['modelArn']}
    
    # Fallback to INFERENCE_PROFILE (cross-region access)
    elif 'INFERENCE_PROFILE' in inference_types:
        if inference_profiles_cache['profiles'] is None:
            logger.debug("Fetching inference profiles")
            inference_profiles_cache['profiles'] = get_inference_profiles()
            logger.info(f"Found {len(inference_profiles_cache['profiles'])} inference profiles")
        
        # Find inference profile that supports this model
        for profile_arn, model_arns in inference_profiles_cache['profiles'].items():
            if model['modelArn'] in model_arns:
                logger.info(f"Selected INFERENCE_PROFILE: {profile_arn} for model {model_id}")
                return {"supported": True, "modelArn": profile_arn}
    
    return None

def find_best_model():
    """
    Core logic to find the best available Bedrock model based on preferences.
    
    Returns:
        dict: Model selection result with 'supported' and 'modelArn' keys
    """
    logger.debug("Fetching foundation models")
    foundation_models = get_foundation_models()
    logger.info(f"Found {len(foundation_models)} foundation models")
    
    # Lazy load inference profiles only when needed
    inference_profiles_cache = {'profiles': None}
    
    # Check each model in preference order
    for model_id in preferred_models:
        logger.debug(f"Checking model: {model_id}")
        if model_id in foundation_models:
            result = check_model_availability(model_id, foundation_models[model_id], inference_profiles_cache)
            if result:
                return result
        else:
            logger.debug(f"Model {model_id} not available in this region")
    
    logger.warning("No supported models found")
    return invalid_response

def get_best_model():
    """
    Retry wrapper for model selection with exponential backoff.
    
    Handles transient API failures by retrying up to 3 times with
    exponential backoff (1s, 2s, 4s delays).
    
    Returns:
        dict: Model selection result or invalid_response on failure
    """
    logger.info("Starting model selection process")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1} to find best model")
            return find_best_model()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                # Exponential backoff: 2^0=1s, 2^1=2s, 2^2=4s
                sleep_time = 2 ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("All retry attempts failed, returning invalid response")
                return invalid_response
    
def send_response(event, context, status, data=None):
    """
    Send response back to CloudFormation for custom resource completion.
    
    Args:
        event: CloudFormation event containing ResponseURL and identifiers
        context: Lambda context for log stream reference
        status: 'SUCCESS' or 'FAILED'
        data: Optional data to return to CloudFormation (becomes !GetAtt values)
    """
    # Build CloudFormation custom resource response
    response_body = {
        'Status': status,
        'Reason': f'See CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': context.log_stream_name,  # Unique resource identifier
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': data or {}  # Data becomes available via !GetAtt
    }
    
    # Send response to CloudFormation via pre-signed URL
    http = urllib3.PoolManager()
    http.request('PUT', event['ResponseURL'], 
                body=json.dumps(response_body),
                headers={'Content-Type': 'application/json'})