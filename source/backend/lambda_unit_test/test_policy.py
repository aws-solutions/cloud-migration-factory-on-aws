#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import logging
import os
import json
import boto3
import time
from jose import jwt
from moto import mock_dynamodb
from unittest import TestCase, mock
from test_common_utils import default_mock_os_environ
import test_common_utils

# # This is to get around the relative path import issue.
# # Absolute paths are being used in this file after setting the root directory
import sys  
from pathlib import Path
file = Path(__file__).resolve()  
package_root_directory = file.parents [1]  
sys.path.append(str(package_root_directory))  
sys.path.append(str(package_root_directory)+'/lambda_layers/lambda_layer_policy/python/')

# Set log level
loglevel = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger(__name__)

mock_os_environ = {
    **default_mock_os_environ,
    'userpool': 'testuserpool',
    'clientid': 'testclientid'
}

@mock.patch.dict('os.environ', mock_os_environ)
@mock_dynamodb
class PolicyTestCase(TestCase):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self) -> None:
        from lambda_layers.lambda_layer_policy.python.policy import MFAuth, AuthPolicy
        import lambda_role
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_policies(
            self.ddb_client,
            lambda_role.policies_table_name,
            data_file_name = "../../lambda_functions/lambda_defaultschema/default_policies.json")
        test_common_utils.create_and_populate_roles(self.ddb_client, lambda_role.roles_table_name)
        self.auth = MFAuth()
        self.authPolicy = AuthPolicy("test_principal_id", "test_account_id")
        self.email = "test@example.com"
        self.method = "GET"
        self.path = "//request"
        self.admin_api_type = "admin"
        self.login_api_type = "login"
        self.put_event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "email": self.email,
                        "cognito:groups": [
                            "admin",
                            "readonly"
                        ],
                        "cognito:username": "testuser"
                    }
                }
            },
            "httpMethod": "PUT"
        }
        self.post_event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "email": self.email,
                        "cognito:groups": [
                            "admin",
                            "user"
                        ],
                        "cognito:username": "testuser"
                    }
                }
            },
            "httpMethod": "POST"
        }
        self.delete_event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "email": self.email,
                        "cognito:groups": [
                            "admin",
                            "user"
                        ],
                        "cognito:username": "testuser"
                    }
                }
            },
            "httpMethod": "DELETE"
        }
        self.put_event_having_body = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "email": self.email,
                        "cognito:groups": [
                            "admin",
                            "readonly"
                        ],
                        "cognito:username": "testuser"
                    }
                }
            },
            "httpMethod": "PUT",
            "pathParameters": {
                "schema_name": "application"
            },
            "body": '{"event": "PUT", "name": "unittest", "update": {"name": "unittest", "type": "list", '
                              '"description": "test description"}}'
        }


    def tearDown(self):
        """
        Delete database resource and mock table
        """
        import lambda_role
        print("Tearing down")
        self.ddb_client.delete_table(TableName=lambda_role.policies_table_name)
        self.ddb_client.delete_table(TableName=lambda_role.roles_table_name)
        self.dynamodb = None
        print("Teardown complete")


    def test_get_authorization_token_with_authorization_token(self):
        log.info("Testing policy: get_authorization_token with authorizationToken")
        event = {
            "type":"TOKEN",
            "authorizationToken":"xxx"
        }
        response = self.auth.get_authorization_token(event)
        print("Response: ", response)
        expected_response = "xxx"
        self.assertEqual(response, expected_response)


    def test_get_authorization_toke_with_upper_case_authorization_in_headers(self): 
        log.info("Testing policy: get_authorization_token with upper case 'A' Authorization in headers")
        event = {
            "type": "TOKEN",
            "headers": {
                    "Authorization": "xxx"
                }
        }
        response = self.auth.get_authorization_token(event)
        print("Response: ", response)
        expected_response = "xxx"
        self.assertEqual(response, expected_response)

    
    def test_get_authorization_toke_with_lower_case_authorization_in_headers(self): 
        log.info("Testing policy: get_authorization_token with lower case 'a' authorization in headers")
        event = {
            "type": "TOKEN",
            "headers": {
                    "authorization": "xxx"
                }
        }
        response = self.auth.get_authorization_token(event)
        print("Response: ", response)
        expected_response = "xxx"
        self.assertEqual(response, expected_response)


    def test_get_authorization_toke_without_authorization_token(self):  
        log.info("Testing policy: get_authorization_token without authorization token")
        event = {
            "type": "TOKEN",
            "headers": {}
        }
        response = self.auth.get_authorization_token(event)
        print("Response: ", response)
        expected_response = None
        self.assertEqual(response, expected_response)


    def test_get_access_token_with_upper_case_authorization_in_headers(self): 
        log.info("Testing policy: get_access_token with upper case 'A' Authorization-Access in headers")
        event = {
            "type": "TOKEN",
            "headers": {
                    "Authorization-Access": "xxx"
                }
        }
        response = self.auth.get_access_token(event)
        print("Response: ", response)
        expected_response = "xxx"
        self.assertEqual(response, expected_response)


    def test_get_access_token_with_lower_case_authorization_in_headers(self): 
        log.info("Testing policy: get_access_token with lower case 'a' authorization-access in headers")
        event = {
            "type": "TOKEN",
            "headers": {
                    "authorization-access": "xxx"
                }
        }
        response = self.auth.get_access_token(event)
        print("Response: ", response)
        expected_response = "xxx"
        self.assertEqual(response, expected_response)


    def test_get_access_token_without_token(self): 
        log.info("Testing policy: get_access_token without token")
        event = {
            "type": "TOKEN",
            "headers": {}
        }
        response = self.auth.get_access_token(event)
        print("Response: ", response)
        expected_response = None
        self.assertEqual(response, expected_response)


    def test_add_methods_for_admin_api_with_admin_group(self):
        log.info("Testing policy: add_methods_for_admin_api with admin group")
        group = ["admin", "user"]
        self.auth.add_methods_for_admin_api(
            self.admin_api_type, group, self.email, self.authPolicy, self.method, self.path)
        count = len(self.authPolicy.allow_methods)
        self.assertGreater(count, 0)


    def test_add_methods_for_admin_api_without_admin_group(self):
        log.info("Testing policy: add_methods_for_admin_api without admin group")
        group = ["other", "user"]
        self.auth.add_methods_for_admin_api(
            self.admin_api_type, group, self.email, self.authPolicy, self.method, self.path)
        count = len(self.authPolicy.deny_methods)
        self.assertGreater(count, 0)

    def test_add_methods_for_admin_api_without_any_group(self):
        log.info("Testing policy: add_methods_for_admin_api without any group")
        group = None
        self.auth.add_methods_for_admin_api(
            self.admin_api_type, group, self.email, self.authPolicy, self.method, self.path)
        count = len(self.authPolicy.deny_methods)
        self.assertGreater(count, 0)


    def test_add_methods_for_login_api_with_admin_group(self):
        log.info("Testing policy: add_methods_for_login_api with admin group")
        group = ["admin", "user"]
        self.auth.add_methods_for_login_api(
            self.login_api_type, group, self.email, self.authPolicy, self.method, self.path)
        count = len(self.authPolicy.allow_methods)
        self.assertGreater(count, 0)


    def test_add_methods_for_login_api_without_admin_group(self):
        log.info("Testing policy: add_methods_for_login_api without admin group")
        group = ["other", "user"]
        self.auth.add_methods_for_login_api(
            self.login_api_type, group, self.email, self.authPolicy, self.method, self.path)
        count = len(self.authPolicy.deny_methods)
        self.assertGreater(count, 0)

    def test_add_methods_for_login_api_without_any_group(self):
        log.info("Testing policy: add_methods_for_login_api without any group")
        group = None
        self.auth.add_methods_for_login_api(
            self.login_api_type, group, self.email, self.authPolicy, self.method, self.path)
        count = len(self.authPolicy.deny_methods)
        self.assertGreater(count, 0)

    def test_get_admin_resource_policy(self): 
        log.info("Testing policy: test_get_admin_resource_policy")
        kid = 'UPSZ26EORotKU88HFmnKO6Z1NgTVteSRMVwvIfqmpKA='
        token = json.dumps({
                'type': 'auth',
                'token':  jwt.encode({
                        'cmf': 'some_secret',
                        'exp': time.time(),
                        'aud': 'xxx',
                        'email': self.email,
                        'cognito:groups': ['admin','user']
                    }, 
                    'secret',
                    algorithm='HS256',
                    headers={
                        'kid': kid
                    },
                    access_token='xxx'
                )
            })
        event ={
            "type": "REQUEST",
            "authorizationToken":token,
            "methodArn": "arn:aws:execute-api:us-east-1:accountid:abcdef123/test/GET/request",
            "resource": "/request",
            "path": "/request",
            "httpMethod": "GET",
            "headers": {
                "authorization-access": "xxx"
            }
        }
        response = self.auth.get_admin_resource_policy(event)
        print("Response: ", response)
        expected_response = {
            "principalId": "",
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{
                    "Action": "execute-api:Invoke",
                    "Effect": "Deny",
                    "Resource": ["arn:aws:execute-api:us-east-1:accountid:abcdef123/test/*/*"]
                }]
            }
        }
        self.assertEqual(response, expected_response)


    def test_get_user_policy_list(self):
        log.info("Testing policy: get_user_policy_list")
        response = self.auth.get_user_policy_list(self.put_event)
        print("Response: ", response)
        expected_response = ['1', '2']
        self.assertEqual(response, expected_response)


    def test_get_user_resource_creation_policy_for_put_event(self):
        log.info("Testing policy: get_user_resource_creation_policy for put event")
        schema_name = 'app'
        response = self.auth.get_user_resource_creation_policy(self.put_event, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "allow",
            "cause": "User has permission to update the resource type application.",
            "user": {
                "userRef": "testuser",
                "email": "test@example.com"
            }
        }
        self.assertEqual(response, expected_response)


    def test_get_user_resource_creation_policy_for_post_event(self):
        log.info("Testing policy: get_user_resource_creation_policy for post event")
        schema_name = 'app'
        response = self.auth.get_user_resource_creation_policy(self.post_event, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "allow",
            "cause": "User has permission to create the resource type application.",
            "user": {
                "userRef": "testuser",
                "email": "test@example.com"
            }
        }
        self.assertEqual(response, expected_response)


    def test_get_user_resource_creation_policy_for_delete_event(self):
        log.info("Testing policy: get_user_resource_creation_policy for delete event")
        schema_name = 'app'
        response = self.auth.get_user_resource_creation_policy(self.delete_event, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "allow",
            "cause": "User has permission to delete the resource type application.",
            "user": {
                "userRef": "testuser",
                "email": "test@example.com"
            }
        }
        self.assertEqual(response, expected_response)


    def test_get_user_resource_creation_policy_for_delete_event_with_mismatching_schema(self):
        log.info("Testing policy: get_user_resource_creation_policy for delete event with mismatching schema")
        schema_name = 'app2'
        response = self.auth.get_user_resource_creation_policy(self.delete_event, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "deny",
            "cause": "User does not have permission to delete the resource type app2. Verify you have been assign a policy or role with this permission.",
            "user": {
                "userRef": "testuser",
                "email": "test@example.com"
            }
        }
        self.assertEqual(response, expected_response)


    def test_get_user_attribute_policy_without_event_body(self):
        log.info("Testing policy: get_user_attribute_policy for event without event body")
        schema_name = 'app'
        response = self.auth.get_user_attribute_policy(self.put_event, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "deny",
            "cause": "There are no attributes to update"
        }
        self.assertEqual(response, expected_response)


    def test_get_user_attribute_policy_with_event_body(self):
        log.info("Testing policy: get_user_attribute_policy for event having event body")
        schema_name = 'app'
        response = self.auth.get_user_attribute_policy(self.put_event_having_body, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "deny",
            "cause": "You do not have permission to update attributes : event,name,update",
            "user": {
                "userRef": "testuser",
                "email": "test@example.com"
            }
        }
        self.assertEqual(response, expected_response)


    def test_get_user_attribute_policy_without_cognito_user(self):
        log.info("Testing policy: get_user_attribute_policy for event having no cognito user name")
        schema_name = 'app'

        del self.put_event_having_body['requestContext']['authorizer']['claims']['cognito:username']
        response = self.auth.get_user_attribute_policy(self.put_event_having_body, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "deny",
            "cause": "Username not provided. Access denied."
        }
        self.assertEqual(response, expected_response)


    def test_get_user_attribute_policy_without_claims(self):
        log.info("Testing policy: get_user_attribute_policy for event having no claims")
        schema_name = 'app'

        del self.put_event_having_body['requestContext']['authorizer']['claims']
        response = self.auth.get_user_attribute_policy(self.put_event_having_body, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "deny",
            "cause": "Username not provided. Access denied."
        }
        self.assertEqual(response, expected_response)


    def test_get_user_attribute_policy_without_cognito_group(self):
        log.info("Testing policy: get_user_attribute_policy for event having no cognito group")
        schema_name = 'app'

        del self.put_event_having_body['requestContext']['authorizer']['claims']['cognito:groups']
        response = self.auth.get_user_attribute_policy(self.put_event_having_body, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "deny",
            "cause": "User is not assigned to any group. Access denied."
        }
        self.assertEqual(response, expected_response)


    def test_get_user_attribute_policy_without_email(self):
        log.info("Testing policy: get_user_attribute_policy for event having no email")
        schema_name = 'app'

        del self.put_event_having_body['requestContext']['authorizer']['claims']['email']
        response = self.auth.get_user_attribute_policy(self.put_event_having_body, schema_name)
        print("Response: ", response)
        expected_response = {
            "action": "deny",
            "cause": "Email address not provided. Access denied."
        }
        self.assertEqual(response, expected_response)