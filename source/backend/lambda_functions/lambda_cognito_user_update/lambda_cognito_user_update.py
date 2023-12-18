#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import botocore
import os

import cmf_boto
from cmf_logger import logger
from cmf_utils import cors, default_http_headers


def add_user_to_current_groups(user, current_group_names, client_cognito_idp):
    # Check through list of groups provided for the user and add them to the groups.
    for group in user['groups']:
        if group not in current_group_names:
            # add group membership as not a member currently.
            logger.info("Adding user '%s' to group '%s'." % (user['username'], group))
            client_cognito_idp.admin_add_user_to_group(
                UserPoolId=os.environ['userpool_id'],
                Username=user['username'],
                GroupName=group
            )


def remove_user_from_current_groups(current_group_names, user, client_cognito_idp):
    # Check through list of currently assigned groups provided for the user and
    # remove from the groups that are not present in request for which they are a member.
    for group in current_group_names:
        if group not in user['groups']:
            logger.info("Removing user '%s' from group '%s'." % (user['username'], group))
            client_cognito_idp.admin_remove_user_from_group(
                UserPoolId=os.environ['userpool_id'],
                Username=user['username'],
                GroupName=group
            )


def add_groups(user, current_group_names, client_cognito_idp):
    for group in user['addGroups']:
        if group not in current_group_names:
            # add group membership as not a member currently.
            logger.info("Adding user '%s' to group '%s'." % (user['username'], group))
            client_cognito_idp.admin_add_user_to_group(
                UserPoolId=os.environ['userpool_id'],
                Username=user['username'],
                GroupName=group
            )


def remove_groups(user, current_group_names, client_cognito_idp):
    for group in user['removeGroups']:
        if group in current_group_names:
            # add group membership as not a member currently.
            logger.info("Removing user '%s' from group '%s'." % (user['username'], group))
            client_cognito_idp.admin_remove_user_from_group(
                UserPoolId=os.environ['userpool_id'],
                Username=user['username'],
                GroupName=group
            )


def set_user_account_state(user, client_cognito_idp):
    if user['enabled']:
        logger.info("Enabling user '%s'." % (user['username']))
        client_cognito_idp.admin_enable_user(
            UserPoolId=os.environ['userpool_id'],
            Username=user['username']
        )
    else:
        logger.info("Disabling user '%s'." % (user['username']))
        client_cognito_idp.admin_disable_user(
            UserPoolId=os.environ['userpool_id'],
            Username=user['username']
        )


def delete_user(user, client_cognito_idp):
    logger.info("Deleting user '%s'." % (user['username']))
    client_cognito_idp.admin_delete_user(
        UserPoolId=os.environ['userpool_id'],
        Username=user['username']
    )


def update_user(user, client_cognito_idp):
    errors = []
    try:
        # Get current groups for user
        user_groups = client_cognito_idp.admin_list_groups_for_user(
            Username=user['username'],
            UserPoolId=os.environ['userpool_id']
        )

        current_group_names = []
        for group in user_groups['Groups']:
            current_group_names.append(group['GroupName'])

        # Support for updating all groups to match the list provided.
        if 'groups' in user:
            add_user_to_current_groups(user, current_group_names, client_cognito_idp)
            remove_user_from_current_groups(current_group_names, user, client_cognito_idp)

        # Add groups only.
        if 'addGroups' in user:
            add_groups(user, current_group_names, client_cognito_idp)

        # Remove groups only.
        if 'removeGroups' in user:
            remove_groups(user, current_group_names, client_cognito_idp)

        # set state of user account.
        if 'enabled' in user:
            set_user_account_state(user, client_cognito_idp)

        # set state of user account.
        if 'delete' in user and user['delete']:
            delete_user(user, client_cognito_idp)

    except client_cognito_idp.exceptions.UserNotFoundException:
        logger.info("User '%s' does not exist , skipping user updates." % user['username'])
        errors.append("User '%s'  does not exist , skipping user updates." % user['username'])
    except client_cognito_idp.exceptions.NotAuthorizedException:
        logger.error("User update Lambda does not have permission to update users "
                     "in pool %s. Cancelling update." % os.environ['userpool_id'])
        errors.append("User update Lambda does not have permission to update users "
                      "in pool %s. Cancelling update." % os.environ['userpool_id'])
        raise
    except botocore.exceptions.ClientError as boto_client_error:
        # Error not specific boto client error.
        logger.error(boto_client_error)
        errors.append("Internal error.")
    except Exception as unknown_error:
        logger.error(unknown_error)
        errors.append("Internal error.")

    return errors


def lambda_handler(event, _):
    client_cognito_idp = cmf_boto.client('cognito-idp')
    body = json.loads(event['body'])
    errors = []

    if 'users' in body:
        for user in body['users']:
            errors = update_user(user, client_cognito_idp)

    if len(errors) > 0:
        return {'headers': {**default_http_headers},
                'statusCode': 400,
                'body': json.dumps(errors)
                }
    else:
        return {'headers': {**default_http_headers},
                'statusCode': 200
                }
