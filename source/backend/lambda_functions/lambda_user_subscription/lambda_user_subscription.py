import cmf_boto
import botocore
from cmf_logger import logger
from cmf_constants import COGNITO_POST_AUTH_TRIGGER_SOURCE, COGNITO_CREATE_USER_TRIGGER_SOURCE
import os
import json

topic_arn = os.environ['topicArn']
application = os.environ['application']
environment = os.environ['environment']

# Initialize the SNS client
sns = cmf_boto.client('sns')

# Initialize the Cognito client
cognito = cmf_boto.client('cognito-idp')

dynamodb = cmf_boto.resource("dynamodb")
subscriptions_table_name = f'{application}-{environment}-subscriptions'
subscriptions_table = dynamodb.Table(subscriptions_table_name)

def validate_event(event) -> bool:
    """
    Validates the structure and content of a Cognito trigger event.

    This function performs validation checks on the event object received from 
    Cognito triggers (PreSignUp or PostAuthentication). It verifies the presence 
    and validity of required fields and attributes.

    Args:
        event (dict): The event object from Cognito trigger containing user 
                     registration or authentication data.

    Returns:
        bool: True if the event is valid and contains all required fields,
              False otherwise.

    Required event structure:
        {
            'triggerSource': str,  # Must be 'PreSignUp_AdminCreateUser' or 'PostAuthentication_Authentication'
            'userName': str,
            'request': {
                'userAttributes': {
                    'email': str
                }
            }
        }
    """
    # Check if the event has triggerSource
    if 'triggerSource' not in event:
        logger.error('Invalid event: Missing triggerSource')
        return False

    # Validate that the triggerSource is 'PreSignUp_AdminCreateUser'
    if event['triggerSource'] != COGNITO_CREATE_USER_TRIGGER_SOURCE and event['triggerSource'] != COGNITO_POST_AUTH_TRIGGER_SOURCE:
        logger.error(f'Invalid event: Unexpected triggerSource {event["triggerSource"]}')
        return False
    
    # Validate event has the right structure
    if 'request' not in event or 'userAttributes' not in event['request']:
        logger.error('Invalid event: Missing request or userAttributes')
        return False

    # Validate cognito username is present in event
    if 'userName' not in event:
        logger.error('Invalid event: Missing userName')
        return False

    # Validate that email is available in user attributes
    if 'email' not in event['request']['userAttributes']:
        logger.error('Invalid event: Missing email in userAttributes')
        return False

    # Validation passed
    return True

def create_user_subscription(
        username: str,
        email_address: str,
        filter_policy: dict) -> str:
    """
    Creates an SNS subscription for a user and stores the subscription details in DynamoDB.
    
    Args:
        username: User's username
        email_address: User's email address
        filter_policy: SNS filter policy
        
    Returns:
        str: Subscription ARN
    """
    response = sns.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint=email_address,
        ReturnSubscriptionArn=True,
        Attributes={
            'FilterPolicy': json.dumps(filter_policy)
        }
    )
    logger.info(f"Created SNS subscription for user: {json.dumps(response)}")

    subscription_arn = response['SubscriptionArn']

    # Store user subscription details for future management
    subscriptions_table.put_item(
        Item={
            'username': username,
            'email': email_address,
            'subscription_arn': subscription_arn
        }
    )

    logger.info(f"Stored subscription details for user with username: {username}")
    
    return subscription_arn


def handle_create_user(username: str, 
    email_address: str,
    filter_policy: dict) -> None:
    """
    Handles the creation of a new Cognito user by adding a SNS subscriber.

    This function is triggered during the Cognito PreSignUp process when a new user
    is created. It performs the following actions:
    1. Creates an email subscription to the specified SNS topic
    2. Applies a filter policy to the subscription
    3. Stores the subscription details in DynamoDB for user notification management

    Args:
        username (str): The Cognito username of the new user
        email_address (str): The email address of the new user
        filter_policy (dict): The SNS topic filter policy for the user's notifications

    Returns:
        None
    """
    try:
        # Subscribe new user to SNS topic for notifications
        create_user_subscription(username, email_address, filter_policy)

    except Exception as e:
        logger.error(f"Error during new user creation process: {str(e)}")

def handle_post_authentication(
    username: str,
    email_address: str,
    filter_policy: dict
) -> None:
    """
    Handles post-authentication subscription updates for a Cognito user.

    This function is triggered after successful user authentication in CMF, to manage SNS
    subscriptions. It performs the following actions:
    1. Retrieves the user's existing subscription from DynamoDB
    2. Removes the old subscription if it exists
    3. Creates a new subscription with updated email address
    4. Updates the subscription record in DynamoDB

    Args:
        username (str): The Cognito username of the authenticated user
        email_address (str): The current email address of the user
        filter_policy (dict): The SNS topic filter policy for the user's notifications

    Returns:
        None
    """
    try:
        # Retrieve existing subscription information
        subscription_item = subscriptions_table.get_item(
            Key={
                'username': username
            }
        )

        if 'Item' not in subscription_item:
            logger.error(f"No existing subscription found for user: {username}")
            return

        subscription_arn = subscription_item['Item']['subscription_arn']
        old_email_address = subscription_item['Item']['email']

        if old_email_address == email_address:
            logger.info(f"No change in email for user: {username}, SNS subscription update not needed.")
            return

        # Remove existing subscription
        try:
            sns.unsubscribe(SubscriptionArn=subscription_arn)
            logger.info(f"Unsubscribed old subscription: {subscription_arn}")
        except Exception as e:
            logger.error(f"Error unsubscribing: {str(e)}")

        # Create new subscription with updated email
        try:
            create_user_subscription(username, email_address, filter_policy)

        except Exception as e:
            logger.error(f"Error creating new subscription: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error in post authentication handling: {str(e)}")



def lambda_handler(event, _):
    if not validate_event(event):
        return event

    email_address = event['request']['userAttributes']['email']
    filter_policy = {
        "Email": [
            email_address
        ]
    }

    username = event['userName']

    if event.get('triggerSource') == COGNITO_CREATE_USER_TRIGGER_SOURCE:
        handle_create_user(username, email_address, filter_policy)
        
    elif event.get('triggerSource') == COGNITO_POST_AUTH_TRIGGER_SOURCE:
        handle_post_authentication(username, email_address, filter_policy)
        
    return event