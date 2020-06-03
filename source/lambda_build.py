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

import json, boto3, logging, os
import requests

ec2_client = boto3.client('ec2')
ecs_client = boto3.client('ecs')

log = logging.getLogger()
log.setLevel(logging.INFO)

ECS_CLUSTER = os.getenv('ECS_CLUSTER')
ECS_TASK = os.getenv('ECS_TASK')
USER_API = os.getenv('USER_API')
ADMIN_API = os.getenv('ADMIN_API')
LOGIN_API = os.getenv('LOGIN_API')
TOOLS_API = os.getenv('TOOLS_API')
USER_POOL_ID = os.getenv('USER_POOL_ID')
APP_CLIENT_ID = os.getenv('APP_CLIENT_ID')
FRONTEND_BUCKET = os.getenv('FRONTEND_BUCKET')
SOURCE_BUCKET = os.getenv('SOURCE_BUCKET')
SOURCE_KEY = os.getenv('SOURCE_KEY')

SG = os.getenv('SG')
SUBNET = os.getenv('SUBNET')

def run_task(subnet, sg):
    session = boto3.session.Session()
    region = session.region_name

    response = ecs_client.run_task(
        cluster=ECS_CLUSTER,
        taskDefinition=ECS_TASK,
        overrides={
            'containerOverrides': [
                {
                    'name': 'factory-build',
                    'environment': [
                        {
                            'name': 'region',
                            'value': region
                        },
                        {
                            'name': 'user_api',
                            'value': USER_API
                        },
                        {
                            'name': 'admin_api',
                            'value': ADMIN_API
                        },
                        {
                            'name': 'login_api',
                            'value': LOGIN_API
                        },
                        {
                            'name': 'tools_api',
                            'value': TOOLS_API
                        },
                        {
                            'name': 'user_pool_id',
                            'value': USER_POOL_ID
                        },
                        {
                            'name': 'app_client_id',
                            'value': APP_CLIENT_ID
                        },
                        {
                            'name': 'frontend_bucket',
                            'value': FRONTEND_BUCKET
                        },
                        {
                            'name': 'source_bucket',
                            'value': SOURCE_BUCKET
                        },
                        {
                            'name': 'source_key',
                            'value': SOURCE_KEY
                        }
                    ]
                }
            ]
        },
        count=1,
        launchType='FARGATE',

        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': [
                    subnet,
                ],
                'securityGroups': [
                    sg
                ],
                'assignPublicIp': 'ENABLED'
            }
        }

    )


def get_default_vpc():
    try:
        response = ec2_client.describe_vpcs(
            Filters=[
                {
                    'Name': 'isDefault',
                    'Values': [
                        'true',
                    ]
                },
            ]
        )
        return response['Vpcs'][0]['VpcId']
    except Exception as e:
        print('ERROR: Default VPC does not exist')
        print(e)


def get_default_sg(vpc_id):
    try:
        response = ec2_client.describe_security_groups(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        vpc_id,
                    ]
                },
                {
                    'Name': 'group-name',
                    'Values': [
                        'default',
                    ]
                }
            ]
        )
        return response['SecurityGroups'][0]['GroupId']
    except Exception as e:
        print('ERROR: Default Security group does not exist')
        print(e)


def get_subnet(vpc_id):
    # Get first available subnet id
    try:
        response = ec2_client.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        vpc_id,
                    ]
                },
            ]
        )
        return response['Subnets'][0]['SubnetId']
    except Exception as e:
        print('ERROR: Get subnet Id failed')
        print(e)


def lambda_handler(event, context):

    try:
        log.info('Event:\n {}'.format(event))
        log.info('Contex:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            log.info('Create action')

            if SG == 'default' and SUBNET == 'default':
                vpc_id = get_default_vpc()
            else:
                vpc_id = ""

            if SG == 'default':
                if vpc_id == "":
                   print("ERROR: if you select default, both SG and Subnet must be default")
                sg = get_default_sg(vpc_id)
            else:
                sg = SG

            if SUBNET == 'default':
                if vpc_id == "":
                   print("ERROR: if you select default, both SG and Subnet must be default")
                subnet = get_subnet(vpc_id)
            else:
                subnet = SUBNET

            run_task(subnet, sg)

            status='SUCCESS'
            message='Initiated build process'

        elif event['RequestType'] == 'Update':
            log.info('Update action')

            if SG == 'default' and SUBNET == 'default':
                vpc_id = get_default_vpc()

            if SG == 'default':
                if vpc_id == "":
                   print("ERROR: if you select default, both SG and Subnet must be default")
                sg = get_default_sg(vpc_id)
            else:
                sg = SG

            if SUBNET == 'default':
                if vpc_id == "":
                   print("ERROR: if you select default, both SG and Subnet must be default")
                subnet = get_subnet(vpc_id)
            else:
                subnet = SUBNET

            run_task(subnet, sg)

            status='SUCCESS'
            message='No update required'

        elif event['RequestType'] == 'Delete':
            log.info('Delete action')
            status='SUCCESS'
            message='No deletion required'

        else:
            log.info('SUCCESS!')
            status='SUCCESS'
            message='Unexpected event received from CloudFormation'

    except Exception as e:
        log.info('FAILED!')
        log.info(e)
        status='FAILED'
        message='Exception during processing'

    response_data = {'Message' : message}
    response=respond(event, context, status, response_data, None)

    return {
        'Response' :response
    }

def respond(event, context, responseStatus, responseData, physicalResourceId):
    #Build response payload required by CloudFormation
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'Details in: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['Data'] = responseData

    #Convert json object to string and log it
    json_responseBody = json.dumps(responseBody)
    log.info('Response body: {}'.format(str(json_responseBody)))

    #Set response URL
    responseUrl = event['ResponseURL']

    #Set headers for preparation for a PUT
    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    #Return the response to the signed S3 URL
    try:
        response = requests.put(responseUrl,
        data=json_responseBody,
        headers=headers)
        log.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        log.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'