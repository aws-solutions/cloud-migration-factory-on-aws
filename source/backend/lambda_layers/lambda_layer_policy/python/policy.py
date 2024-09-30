#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import base64
import os
import boto3
import re
import requests
import simplejson as json
import jwt
from jwt import PyJWKClient
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)  # //NOSONAR Basic configuration doesn't pose security risk
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class AtHashValidationFailed(Exception):
    def __init__(self, message="at_hash validation failed."):
        self.message = message
        super().__init__(self.message)


class HttpVerb:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    HEAD = "HEAD"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    ALL = "*"


class AuthPolicy(object):
    aws_account_id = ""
    """The AWS account id the policy will be generated for. This is used to create the method ARNs."""
    principal_id = ""
    """The principal used for the policy, this should be a unique identifier for the end user."""
    version = "2012-10-17"
    """The policy version used for the evaluation. This should always be '2012-10-17'"""
    path_regex  = "^[/.a-zA-Z0-9-_\*]+$"
    """The regular expression used to validate resource paths for the policy"""

    """these are the internal lists of allowed and denied methods. These are lists
    of objects and each object has 2 properties: A resource ARN and a nullable
    conditions statement.
    the build method processes these lists and generates the appropriate
    statements for the final policy"""
    allow_methods = []
    deny_methods = []

    rest_api_id = "*"
    """The API Gateway API id. By default this is set to '*'"""
    region = "*"
    """The region where the API is deployed. By default this is set to '*'"""
    policy = "*"
    """The name of the policy used in the policy. By default this is set to '*'"""

    def __init__(self, principal, aws_account_id):
        self.aws_account_id = aws_account_id
        self.principal_id = principal
        self.allow_methods = []
        self.deny_methods = []

    def _add_method(self, effect, verb, resource, conditions):
        """Adds a method to the internal lists of allowed or denied methods. Each object in
        the internal list contains a resource ARN and a condition statement. The condition
        statement can be null."""
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resource_pattern = re.compile(self.path_regex )
        if not resource_pattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.path_regex )

        if resource.startswith("/"):
            resource = resource[1:]

        resource_arn = ("arn:aws:execute-api:" +
                       self.region + ":" +
                       self.aws_account_id + ":" +
                       self.rest_api_id + "/" +
                       self.policy + "/" +
                       verb + "/" +
                       resource)

        if effect.lower() == "allow":
            self.allow_methods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })
        elif effect.lower() == "deny":
            self.deny_methods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })

    def _get_empty_statement(self, effect):
        """Returns an empty statement object prepopulated with the correct action and the
        desired effect."""
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }

        return statement

    def _get_statement_for_effect(self, effect, methods):
        """This function loops over an array of objects containing a resourceArn and
        conditions statement and generates the array of statements for the policy."""
        statements = []

        if len(methods) > 0:
            statement = self._get_empty_statement(effect)

            for cur_method in methods:
                if cur_method['conditions'] is None or len(cur_method['conditions']) == 0:
                    statement['Resource'].append(cur_method['resourceArn'])
                else:
                    conditional_statement = self._get_empty_statement(effect)
                    conditional_statement['Resource'].append(cur_method['resourceArn'])
                    conditional_statement['Condition'] = cur_method['conditions']
                    statements.append(conditional_statement)

            statements.append(statement)

        return statements

    def allow_all_methods(self):
        """Adds a '*' allow to the policy to authorize access to all methods of an API"""
        self._add_method("Allow", HttpVerb.ALL, "*", [])

    def deny_all_methods(self):
        """Adds a '*' allow to the policy to deny access to all methods of an API"""
        self._add_method("Deny", HttpVerb.ALL, "*", [])

    def allow_method(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods for the policy"""
        self._add_method("Allow", verb, resource, [])

    def deny_method(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods for the policy"""
        self._add_method("Deny", verb, resource, [])

    def allow_method_with_conditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._add_method("Allow", verb, resource, conditions)

    def deny_method_with_conditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._add_method("Deny", verb, resource, conditions)

    def build(self):
        """Generates the policy document based on the internal lists of allowed and denied
        conditions. This will generate a policy with two main statements for the effect:
        one statement for Allow and one statement for Deny.
        Methods that includes conditions will have their own statement in the policy."""
        if ((self.allow_methods is None or len(self.allow_methods) == 0) and
            (self.deny_methods is None or len(self.deny_methods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId': self.principal_id,
            'policyDocument': {
                'Version': self.version,
                'Statement': []
            }
        }

        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Allow", self.allow_methods))
        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Deny", self.deny_methods))

        return policy


class MFAuth(object):

    def __init__(self):

        application = os.environ['application']
        environment = os.environ['environment']

        roles_table_name = '{}-{}-roles'.format(application, environment)
        policy_table_name = '{}-{}-policies'.format(application, environment)

        self.role_table = boto3.resource('dynamodb').Table(roles_table_name)
        self.policy_table = boto3.resource('dynamodb').Table(policy_table_name)
        self.region = os.environ['region']

    def get_claims(self, aws_region, aws_user_pool, token, audience=None, access_token=None):
        """ Given a token (and optionally an audience), validate and
        return the claims for the token
        """

        verify_url = self.pool_url(aws_region, aws_user_pool)

        optional_custom_headers = {"User-agent": "custom-user-agent"}
        jwks_client = PyJWKClient(verify_url + '/.well-known/jwks.json', headers=optional_custom_headers)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        kargs = {"issuer": verify_url, "algorithms": ['RS256']}
        if audience is not None:
            kargs["audience"] = audience

        if access_token is not None:
            kargs["access_token"] = access_token

        data = jwt.api_jwt.decode_complete(
            token,
            signing_key.key,
            **kargs
        )

        claims, header = data["payload"], data["header"]

        if access_token is not None and "at_hash" in claims:
            # Validate the at_hash against the access_token provided.
            alg_obj = jwt.get_algorithm_by_name(header["alg"])

            # compute at_hash
            digest = alg_obj.compute_hash_digest(access_token.encode())

            at_hash = base64.urlsafe_b64encode(digest[: (len(digest) // 2)])

            if not at_hash.startswith(claims['at_hash'].encode()):
                raise AtHashValidationFailed

        return claims

    def pool_url(self, aws_region, aws_user_pool):
        """ Create an Amazon cognito issuer URL from a region and pool id
        Args:
            aws_region (string): The region the pool was created in.
            aws_user_pool (string): The Amazon region ID.
        Returns:
            string: a URL
        """
        return (
            "https://cognito-idp.{}.amazonaws.com/{}".
            format(aws_region, aws_user_pool)
        )
    
    def get_authorization_token(self, event):
        if 'authorizationToken' in event:
            # support for TOKEN based authentication request from API GW.
            token = event['authorizationToken']
        else:
            # support for REQUEST based authentication request from API GW.
            if 'Authorization' in event['headers']:
                token = event['headers']['Authorization']
            elif 'authorization' in event['headers']:
                token = event['headers']['authorization']
            else:
                token = None

        return token

    def get_access_token(self, event):
        # Check to see if an access token has been provided and extract.
        # Checking for both capitalized and lower-case header is required in some environments.
        if 'authorization-access' in event['headers']:
            access = event['headers']['authorization-access']
        elif 'Authorization-Access' in event['headers']:
            access = event['headers']['Authorization-Access']
        else:
            access = None

        return access

    def add_methods_for_admin_api(self, api_type, group, email, policy, method, path):
        if (api_type == 'admin'):
            logger.info('Admin API Access')
            if group is not None:
                if 'admin' in group:
                    logger.info('Allowing Admin API Access, %s', email)
                    try:
                        policy.allow_method(method, path)
                    except NameError as e:
                        logger.info(f'Denying Admin API Access due to: {e} with user: {email}')
                        policy.deny_all_methods()
                else:
                    logger.info('Denying Admin API Access, %s', email)
                    policy.deny_all_methods()

            else:
                logger.info('Denying Admin API, as user is not a member of any Cognito groups: %s', email)
                policy.deny_all_methods()

    def add_methods_for_login_api(self, api_type, group, email, policy, method, path):
        if (api_type == 'login'):
            logger.info('Login API Access')
            if group is not None:
                if 'admin' in group:
                    logger.info('Allowing Login API Access, %s', email)
                    try:
                        policy.allow_method(method, path)
                    except NameError as e:
                        logger.info(f'Denying Admin API Access due to: {e} with user: {email}')
                        policy.deny_all_methods()
                else:
                    logger.info('Denying Login API Access: %s', email)
                    policy.deny_all_methods()
            else:
                logger.info('Denying Login API, as user is not a member of any Cognito groups: %s', email)
                policy.deny_all_methods()

    def get_admin_resource_policy(self, event):
        region = os.environ['region']
        userpool = os.environ['userpool']
        clientid = os.environ['clientid']

        token = self.get_authorization_token(event)

        access = self.get_access_token(event)

        arn = event['methodArn'].split(':')
        apigateway_arn = arn[5].split('/')
        logger.debug('API Gateway ARN: %s', arn)

        aws_account_id = arn[4]

        policy = AuthPolicy('', aws_account_id)
        policy.rest_api_id = apigateway_arn[0]
        policy.region = arn[3]
        policy.policy = apigateway_arn[1]

        method = apigateway_arn[2]
        apitype = apigateway_arn[3]

        try:
            claims = self.get_claims(region, userpool, token, clientid, access_token=access)
        except Exception as claim_error:
            logger.error('Denying Admin API Access, Claims Error, %s', claim_error)
            policy.deny_all_methods()
            # Build the policy
            auth_response = policy.build()
            return auth_response

        if claims.get('token_use') != 'id':
            raise ValueError('Not an ID Token')

        email = claims.get('email')
        group = claims.get('cognito:groups')  # //NOSONAR It is fine to repeat cognito:groups string as a json key name
        principal_id = claims.get('sub')
        policy.principal_id = principal_id
        logger.info('Cognito User email: %s', email)
        logger.debug('Cognito User principalId: %s', principal_id)

        path = "/" + "/".join(apigateway_arn[3:])

        self.add_methods_for_admin_api(
            apitype, group, email, policy, method, path)
        self.add_methods_for_login_api(
            apitype, group, email, policy, method, path)

        # Finally, build the policy
        auth_response = policy.build()

        return auth_response


    def get_user_policy(self, event):
        group_identity = event['requestContext']['authorizer']['claims']['cognito:groups']
        role_list = self.role_table.scan()

        user_policy_list = []
        logger.debug(role_list['Items'])
        logger.debug(group_identity)
        for item in role_list['Items']:
            for group in item['groups']:
                if (group['group_name'] in group_identity):
                    for policy in item['policies']:
                        if policy['policy_id'] not in user_policy_list:
                            user_policy_list.append(policy['policy_id'])
        user = {
            'userRef': event['requestContext']['authorizer']['claims']['cognito:username'], #NOSONAR It is fine to repeat cognito:username string as a json key name
            'email': event['requestContext']['authorizer']['claims']['email']
        }

        logger.debug('User policies: %s', user_policy_list)
        return user_policy_list, user

    def set_access_level_for_schema(self, schema, schema_name, schema_action, allow_access):
        is_matching_schema_found = False
        
        # Schema is matching, set access level.
        if schema.get('schema_name') == schema_name:
            if schema_action and schema.get(schema_action) == True:
                is_matching_schema_found = True
                allow_access = True
            
        return is_matching_schema_found, allow_access

    def get_access_level_for_schema(self, event, policy, schema_name, allow_access):
        method_schema_dict ={
            "PUT": "update",
            "POST": "create",
            "DELETE": "delete"}
        
        for schema in policy['entity_access']:
            # Set access level for matching schema, if found.
            is_matching_schema_found, allow_access = self.set_access_level_for_schema(
                    schema,
                    schema_name,
                    method_schema_dict.get(event['httpMethod']),
                    allow_access)
            
            if is_matching_schema_found == True:
                break

        return allow_access

    def get_allow_access(self, event, user_policy_list, schema_name):
        policies = self.policy_table.scan()
        allow_access = False

        for policy in policies['Items']:
            for user_policy in user_policy_list:
                # Found policy match.
                if policy['policy_id'] == user_policy and 'entity_access' in policy:
                    allow_access = self.get_access_level_for_schema(
                        event, policy, schema_name, allow_access)
                    if allow_access:
                        break
            if allow_access:
                # Policy located, no need to check others, exit loop.
                break

        return allow_access

    def update_access_type_in_return_message(self, event, allow_access, schema_name, user):
        # Update access type string for return message.
        allow_access_type = 'unknown'
        if event['httpMethod'] == 'PUT':
            allow_access_type = 'update'
        if event['httpMethod'] == 'POST':
            allow_access_type = 'create'
        if event['httpMethod'] == 'DELETE':
            allow_access_type = 'delete'

        if allow_access:
            logger.info('%s: User has permission to ' + allow_access_type + ' the resource type ' + schema_name + '.',
                        event['requestContext']['authorizer']['claims']['cognito:username'])
            return {
                'action': "allow",
                'cause': "User has permission to " + allow_access_type + " the resource type " + schema_name + ".",
                'user': user
            }
        else:
            logger.error(
                '%s: User does not have permission to ' + allow_access_type + ' the resource type ' + schema_name + '. Verify you have been assign a policy or role with this permission.',
                event['requestContext']['authorizer']['claims']['cognito:username'])
            return {
                'action': "deny",
                'cause': "User does not have permission to " + allow_access_type + " the resource type " + schema_name + ". Verify you have been assign a policy or role with this permission.",
                'user': user
            }

    def get_user_resource_creation_policy(self, event, schema_name):

        #  Fix for change of app to application in schema.
        if schema_name == 'app':
            schema_name = 'application'

        try:
            event['requestContext']['authorizer']['claims']
        except KeyError as error:
            logger.error(f'Request is not Authenticated. Error: {error}')
            return {
                'action': "deny",
                'cause': "Request is not Authenticated",
            }

        try:
            event['requestContext']['authorizer']['claims']['cognito:groups']
        except KeyError as error:
            logger.error(f"{event['requestContext']['authorizer']['claims']['email']}"
                         ": User is not assigned to any Cognito group. Access denied."
                         " Error: {error}")
            return {
                'action': "deny",
                'cause': "User is not assigned to any group. Access denied.",
            }
        
        user_policy_list, user = self.get_user_policy(event)

        allow_access = self.get_allow_access(event, user_policy_list, schema_name)

        return_message = self.update_access_type_in_return_message(event, allow_access, schema_name, user)

        return return_message

    def get_user_policy_list(self, event):
        group_identity = event['requestContext']['authorizer']['claims']['cognito:groups']
        user_policy_list = []

        role_list = self.role_table.scan()
        logger.debug('Cognito User email: %s', event['requestContext']['authorizer']['claims']['email'])
        logger.info('Cognito Username: ' + event['requestContext']['authorizer']['claims']['cognito:username'])
        logger.debug('All Roles: %s', role_list['Items'])
        for item in role_list['Items']:
            for group in item['groups']:
                if (group['group_name'] in group_identity):
                    for policy in item['policies']:
                        if policy['policy_id'] not in user_policy_list:
                            user_policy_list.append(policy['policy_id'])

        return user_policy_list

    def create_user_allowed_attr_list(self, policy, schema_name, user_allowed_attr_list):
        for entity in policy['entity_access']:
            if 'attributes' in entity and entity['schema_name'] == schema_name:
                # Found schema in entity access list.
                for attr in entity['attributes']:
                    user_allowed_attr_list.append(attr['attr_name'])
                break  # No need to look further as found schema.

        return  user_allowed_attr_list

    def get_user_allowed_attr_list(self, policy_list, user_policy_list, schema_name):
        user_allowed_attr_list = []
        for policy in policy_list['Items']:
            if 'entity_access' in policy and policy['policy_id'] in user_policy_list:
                user_allowed_attr_list = self.create_user_allowed_attr_list(
                    policy, schema_name, user_allowed_attr_list)

        return user_allowed_attr_list
    
    def get_access_allowed_denied_list(self, attr_list, user_allowed_attr_list):
        access_allowed_attr_list = []
        access_denied_attr_list = []
        for attr in attr_list:
            if (attr in user_allowed_attr_list):
                access_allowed_attr_list.append(attr)
            else:
                access_denied_attr_list.append(attr)

        return access_allowed_attr_list, access_denied_attr_list

    def get_user_attribute_policy(self, event, schema_name):

        # Fix for change of app to application in schema.
        if schema_name == 'app':
            schema_name = 'application'

        try:
            event['requestContext']['authorizer']['claims']['cognito:username']
        except KeyError as error:
            logger.error(f'Username not provided. Access denied. Error: {error}')
            return {
                'action': "deny",
                'cause': "Username not provided. Access denied.",
            }

        try:
            event['requestContext']['authorizer']['claims']
        except KeyError as error:
            logger.error(f"{event['requestContext']['authorizer']['claims']['cognito:username']}"
                         " Request is not Authenticated. Error: {error}")
            return {
                'action': "deny",
                'cause': "Request is not Authenticated",
            }

        body = json.loads(event['body']) if event.get('body') else {}
        attr_list = body.keys()
        if (len(attr_list) == 0):
            logger.error('%s: There are no attributes to update',
                         event['requestContext']['authorizer']['claims']['cognito:username'])
            return {
                'action': "deny",
                'cause': "There are no attributes to update",
            }

        try:
            event['requestContext']['authorizer']['claims']['cognito:groups']
        except KeyError as error:
            logger.error(f"{event['requestContext']['authorizer']['claims']['cognito:username']}"
                         ": Cognito User is not assigned to any Cognito group. Access denied."
                         "  Error: {error}")
            return {
                'action': "deny",
                'cause': "User is not assigned to any group. Access denied.",
            }

        try:
            event['requestContext']['authorizer']['claims']['email']
        except KeyError as error:
            logger.error(f"{event['requestContext']['authorizer']['claims']['cognito:username']}"
                         ": Cognito Email address not provided. Access denied."
                         "  Error: {error}")
            return {
                'action': "deny",
                'cause': "Email address not provided. Access denied.",
            }

        user = {
            'userRef': event['requestContext']['authorizer']['claims']['cognito:username'],
            'email': event['requestContext']['authorizer']['claims']['email']
        }

        user_policy_list =  self.get_user_policy_list(event)

        policy_list = self.policy_table.scan()

        user_allowed_attr_list = self.get_user_allowed_attr_list(policy_list, user_policy_list, schema_name)

        logger.debug('%s Attributes requested: %s', event['requestContext']['authorizer']['claims']['cognito:username'],
                     attr_list)
        logger.debug('%s: Attributes allowed: %s', event['requestContext']['authorizer']['claims']['cognito:username'],
                     user_allowed_attr_list)

        access_allowed_attr_list, access_denied_attr_list = \
            self.get_access_allowed_denied_list(attr_list, user_allowed_attr_list)

        if (len(access_denied_attr_list) > 0):
            error_msg = 'You do not have permission to update attributes ' + ': ' + ",".join(access_denied_attr_list)
            logger.error('%s: Access Denied: User does not have permission to update: %s',
                         event['requestContext']['authorizer']['claims']['cognito:username'], access_denied_attr_list)
            return {
                'action': "deny",
                'cause': error_msg,
                'user': user
            }

        if (len(access_allowed_attr_list) > 0):
            success_msg = 'You have permission to update attributes ' + ': ' + ",".join(access_allowed_attr_list)
            logger.info('%s: Access Granted: User has permission to update: %s',
                        event['requestContext']['authorizer']['claims']['cognito:username'], access_allowed_attr_list)
            return {
                'action': "allow",
                'cause': success_msg,
                'user': user
            }
