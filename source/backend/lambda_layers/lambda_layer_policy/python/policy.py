#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0



import os
import boto3
import re
import sys
import requests

import simplejson as json

from jose import jwt, JWTError
from boto3.dynamodb.conditions import Key, Attr
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
    awsAccountId = ""
    """The AWS account id the policy will be generated for. This is used to create the method ARNs."""
    principalId = ""
    """The principal used for the policy, this should be a unique identifier for the end user."""
    version = "2012-10-17"
    """The policy version used for the evaluation. This should always be '2012-10-17'"""
    pathRegex = "^[/.a-zA-Z0-9-\*]+$"
    """The regular expression used to validate resource paths for the policy"""

    """these are the internal lists of allowed and denied methods. These are lists
    of objects and each object has 2 properties: A resource ARN and a nullable
    conditions statement.
    the build method processes these lists and generates the approriate
    statements for the final policy"""
    allowMethods = []
    denyMethods = []

    restApiId = "*"
    """The API Gateway API id. By default this is set to '*'"""
    region = "*"
    """The region where the API is deployed. By default this is set to '*'"""
    policy = "*"
    """The name of the policy used in the policy. By default this is set to '*'"""

    def __init__(self, principal, awsAccountId):
        self.awsAccountId = awsAccountId
        self.principalId = principal
        self.allowMethods = []
        self.denyMethods = []

    def _addMethod(self, effect, verb, resource, conditions):
        """Adds a method to the internal lists of allowed or denied methods. Each object in
        the internal list contains a resource ARN and a condition statement. The condition
        statement can be null."""
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resourcePattern = re.compile(self.pathRegex)
        if not resourcePattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.pathRegex)

        if resource[:1] == "/":
            resource = resource[1:]

        resourceArn = ("arn:aws:execute-api:" +
                       self.region + ":" +
                       self.awsAccountId + ":" +
                       self.restApiId + "/" +
                       self.policy + "/" +
                       verb + "/" +
                       resource)

        if effect.lower() == "allow":
            self.allowMethods.append({
                'resourceArn': resourceArn,
                'conditions': conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                'resourceArn': resourceArn,
                'conditions': conditions
            })

    def _getEmptyStatement(self, effect):
        """Returns an empty statement object prepopulated with the correct action and the
        desired effect."""
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }

        return statement

    def _getStatementForEffect(self, effect, methods):
        """This function loops over an array of objects containing a resourceArn and
        conditions statement and generates the array of statements for the policy."""
        statements = []

        if len(methods) > 0:
            statement = self._getEmptyStatement(effect)

            for curMethod in methods:
                if curMethod['conditions'] is None or len(curMethod['conditions']) == 0:
                    statement['Resource'].append(curMethod['resourceArn'])
                else:
                    conditionalStatement = self._getEmptyStatement(effect)
                    conditionalStatement['Resource'].append(curMethod['resourceArn'])
                    conditionalStatement['Condition'] = curMethod['conditions']
                    statements.append(conditionalStatement)

            statements.append(statement)

        return statements

    def allowAllMethods(self):
        """Adds a '*' allow to the policy to authorize access to all methods of an API"""
        self._addMethod("Allow", HttpVerb.ALL, "*", [])

    def denyAllMethods(self):
        """Adds a '*' allow to the policy to deny access to all methods of an API"""
        self._addMethod("Deny", HttpVerb.ALL, "*", [])

    def allowMethod(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods for the policy"""
        self._addMethod("Allow", verb, resource, [])

    def denyMethod(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods for the policy"""
        self._addMethod("Deny", verb, resource, [])

    def allowMethodWithConditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._addMethod("Allow", verb, resource, conditions)

    def denyMethodWithConditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._addMethod("Deny", verb, resource, conditions)

    def build(self):
        """Generates the policy document based on the internal lists of allowed and denied
        conditions. This will generate a policy with two main statements for the effect:
        one statement for Allow and one statement for Deny.
        Methods that includes conditions will have their own statement in the policy."""
        if ((self.allowMethods is None or len(self.allowMethods) == 0) and
            (self.denyMethods is None or len(self.denyMethods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId': self.principalId,
            'policyDocument': {
                'Version': self.version,
                'Statement': []
            }
        }

        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Allow", self.allowMethods))
        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Deny", self.denyMethods))

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
        # header, _, _ = get_token_segments(token)
        header = jwt.get_unverified_header(token)
        kid = header['kid']

        verify_url = self.pool_url(aws_region, aws_user_pool)

        keys = self.aws_key_dict(aws_region, aws_user_pool)

        key = keys.get(kid)

        kargs = {"issuer": verify_url}
        if audience is not None:
            kargs["audience"] = audience

        if access_token is not None:
            kargs["access_token"] = access_token

        claims = jwt.decode(
            token,
            key,
            **kargs
        )
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

    def getAdminResourcePolicy(self, event):
        region = os.environ['region']
        userpool = os.environ['userpool']
        clientid = os.environ['clientid']

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

        # Check to see if an access token has been provided and extract.
        # Checking for both capitalized and lower-case header is required in some environments.
        if 'authorization-access' in event['headers']:
            access = event['headers']['authorization-access']
        elif 'Authorization-Access' in event['headers']:
            access = event['headers']['Authorization-Access']
        else:
            access = None

        arn = event['methodArn'].split(':')
        apigatwayArn = arn[5].split('/')
        logger.debug('API Gateway ARN: %s', arn)

        awsAccountId = arn[4]

        policy = AuthPolicy('', awsAccountId)
        policy.restApiId = apigatwayArn[0]
        policy.region = arn[3]
        policy.policy = apigatwayArn[1]

        method = apigatwayArn[2]
        apitype = apigatwayArn[3]

        try:
            claims = self.get_claims(region, userpool, token, clientid, access_token=access)
        except Exception as claim_error:
            logger.error('Denying Admin API Access, Claims Error, %s', claim_error)
            policy.denyAllMethods()
            # Build the policy
            authResponse = policy.build()
            return authResponse

        if claims.get('token_use') != 'id':
            raise ValueError('Not an ID Token')

        email = claims.get('email')
        group = claims.get('cognito:groups')
        principalId = claims.get('sub')
        policy.principalId = principalId
        logger.info('Cognito User email: %s', email)
        logger.debug('Cognito User principalId: %s', principalId)

        path = "/" + "/".join(apigatwayArn[3:])

        if (apitype == 'admin'):
            logger.info('Admin API Access')
            if group is not None:
                check = False
                for g in group:
                    if 'admin' in g:
                        check = True
                if check == False:
                    logger.info('Denying Admin API Access, %s', email)
                    policy.denyAllMethods()
                else:
                    logger.info('Allowing Admin API Access, %s', email)
                    policy.allowMethod(method, path)
            else:
                logger.info('Denying Admin API, as user is not a member of any Cognito groups: %s', email)
                policy.denyAllMethods()
        if (apitype == 'login'):
            logger.info('Login API Access')
            if group is not None:
                check = False
                for g in group:
                    if 'admin' in g:
                        check = True
                if check == False:
                    logger.info('Denying Login API Access: %s', email)
                    policy.denyAllMethods()
                else:
                    logger.info('Allowing Login API Access, %s', email)
                    policy.allowMethod(method, path)
            else:
                logger.info('Denying Login API, as user is not a member of any Cognito groups: %s', email)
                policy.denyAllMethods()

        # Finally, build the policy
        authResponse = policy.build()

        return authResponse

    def aws_key_dict(self, aws_region, aws_user_pool):

        aws_data = requests.get(
            self.pool_url(aws_region, aws_user_pool) + '/.well-known/jwks.json',
            timeout=30
        )
        aws_jwt = json.loads(aws_data.text)
        result = {}
        for item in aws_jwt['keys']:
            result[item['kid']] = item

        return result

    def getUserResourceCreationPolicy(self, event, schema_name):

        #  Fix for change of app to application in schema.
        if schema_name == 'app':
            schema_name = 'application'

        try:
            event['requestContext']['authorizer']['claims']
        except KeyError as error:
            logger.error('Request is not Authenticated.')
            return {
                'action': "deny",
                'cause': "Request is not Authenticated",
            }

        try:
            event['requestContext']['authorizer']['claims']['cognito:groups']
        except KeyError as error:
            logger.error('%s: User is not assigned to any Cognito group. Access denied.',
                         event['requestContext']['authorizer']['claims']['email'])
            return {
                'action': "deny",
                'cause': "User is not assigned to any group. Access denied.",
            }
        groupidentity = event['requestContext']['authorizer']['claims']['cognito:groups']
        # hard coding the staging_id
        policy_id = '1'
        rolelist = self.role_table.scan()

        userPolicyList = []
        logger.debug(rolelist['Items'])
        logger.debug(groupidentity)
        for item in rolelist['Items']:
            for group in item['groups']:
                if (group['group_name'] in groupidentity):
                    for policy in item['policies']:
                        if policy['policy_id'] not in userPolicyList:
                            userPolicyList.append(policy['policy_id'])
        user = {
            'userRef': event['requestContext']['authorizer']['claims']['cognito:username'],
            'email': event['requestContext']['authorizer']['claims']['email']
        }

        logger.debug('User policies: %s', userPolicyList)

        policies = self.policy_table.scan()
        allow_access = False

        for policy in policies['Items']:
            for userPolicy in userPolicyList:
                if policy['policy_id'] == userPolicy:
                    # Found policy match.
                    if 'entity_access' in policy:
                        for schema in policy['entity_access']:
                            if 'schema_name' in schema and schema_name == schema['schema_name']:
                                # Schema is matching, check access level.
                                if event['httpMethod'] == 'PUT':
                                    if 'update' in schema:
                                        if schema['update'] == True:
                                            allow_access = True
                                            break
                                if event['httpMethod'] == 'POST':
                                    if 'create' in schema:
                                        if schema['create'] == True:
                                            allow_access = True
                                            break
                                if event['httpMethod'] == 'DELETE':
                                    if 'delete' in schema:
                                        if schema['delete'] == True:
                                            allow_access = True
                                            break
                        if allow_access:
                            break
            if allow_access:
                # Policy located, no need to check others, exit loop.
                break

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

    def getUserAttributePolicy(self, event, schema_name):

        # Fix for change of app to application in schema.
        if schema_name == 'app':
            schema_name = 'application'

        try:
            event['requestContext']['authorizer']['claims']['cognito:username']
        except KeyError as error:
            logger.error('Username not provided. Access denied.')
            return {
                'action': "deny",
                'cause': "Username not provided. Access denied.",
            }

        try:
            event['requestContext']['authorizer']['claims']
        except KeyError as error:
            logger.error('%s Request is not Authenticated',
                         event['requestContext']['authorizer']['claims']['cognito:username'])
            return {
                'action': "deny",
                'cause': "Request is not Authenticated",
            }

        if 'body' in event and event['body']:
            body = json.loads(event['body'])
        else:
            body = {}
        attrList = body.keys()
        if (len(attrList) == 0):
            logger.error('%s: There are no attributes to update',
                         event['requestContext']['authorizer']['claims']['cognito:username'])
            return {
                'action': "deny",
                'cause': "There are no attributes to update",
            }

        try:
            event['requestContext']['authorizer']['claims']['cognito:groups']
        except KeyError as error:
            logger.error('%s: Cognito User is not assigned to any Cognito group. Access denied.',
                         event['requestContext']['authorizer']['claims']['cognito:username'])
            return {
                'action': "deny",
                'cause': "User is not assigned to any group. Access denied.",
            }

        try:
            event['requestContext']['authorizer']['claims']['email']
        except KeyError as error:
            logger.error('%s: Cognito Email address not provided. Access denied.',
                         event['requestContext']['authorizer']['claims']['cognito:username'])
            return {
                'action': "deny",
                'cause': "Email address not provided. Access denied.",
            }

        user = {
            'userRef': event['requestContext']['authorizer']['claims']['cognito:username'],
            'email': event['requestContext']['authorizer']['claims']['email']
        }

        groupidentity = event['requestContext']['authorizer']['claims']['cognito:groups']
        userPolicyList = []
        accessAllowedAttrList = []
        accessDeniedAttrList = []
        userAllowedAttributes = []

        rolelist = self.role_table.scan()
        logger.debug('Cognito User email: %s', event['requestContext']['authorizer']['claims']['email'])
        logger.info('Cognito Username: ' + event['requestContext']['authorizer']['claims']['cognito:username'])
        logger.debug('All Roles: %s', rolelist['Items'])
        for item in rolelist['Items']:
            for group in item['groups']:
                if (group['group_name'] in groupidentity):
                    for policy in item['policies']:
                        if policy['policy_id'] not in userPolicyList:
                            userPolicyList.append(policy['policy_id'])

        policyList = self.policy_table.scan()

        for policy in policyList['Items']:
            if 'entity_access' in policy and policy['policy_id'] in userPolicyList:
                for entity in policy['entity_access']:
                    if 'attributes' in entity and entity['schema_name'] == schema_name:
                        # Found schema in entity access list.
                        for attr in entity['attributes']:
                            userAllowedAttributes.append(attr['attr_name'])
                        break  # No need to look further as found schema.

        logger.debug('%s Attributes requested: %s', event['requestContext']['authorizer']['claims']['cognito:username'],
                     attrList)
        logger.debug('%s: Attributes allowed: %s', event['requestContext']['authorizer']['claims']['cognito:username'],
                     userAllowedAttributes)

        for attr in attrList:
            if (attr in userAllowedAttributes):
                accessAllowedAttrList.append(attr)
            else:
                accessDeniedAttrList.append(attr)

        if (len(accessDeniedAttrList) > 0):
            errorMsg = 'You do not have permission to update attributes ' + ': ' + ",".join(accessDeniedAttrList)
            logger.error('%s: Access Denied: User does not have permission to update: %s',
                         event['requestContext']['authorizer']['claims']['cognito:username'], accessDeniedAttrList)
            return {
                'action': "deny",
                'cause': errorMsg,
                'user': user
            }

        if (len(accessAllowedAttrList) > 0):
            sucessMsg = 'You have permission to update attributes ' + ': ' + ",".join(accessAllowedAttrList)
            logger.info('%s: Access Granted: User has permission to update: %s',
                        event['requestContext']['authorizer']['claims']['cognito:username'], accessAllowedAttrList)
            return {
                'action': "allow",
                'cause': sucessMsg,
                'user': user
            }
