import traceback
import cmf_boto
import botocore
from datetime import datetime, timezone
from cmf_logger import logger
import os
import json
from cmf_types import NotificationDetailType, NotificationType, Pipeline, NotificationEvent
from typing import Dict, List, Optional, Set
from botocore.exceptions import ClientError
from cmf_constants import (
    DETAIL_TYPE,
    DETAIL,
    SOURCE,
    TASK_ID,
    TYPE,
    ITEM,
    PIPELINE_ID,
    CURRENT_TASK_ID,
    PIPELINE_NAME,
    PIPELINE_DESCRIPTION,
    PIPELINE_DEFAULT_EMAIL_GROUPS,
    PIPELINE_DEFAULT_EMAIL_RECIPIENTS,
    PIPELINE_ENABLE_EMAIL_NOTIFICATIONS,
    EMAIL,
    TASK_LEVEL_EMAIL_SETTINGS,
    EMAIL_GROUPS,
    EMAIL_USERS,
    EMAIL_BODY,
    ENABLED,
    OVERRIDE_DEFAULTS
)


# Initialize AWS clients
sns = cmf_boto.client('sns')
cognito = cmf_boto.client('cognito-idp')
dynamodb = cmf_boto.resource("dynamodb")

# Environment variables
application = os.environ['application']
environment = os.environ['environment']
user_pool_id = os.environ['user_pool_id']
sns_topic_arn = os.environ['sns_topic_arn']
pipeline_table_name = f"{application}-{environment}-pipelines"

pipeline_table = dynamodb.Table(pipeline_table_name)

def validate_event(event) -> bool:
    """
    Validates the incoming EventBridge event payload.

    Args:
        event (dict): The EventBridge event to validate containing:
            - detail-type (str): Type of notification event
            - detail (dict): Event details including pipeline_id, task_id, type
            - source (str): Event source

    Returns:
        bool: True if event is valid, False otherwise

    Raises:
        Exception: If there is an error during validation
    """
    try:
        # Validate event structure
        required_event_fields = [DETAIL_TYPE, DETAIL, SOURCE]
        if not all(field in event for field in required_event_fields):
            logger.error(f"Missing required event fields. Required: {required_event_fields}")
            return False

        # Validate detail-type
        valid_detail_types = [
            NotificationDetailType.TASK_MANUAL_APPROVAL.value,
            NotificationDetailType.TASK_FAILED.value,
            NotificationDetailType.TASK_SEND_EMAIL.value
        ]
        if event[DETAIL_TYPE] not in valid_detail_types:
            logger.error(f"Invalid detail-type: {event.get(DETAIL_TYPE)}. Expected one of: {valid_detail_types}")
            return False

        # Validate detail
        detail = event[DETAIL]
        required_detail_fields = [PIPELINE_ID, TASK_ID, TYPE]
        if not all(field in detail for field in required_detail_fields):
            logger.error(f"Missing required detail fields. Required: {required_detail_fields}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error validating event: {str(e)}")
        return False
    

def get_pipeline_item(pipeline_id: str) -> Optional[Pipeline]:
    """
        Retrieves specific pipeline fields from DynamoDB and converts it to a Pipeline object.

        Args:
            pipeline_id (str): The unique identifier of the pipeline to retrieve from DynamoDB

        Returns:
            Optional[Pipeline]: A Pipeline object containing the pipeline configuration if found,
                            None if no pipeline exists with the given ID

        Raises:
            Exception: If there is an error accessing DynamoDB or parsing the response
    """
    try:
        response = pipeline_table.get_item(
            Key={PIPELINE_ID: pipeline_id}
        )
        
        if ITEM not in response:
            return None
            
        item = response[ITEM]
        default_recipients = item.get(PIPELINE_DEFAULT_EMAIL_RECIPIENTS, [])
        
        pipeline: Pipeline = {
            PIPELINE_ID: item.get(PIPELINE_ID),
            CURRENT_TASK_ID: item.get(CURRENT_TASK_ID),
            'default_email_groups': item.get(PIPELINE_DEFAULT_EMAIL_GROUPS, []),
            'default_email_recipients': [
                recipient[EMAIL]
                for recipient in default_recipients
            ] if default_recipients else [],
            'description': item.get(PIPELINE_DESCRIPTION),
            'name': item[PIPELINE_NAME]
        }

        if PIPELINE_ENABLE_EMAIL_NOTIFICATIONS in item:
            pipeline['enable_email_notifications'] = item.get(PIPELINE_ENABLE_EMAIL_NOTIFICATIONS)
            
        if TASK_LEVEL_EMAIL_SETTINGS in item:
            pipeline[TASK_LEVEL_EMAIL_SETTINGS] = [
                {
                    EMAIL_BODY: task.get(EMAIL_BODY, ''),
                    EMAIL_GROUPS: task.get(EMAIL_GROUPS, []),
                    EMAIL_USERS: [
                        user.get(EMAIL)
                        for user in task.get(EMAIL_USERS, [])
                    ] if task.get(EMAIL_USERS) else [],
                    TASK_ID: task.get(TASK_ID),
                    ENABLED: task.get(ENABLED, False),
                    OVERRIDE_DEFAULTS: task.get(OVERRIDE_DEFAULTS, False)
                }
                for task in item[TASK_LEVEL_EMAIL_SETTINGS]
            ]
        
        return pipeline
        
    except Exception as e:
        logger.error(f"Error retrieving pipeline {pipeline_id}: {str(e)}")
        raise

def get_cognito_group_emails(group_names: List[str]) -> Set[str]:
    """
    Retrieves the email addresses of Cognito users who are members of the specified groups.

    Args:
        group_names (list): A list of Cognito group names.

    Returns:
        set: A set of email addresses for the users in the specified groups.

    Raises:
        ClientError: When there are errors accessing Cognito
    """
    user_emails = set()

    for group_name in group_names:
        try:
            response = cognito.list_users_in_group(
                UserPoolId=user_pool_id,
                GroupName=group_name,
                Limit=60
            )

            logger.info(f'Cognito list users response: {str(response)}')

            for user in response['Users']:
                email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == EMAIL), None)
                if email:
                    user_emails.add(email)
                else:
                    logger.warning(f"No email found for user '{user['Username']}' in group '{group_name}'.")

            next_token = response.get('NextToken')
            while next_token:
                response = cognito.list_users_in_group(
                    UserPoolId=user_pool_id,
                    GroupName=group_name,
                    Limit=60,
                    NextToken=next_token
                )

                for user in response['Users']:
                    email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == EMAIL), None)
                    if email:
                        user_emails.add(email)
                    else:
                        logger.warning(f"No email found for user '{user['Username']}' in group '{group_name}'.")

                next_token = response.get('NextToken')

        except ClientError as e:
            logger.error(f"Error retrieving users in group '{group_name}': {e}")

    return user_emails

def get_default_recipients(pipeline: Pipeline) -> Set[str]:
    """
    Gets default recipients and groups from Pipelines DynamoDB Table.

    Args:
        pipeline (Pipeline): Pipeline DynamoDB record for a specific pipeline

    Returns:
        Set[str]: List of email addresses for default recipients
            
    Raises:
        Exception: If there is an error accessing DynamoDB or required fields are missing from the pipeline item
    """
    try:
        default_recipients = set(pipeline.get('default_email_recipients', []))
        default_groups = [
            group['group_name'] 
            for group in pipeline.get('default_email_groups', [])
        ]

        default_group_email_addresses = get_cognito_group_emails(default_groups)

        # Combine both sets of emails
        return default_recipients | default_group_email_addresses
    except Exception as e:
        logger.error(f"Error getting default recipients: {str(e)}")
        return set()

def get_task_level_email_config(pipeline: Pipeline, task_name: str) -> tuple[set[str], str, bool]:
    """
    Retrieves task-specific email recipients and email body from the pipeline configuration.
    Combines direct email recipients and Cognito group member emails.

    Args:
        pipeline (Pipeline): The pipeline object containing task email settings
        task_name (str): The task name to look up, will be prefixed with pipeline name

    Returns:
        tuple: A tuple containing:
            - set[str]: Set of email addresses from both direct recipients and group members
            - str: Email body template for the task, empty string if not found
            - bool: Task level email notifications enabled

    Raises:
        botocore.exceptions.ClientError: If there is an error accessing Cognito
        Exception: For any other errors during processing
    """
    try:
        pipeline_task_id = f"{pipeline.get('name')}:{task_name}"
        task_emails_enabled = False
        
        # Find matching task config
        task_settings = pipeline.get('task_level_email_settings', [])
        for task_config in task_settings:
            if (task_config[TASK_ID] == pipeline_task_id):
                task_emails_enabled = task_config.get(ENABLED, False)
                if task_emails_enabled and task_config[OVERRIDE_DEFAULTS]:
                    # Get direct email recipients
                    task_recipients = set(task_config.get(EMAIL_USERS, []))
                    
                    # Get group member emails
                    task_groups = [
                        group['group_name'] 
                        for group in task_config.get(EMAIL_GROUPS, [])
                    ]
                    task_group_email_addresses = get_cognito_group_emails(task_groups)
                    
                    # Combine both sets of emails
                    all_task_recipients = task_recipients | task_group_email_addresses
                    
                    return all_task_recipients, task_config.get(EMAIL_BODY, ''), task_emails_enabled
                
        return set(), '', task_emails_enabled

    except Exception as e:
        logger.error(f"Error getting task level recipients: {str(e)}")
        return set(), '', task_emails_enabled


def format_notification_message(event_detail: dict, task_name: str) -> str:
    """
    Formats the notification message based on the event type.

    Args:
        event_detail (dict): Event detail containing:
            - type (str): Type of notification
            - pipeline_id (str): ID of the pipeline
            - task_id (str): ID of the task
            - timestamp (str, optional): ISO format timestamp
            - error_message (str, optional): Error message for failed tasks
        task_name (str): Name of the task

    Returns:
        str: Formatted notification message

    """
    event_type = event_detail.get(TYPE)
    pipeline_name = event_detail.get(PIPELINE_NAME)
    iso_timestamp = event_detail.get('timestamp', datetime.now(timezone.utc).isoformat())
    dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
    # Format: May 2, 2025 03:35 AM UTC
    timestamp = dt.strftime('%B %d, %Y %I:%M %p %Z')
    
    base_message = f"Pipeline Name: {pipeline_name}\nTask: {task_name}\nTimestamp: {timestamp}\n\n"

    if event_type == NotificationDetailType.TASK_MANUAL_APPROVAL.value:
        return f"Manual Approval Required\n\n{base_message}This task requires manual approval to proceed."
    elif event_type == NotificationDetailType.TASK_FAILED.value:
        error_message = event_detail.get('content', 'No error details available')
        return f"Task Execution Failed\n\n{base_message}Error: {error_message}"
    elif event_type == NotificationDetailType.TASK_SEND_EMAIL.value:
        return f"Email Automation\n\n{base_message}"

def get_notification_display_name(detail_type: str) -> str:
        """
        Maps detail type values to human-readable display formats for email.
        
        Args:
            detail_type (str): The detail type value from the event
            
        Returns:
            str: Human-readable display format of the detail type
        """
        detail_type_map: Dict[str, str] = {
            "EmailAutomationTaskType": "Email Automation",
            "TaskFailed": "Task Execution Failed",
            "TaskManualApprovalNeeded": "Manual Approval Needed"
        }
        
        return detail_type_map.get(detail_type, detail_type)

def publish_email_notification(recipients, message: str, subject: str) -> bool:
    """
    Publishes SNS notification to specified recipients.

    Args:
        recipients (list[str]): List of email addresses to send notification to
        message (str): The notification message body
        subject (str, optional): The email subject line. Defaults to "Migration Factory Notification"

    Returns:
        bool: True if notification was sent successfully, False otherwise

    Raises:
        botocore.exceptions.ClientError: If there is an error publishing to SNS
        Exception: For any other errors during publishing
    """
    try:
        if not recipients:
            logger.error("No recipients specified for notification")
            return False

        message_attributes = {
            'Email': {
                'DataType': 'String.Array',
                'StringValue': json.dumps(recipients, sort_keys=True)
            }
        }

        response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            Subject=subject,
            MessageAttributes=message_attributes
        )

        logger.info(f"Successfully published notification: {response['MessageId']}")
        return True
    except Exception as e:
        logger.error(f"Error publishing notification: {str(e)}")
        return False

def lambda_handler(event: NotificationEvent, _):
    """
    Main handler function for email notifications.
    Processes EventBridge events and sends notifications to appropriate recipients.

    Args:
        event (NotificationEvent): The EventBridge event containing:
            - detail-type (str): Type of notification event
            - detail (dict): Event details including:
                - pipeline_id (str): ID of the pipeline
                - task_id (str): ID of the task
                - type (str): Type of notification
                - task_name (str, optional): Name of the task

    Returns:
        dict: Response containing:
            - statusCode (int): HTTP status code
            - body (str): JSON string containing response message or error

    Raises:
        Exception: For any unhandled errors during processing
    """

    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Validate event payload
        if not validate_event(event):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event payload'})
            }

        detail: NotificationType = event.get(DETAIL)
        pipeline_id = detail.get(PIPELINE_ID)
        task_id = detail.get(TASK_ID)
        task_name = detail.get('task_name', 'Unknown Task')

        pipeline: Pipeline = get_pipeline_item(pipeline_id)

        if not pipeline:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Pipeline with pipeline id {pipeline_id} not found'})
            }

        if not pipeline.get('enable_email_notifications'):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': f'Email notifications are disabled for pipeline with pipeline id {pipeline_id}'})
            }

        detail[PIPELINE_NAME] = pipeline.get('name')
        # Get default recipients
        default_recipients = get_default_recipients(pipeline)

        # Get task level recipients
        task_recipients, custom_email_body, task_email_enabled = get_task_level_email_config(pipeline, task_name)

        base_email_body = format_notification_message(detail, task_name)

        # Use user provided custom email body if provided else format notification message based on event type
        message = (custom_email_body + "\n\n" + base_email_body) if custom_email_body else base_email_body
        # Map detail type to a more human-readable format using the centralized method
        detail_type_display = get_notification_display_name(event.get(DETAIL_TYPE))
        subject = f"{detail_type_display} - {application} - {environment} env"

        #truncate subject to 100 characters because sns publish command has this constraint
        subject = subject[:100] if len(subject) > 100 else subject

        # Try task level recipients first
        if task_recipients and publish_email_notification(list(task_recipients), message, subject):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Email Notification sent to task level recipients'})
            }

        # Fall back to default recipients if email notifications are enabled for the task
        if default_recipients and task_email_enabled and publish_email_notification(list(default_recipients), message, subject):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Email Notification sent to default recipients'})
            }

        # If both attempts fail
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to send email notification to any recipients'})
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}\n{traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
