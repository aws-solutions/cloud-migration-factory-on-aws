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


import os
import boto3
import re
import sys
import requests

import simplejson as json


from jose import jwt, JWTError
from boto3.dynamodb.conditions import Key, Attr

class HttpVerb:
    GET     = "GET"
    POST    = "POST"
    PUT     = "PUT"
    PATCH   = "PATCH"
    HEAD    = "HEAD"
    DELETE  = "DELETE"
    OPTIONS = "OPTIONS"
    ALL     = "*"

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
    stage = "*"
    """The name of the stage used in the policy. By default this is set to '*'"""

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
            self.stage + "/" +
            verb + "/" +
            resource)

        if effect.lower() == "allow":
            self.allowMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
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
            'principalId' : self.principalId,
            'policyDocument' : {
                'Version' : self.version,
                'Statement' : []
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
        stage_table_name = '{}-{}-stage'.format(application, environment)

        self.role_table = boto3.resource('dynamodb').Table(roles_table_name)
        self.stage_table = boto3.resource('dynamodb').Table(stage_table_name)
        self.region=os.environ['region']
        self.userpool=os.environ['userpool']
        self.clientid=os.environ['clientid']

    def get_claims(self, aws_region, aws_user_pool, token, audience=None):
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


    def getAdminResoursePolicy(self, event):
        region=os.environ['region']
        userpool=os.environ['userpool']
        clientid=os.environ['clientid']

        token = event['authorizationToken']
        claims = self.get_claims(region, userpool, token, clientid)
        if claims.get('token_use') != 'id':
            raise ValueError('Not an ID Token')
        arn = event['methodArn'].split(':')
        apigatwayArn = arn[5].split('/')
        print(arn)
        print(apigatwayArn)

        email = claims.get('email')
        group = claims.get('cognito:groups')
        principalId = claims.get('sub')
        print('email ' + email)

        print('principalId ' + principalId)

        awsAccountId = arn[4]
        print('awsAccountId ' + awsAccountId)

        policy = AuthPolicy(principalId, awsAccountId)
        policy.restApiId = apigatwayArn[0]
        policy.region = arn[3]
        policy.stage = apigatwayArn[1]

        print('restApiId = ' + apigatwayArn[0])
        print('region = ' + arn[3])
        print('stage = ' + apigatwayArn[1])

        method = apigatwayArn[2]
        print ('method = ' + method)
        apitype = apigatwayArn[3]
        print ('apitype = ' + apitype)
        path = "/" + "/".join(apigatwayArn[3:])
        print("path" + path)

        if(apitype == 'admin'):
            print('I am in Admin API')
            if group is not None:
                check = False
                for g in group:
                   if 'admin' in g:
                      check = True
                if check == False:
                   print('Denying the access')
                   policy.denyAllMethods()
                else:
                   print('Allowing the access')
                   policy.allowMethod(method, path)
            else:
                print('Denying the access because there is no groups')
                policy.denyAllMethods()
        if(apitype == 'login'):
            print('I am in login API')
            if group is not None:
                check = False
                for g in group:
                   if 'admin' in g:
                      check = True
                if check == False:
                   print('Denying the access')
                   policy.denyAllMethods()
                else:
                   print('Allowing the access')
                   policy.allowMethod(method, path)
            else:
                print('Denying the access because there is no groups')
                policy.denyAllMethods()

        # Finally, build the policy
        authResponse = policy.build()

        # new! -- add additional key-value pairs associated with the authenticated principal
        # these are made available by APIGW like so: $context.authorizer.<key>
        # additional context is cached
        context = {
            "key": "Not assigned to the group admin"
        }
        # context['arr'] = ['foo'] <- this is invalid, APIGW will not accept it
        # context['obj'] = {'foo':'bar'} <- also invalid

        authResponse['context'] = context
        return authResponse




    def aws_key_dict(self, aws_region, aws_user_pool):

        aws_data = requests.get(
            self.pool_url(aws_region, aws_user_pool) + '/.well-known/jwks.json'
        )
        aws_jwt = json.loads(aws_data.text)
        result = {}
        for item in aws_jwt['keys']:
            result[item['kid']] = item

        return result


    def getUserResourceCrationPolicy(self,event):
        try:
            event['requestContext']['authorizer']['claims']
        except KeyError as error:
            return {
                'action': "deny",
                'cause': "Request is not Authenticated",
            }


        try:
            event['requestContext']['authorizer']['claims']['cognito:groups']
        except KeyError as error:
            return {
                'action': "deny",
                'cause': "User is not assigned to any group. Access denied.",
            }
        groupidentity = event['requestContext']['authorizer']['claims']['cognito:groups']
        #hard coding the staging_id
        stage_id = '1'
        rolelist = self.role_table.scan()
        stages = self.stage_table.scan()
        userStageList = []
        print("******groupidentity********")
        print(groupidentity)
        print(rolelist['Items'])
        for item in rolelist['Items']:
            for group in item['groups']:
                if(group['group_name'] in groupidentity):
                    for stage in stages['Items']:
                        if stage['stage_id'] not in userStageList:
                           userStageList.append(stage['stage_id'])
        print("*****userStageList********")
        print(userStageList)
        if(stage_id not in userStageList):
            return {
                'action': "deny",
                'cause': "User does not have permission to create or delete the resource. You need to have stage id 1 assigned to create this resource."
            }
        else:
            return {
                'action': "allow",
                'cause': "User has permission to create the resource"
            }


    def getUserAttributePolicy(self, event):
        try:
            event['requestContext']['authorizer']['claims']
        except KeyError as error:
            return {
                'action': "deny",
                'cause': "Request is not Authenticated",
            }
        body = json.loads(event['body'])
        attrList = body.keys()
        if(len(attrList) == 0):
            return {
                'action': "deny",
                'cause': "There are no attributes to update",
            }

        try:
            event['requestContext']['authorizer']['claims']['cognito:groups']
        except KeyError as error:
            return {
                'action': "deny",
                'cause': "User is not assigned to any group. Access denied.",
            }
        groupidentity = event['requestContext']['authorizer']['claims']['cognito:groups']
        userStageList = []
        accessAllowedAttrList = []
        accessDeniedAttrList = []
        userAllowedAttributes = []

        rolelist = self.role_table.scan()
        stages = self.stage_table.scan()
        print("******groupidentity********")
        print(groupidentity)
        print(rolelist['Items'])
        for item in rolelist['Items']:
            for group in item['groups']:
                if(group['group_name'] in groupidentity):
                    for stage in stages['Items']:
                        if stage['stage_id'] not in userStageList:
                           userStageList.append(stage['stage_id'])

        print('userStageList')
        print(userStageList)

        stageAttributesList =  self.stage_table.scan()
        for stageAttribute in stageAttributesList['Items']:
            if 'attributes' in stageAttribute and stageAttribute['stage_id'] in userStageList:
                    for attr in stageAttribute['attributes']:
                        if 'read_only' not in attr or attr['read_only'] != True:
                            userAllowedAttributes.append(attr['attr_name'])

        print('attrList')
        print(attrList)
        print('userAllowedAttributes')
        print(userAllowedAttributes)

        for attr in attrList:
            if(attr in userAllowedAttributes):
                accessAllowedAttrList.append(attr)
            else:
                accessDeniedAttrList.append(attr)

        if(len(accessDeniedAttrList) > 0):
            errorMsg = 'You do not have permission to update attributes '  + ': ' + ",".join(accessDeniedAttrList)
            return {
                'action': "deny",
                'cause': errorMsg
            }

        if(len(accessAllowedAttrList) > 0):
            sucessMsg = 'You have permission to update attributes '+  ': ' + ",".join(accessAllowedAttrList)
            return {
                'action': "allow",
                'cause': sucessMsg
            }
