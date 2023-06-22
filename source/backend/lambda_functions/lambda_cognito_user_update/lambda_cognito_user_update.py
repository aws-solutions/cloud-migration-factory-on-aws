#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################

import json
import boto3
import botocore
import os
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}


def lambda_handler(event, context):
    client = boto3.client('cognito-idp')
    body = json.loads(event['body'])
    errors = []

    if 'users' in body:
        for user in body['users']:
            try:
                # Get current groups for user
                user_groups = client.admin_list_groups_for_user(
                    Username=user['username'],
                    UserPoolId=os.environ['userpool_id']
                )

                current_group_names = []
                for group in user_groups['Groups']:
                    current_group_names.append(group['GroupName'])

                # Support for updating all groups to match the list provided.
                if 'groups' in user:
                    # Check through list of groups provided for the user and add them to the groups.
                    for group in user['groups']:
                        if group not in current_group_names:
                            # add group membership as not a member currently.
                            logger.info("Adding user '%s' to group '%s'." % (user['username'], group))
                            client.admin_add_user_to_group(
                                UserPoolId=os.environ['userpool_id'],
                                Username=user['username'],
                                GroupName=group
                            )

                    # Check through list of currently assigned groups provided for the user and
                    # remove from the groups that are not present in request for which they are a member.
                    for group in current_group_names:
                        if group not in user['groups']:
                            logger.info("Removing user '%s' from group '%s'." % (user['username'], group))
                            client.admin_remove_user_from_group(
                                UserPoolId=os.environ['userpool_id'],
                                Username=user['username'],
                                GroupName=group
                            )

                # Add groups only.
                if 'addGroups' in user:
                    for group in user['addGroups']:
                        if group not in current_group_names:
                            # add group membership as not a member currently.
                            logger.info("Adding user '%s' to group '%s'." % (user['username'], group))
                            client.admin_add_user_to_group(
                                UserPoolId=os.environ['userpool_id'],
                                Username=user['username'],
                                GroupName=group
                            )

                # Remove groups only.
                if 'removeGroups' in user:
                    for group in user['removeGroups']:
                        if group in current_group_names:
                            # add group membership as not a member currently.
                            logger.info("Removing user '%s' from group '%s'." % (user['username'], group))
                            client.admin_remove_user_from_group(
                                UserPoolId=os.environ['userpool_id'],
                                Username=user['username'],
                                GroupName=group
                            )

                # set state of user account.
                if 'enabled' in user:
                    if user['enabled']:
                        logger.info("Enabling user '%s'." % (user['username']))
                        client.admin_enable_user(
                            UserPoolId=os.environ['userpool_id'],
                            Username=user['username']
                        )
                    else:
                        logger.info("Disabling user '%s'." % (user['username']))
                        client.admin_disable_user(
                            UserPoolId=os.environ['userpool_id'],
                            Username=user['username']
                        )

                # set state of user account.
                if 'delete' in user and user['delete']:
                    logger.info("Deleting user '%s'." % (user['username']))
                    client.admin_delete_user(
                        UserPoolId=os.environ['userpool_id'],
                        Username=user['username']
                    )
            except client.exceptions.UserNotFoundException as boto_client_error_no_user:
                logger.info("User '%s' does not exist , skipping user updates." % user['username'])
                errors.append("User '%s'  does not exist , skipping user updates." % user['username'])
                pass
            except client.exceptions.NotAuthorizedException as boto_client_error_permissions:
                logger.error("User update Lambda does not have permission to update users "
                             "in pool %s. Cancelling update." % os.environ['userpool_id'])
                errors.append("User update Lambda does not have permission to update users "
                              "in pool %s. Cancelling update." % os.environ['userpool_id'])
                raise
            except botocore.exceptions.ClientError as boto_client_error:
                # Error not specific boto client error.
                logger.error(boto_client_error)
                errors.append("Internal error.")
                pass
            except Exception as unknown_error:
                logger.error(unknown_error)
                errors.append("Internal error.")
                pass

    if len(errors) > 0:
        return {'headers': {**default_http_headers},
                'statusCode': 400,
                'body': json.dumps(errors)
                }
    else:
        return {'headers': {**default_http_headers},
                'statusCode': 200
                }
