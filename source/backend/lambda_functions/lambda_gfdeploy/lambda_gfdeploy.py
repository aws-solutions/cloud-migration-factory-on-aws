#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from __future__ import print_function
import json
import os
from policy import MFAuth

import cmf_boto
from cmf_utils import cors, default_http_headers

application = os.environ['application']
environment = os.environ['environment']
servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)
waves_table_name = '{}-{}-waves'.format(application, environment)
servers_table = cmf_boto.resource('dynamodb').Table(servers_table_name)
apps_table = cmf_boto.resource('dynamodb').Table(apps_table_name)
waves_table = cmf_boto.resource('dynamodb').Table(waves_table_name)


def get_wave_name(waves, body):
    wave_name = ''
    for wave in waves:
        if str(wave['wave_id']) == body['waveid']:
            wave_name += extract_alnum(wave['wave_name'])
    return wave_name


def extract_alnum(input_str):
    alnum_str = ''
    for character in input_str:
        if character.isalnum():
            alnum_str += character
    return alnum_str


def extract_numeric(input_str):
    num_str = ''
    for character in input_str:
        if character.isnumeric():
            num_str += character
    return num_str


def process_app(app, body, context, wave_name, stack_result_set):
    if 'wave_id' in app and str(app['wave_id']) == body['waveid']:
        app_name = extract_alnum(app['app_name'])
        print('App Name :' + app_name)

        app_id = extract_alnum(app['app_id'])
        print('App Id :' + app_id)

        account_id = extract_numeric(app['aws_accountid'])

        # AWS Account Id to Create S3 Path
        aws_account_id = context.invoked_function_arn.split(":")[4]

        gfbuild_bucket = "{}-{}-{}-gfbuild-cftemplates".format(
            application, environment, aws_account_id)
        print('S3 Bucket to Load Cloud formation Templates' + gfbuild_bucket)

        # S3 path and Json File
        s3_path = account_id + '/' + wave_name + '/CFN_Template_' + app_id + '_' + app_name + '.yaml'
        print('S3 Path Along with JSON File:' + s3_path)

        # Later Enchancement to deploy the stack
        template_url = 'https://' + gfbuild_bucket + '.s3.amazonaws.com/' + s3_path
        s3 = cmf_boto.client('s3')
        try:
            result = s3.get_bucket_policy(Bucket=gfbuild_bucket)
            data = json.loads(result['Policy'])
            totalstatements = len(data['Statement'])
        except Exception:
            totalstatements = 0
            data = {"Statement": []}

        object_permission = {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::123456:root"
            },
            "Action": ["s3:GetObject", "s3:GetObjectVersion"],
            "Resource": "arn:aws:s3:::s3bcucket/*"
        }

        i = 0
        accountarnval = 'arn:aws:iam::' + account_id + ':root'
        s3bucketobjects = 'arn:aws:s3:::' + gfbuild_bucket + '/*'

        accountexists = 'No'

        while i < totalstatements:
            if (data['Statement'][i]['Principal']['AWS'] == accountarnval):
                accountexists = 'Yes'
            i = i + 1

        if accountexists == 'No':
            data['Statement'].append(object_permission)
            data['Statement'][totalstatements]['Principal']['AWS'] = accountarnval
            data['Statement'][totalstatements]['Resource'] = s3bucketobjects
            bucket_policy = json.dumps(data)
            print(bucket_policy)

            # Set the new policy
            s3.put_bucket_policy(Bucket=gfbuild_bucket, Policy=bucket_policy)

        print(data)

        stack_result = launch_stack(template_url, app_id, app_name, account_id)
        stack_result_set.append(stack_result)


def extract_stack_result_set_error(stack_result_set):
    for stackresult in stack_result_set:
        if stackresult is not None and "ERROR" in stackresult:
            return stackresult


def process_servers(servers):
    for server in servers:
        if "app_id" in server and "r_type" in server:
            print(server['r_type'].upper())
            if server['r_type'].upper() == 'REPLATFORM':
                # update
                server_response = servers_table.get_item(Key={'server_id': server['server_id']})
                server_item = server_response['Item']
                server_item['migration_status'] = 'CF Deployment Submitted'
                servers_table.put_item(Item=server_item)


def lambda_handler(event, context):

    # Verify user has access to run ec2 replatform functions.
    auth = MFAuth()
    auth_response = auth.get_user_resource_creation_policy(event, 'EC2')
    if auth_response['action'] != 'allow':
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': json.dumps(auth_response)}

    stack_result_set = []

    try:
        body = json.loads(event['body'])
        if 'waveid' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'waveid is required'}
        if 'accountid' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'Target AWS Account Id is required'}
    except Exception as e:
        print(e)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    try:
        # Read Apps Dynamo DB Table
        getapp = scan_dynamodb_table('app')
        msgapp= 'Unable to Retrieve Data from Dynamo DB App Table'
        if getapp is not None and "ERROR" in getapp:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body':msgapp }

        apps = sorted(getapp, key = lambda i: i['app_name'])

        # Read Waves Dynamo DB Table
        getwave = scan_dynamodb_table('wave')
        msgwave= 'Unable to Retrieve Data from Dynamo DB Wave Table'
        if getwave is not None and "ERROR" in getwave:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msgwave}

        waves = sorted(getwave, key = lambda i: i['wave_name'])


        getserver = scan_dynamodb_table('server')

        msgserver= 'Unable to Retrieve Data from Dynamo DB Server Table'
        if getserver is not None and "ERROR" in getserver:
             return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msgserver}

        servers = sorted(getserver, key = lambda i: i['server_name'])

        # Get Wave name
        wave_name = get_wave_name(waves, body)

        # App Table Attributes for S3 Path Generation

        for app in apps:
            process_app(app, body, context, wave_name, stack_result_set)

        stack_error = extract_stack_result_set_error(stack_result_set)
        if stack_error is not None:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': stack_error}

        process_servers(servers)
        msg = 'EC2 Deployment has been completed'
        print(msg)

        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': msg}

    except Exception as e:

        print('Lambda Handler Main Function Failed' + str(e))
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'Lambda Handler Main Function Failed with error : '+str(e)}


# Launch Stack based on Cloud Formation template Generate , It's Future Enhancement , not used at the moment
def launch_stack(template_url, app_id, app_name, target_account_id):
    # try:

    sts_client = cmf_boto.client('sts')
    role_arn_value = "arn:aws:iam::" + target_account_id + ":role/Factory-Replatform-EC2Deploy"
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn_value,
        RoleSessionName="AssumeRoleSessionMFReplatform"
        )
    credentials = assumed_role_object['Credentials']
    cfn = cmf_boto.client(
        'cloudformation',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
        )
    stack_name = 'Create-EC2-Servers-for-App-Id-' + app_id + app_name
    capabilities = ['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND','CAPABILITY_NAMED_IAM']
    stackdata = cfn.create_stack(
        StackName=stack_name,
        DisableRollback=True,
        TemplateURL=template_url,
        Capabilities=capabilities
        )
    return stackdata
    # except Exception as e:
        # print( "ERROR: Cloud Formation Stack Creation Failed with Error: " + str(e) )
        # return "ERROR: Cloud Formation Stack Creation Failed with Error: " + str(e)

#Pagination for DDB table scan


def scan_dynamodb_table(datatype):
    try:

        if datatype == 'server':
            response = servers_table.scan(ConsistentRead=True)
        elif datatype == 'app':
            response = apps_table.scan(ConsistentRead=True)
        elif datatype == 'wave':
            response = waves_table.scan(ConsistentRead=True)
        scan_data = response['Items']
        while 'LastEvaluatedKey' in response:
            print("Last Evaluate key is   " + str(response['LastEvaluatedKey']))
            if datatype == 'server':
                response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
            elif datatype == 'app':
                response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
            elif datatype == 'wave':
                response = waves_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
            scan_data.extend(response['Items'])
        return(scan_data)

    except Exception as e:
        print( "ERROR: Unable to retrieve the data from Dynamo DB table: " + str(e))
        return "ERROR: Unable to retrieve the data from Dynamo DB table: " + str(e)
