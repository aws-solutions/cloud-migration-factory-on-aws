#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import json
from datetime import datetime
import uuid
from policy import MFAuth

import cmf_boto
from cmf_logger import logger
from cmf_utils import cors, default_http_headers

application = os.environ['application']
environment = os.environ['environment']
ssm_bucket = os.environ['ssm_bucket']
ssm_automation_document = os.environ['ssm_automation_document']

mf_userapi = os.environ['mf_userapi']
mf_loginapi = os.environ['mf_loginapi']
mf_vpce_id = os.getenv('mf_vpce_id')
mf_cognitouserpoolid = os.environ['userpool']
mf_region = os.environ['region']
mf_cognitouserpoolclientid = os.environ['clientid']

lambda_client = cmf_boto.client('lambda')

ssm = cmf_boto.client("ssm")
ec2 = cmf_boto.client('ec2')


def lambda_handler(event, _):
    logging_context = f"SSM: {event['httpMethod']}"
    logger.debug('Invocation: %s', logging_context)
    if event['httpMethod'] == 'GET':

        mi_list = get_cmf_automation_servers()

        return {'headers': {**default_http_headers},
                'body': json.dumps(mi_list)}

    elif event['httpMethod'] == 'POST':

        # Get record audit
        auth = MFAuth()
        auth_response = auth.get_user_resource_creation_policy(event, 'ssm_job')

        if auth_response['action'] == 'allow':

            create_response = create_automation_job(json.loads(event["body"]), auth_response)

            logger.debug(f"Invocation: {logging_context}, {json.dumps(create_response)}")

            return create_response

        else:
            error_msg = json.dumps(auth_response)
            logger.error(f"Invocation: {logging_context}, {error_msg}")
            return {'headers': {**default_http_headers},
                    'statusCode': 401,
                    'body': error_msg}


def is_cmf_automation_server_instance(ssm_managed_instance):
    if ssm_managed_instance['PingStatus'] == "Online" and ssm_managed_instance['ResourceType'] == 'ManagedInstance':
        tags = ssm.list_tags_for_resource(ResourceType='ManagedInstance',
                                          ResourceId=ssm_managed_instance['InstanceId'])
        if 'TagList' in tags and len(tags['TagList']) > 0:
                automation_tag = {}
                automation_tag['Key'] = 'role'
                automation_tag['Value'] = 'mf_automation'
                if automation_tag in tags['TagList']:
                    return True
    else:
        tags = ec2.describe_tags(Filters=[
            {
                'Name': 'resource-id',
                'Values': [ssm_managed_instance['InstanceId']]
            }
        ])
        if 'Tags' in tags and len(tags['Tags']) > 0:
                automation_tag = {
                    'Key': 'role',
                    'Value': 'mf_automation',
                    'ResourceType': 'instance',
                    'ResourceId': ssm_managed_instance['InstanceId']
                }
                if automation_tag in tags['Tags']:
                    return True

    return False

def get_cmf_automation_servers():
    ssm_managed_instances = []

    ssm_instance_types = ['ManagedInstance', 'EC2Instance']
    for ssm_instance_type in ssm_instance_types:
        paginator = ssm.get_paginator('describe_instance_information')
        page_iterator = paginator.paginate(
            Filters=[
                {
                    'Key': 'ResourceType',
                    'Values': [
                        ssm_instance_type],
                },
            ],
            PaginationConfig={
                # 'MaxItems': 100,
            }
        )

        for page in page_iterator:
            ssm_managed_instances.extend(page['InstanceInformationList'])

    return filter_cmf_automation_servers(ssm_managed_instances)


def filter_cmf_automation_servers(ssm_managed_instances):
    mi_list = []
    for ssm_managed_instance in ssm_managed_instances:
        if is_cmf_automation_server_instance(ssm_managed_instance):
            mi_list.append({
                "mi_id": ssm_managed_instance['InstanceId'],
                "online": (True if ssm_managed_instance['PingStatus'] == "Online" else False),
                "mi_name": (
                    ssm_managed_instance["ComputerName"] if 'ComputerName' in ssm_managed_instance else '')
            })

    return mi_list


def get_validation_errors(ssm_data):
    validation_errors = []

    if "jobname" not in ssm_data.keys():
        validation_errors.append('jobname')

    if "mi_id" not in ssm_data.keys():
        validation_errors.append('mi_id')

    if "script" not in ssm_data.keys():
        validation_errors.append('script')

    return validation_errors


def get_cmf_script(script_uuid, script_version, job_arguments):
    script_selected = None

    scripts_event = {
        'httpMethod': 'GET',
        'pathParameters': {
            'scriptid': script_uuid,
            'version': script_version
        }
    }

    scripts_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-scripts',
                                            InvocationType='RequestResponse',
                                            Payload=json.dumps(scripts_event))

    scripts_response_pl = scripts_response['Payload'].read()

    scripts = json.loads(scripts_response_pl)

    # Get body which contains the script item if found.
    scripts_list = json.loads(scripts['body'])

    for script in scripts_list:
        if script['package_uuid'] == script_uuid:
            script_selected = script
            # replace args with user provided data.
            script_selected['script_arguments'] = job_arguments
            return script_selected


def create_automation_job(ssm_data, auth_response):
    job_uuid = str(uuid.uuid4())

    if 'user' in auth_response:
        last_modified_by = auth_response['user']
        last_modified_timestamp = datetime.utcnow().isoformat()

    ssm_data["_history"] = {}
    ssm_data["_history"]["createdBy"] = last_modified_by
    ssm_data["_history"]["createdTimestamp"] = last_modified_timestamp

    ssm_data['uuid'] = job_uuid

    # Perform payload validation.
    validation_error = get_validation_errors(ssm_data)

    if len(validation_error) > 0:
        error_msg = "Request parameters missing: " + ",".join(validation_error)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': error_msg}

    # Build payload for SSM request.

    ssm_data["SSMId"] = ssm_data["mi_id"] + "+" + ssm_data["uuid"] + "+" + ssm_data["_history"][
        "createdTimestamp"]
    ssm_data['output'] = ''

    if mf_vpce_id != '':
        mf_vpce_id_with_hosted = mf_vpce_id
    else:
        mf_vpce_id_with_hosted = ''

    # Add MF endpoint details to payload.
    ssm_data['mf_endpoints'] = {
        'LoginApi': mf_loginapi,
        'UserApi': mf_userapi,
        'VpceId': mf_vpce_id_with_hosted,
        'UserPoolId': mf_cognitouserpoolid,
        'UserPoolClientId': mf_cognitouserpoolclientid,
        'Region': mf_region
    }

    # Default script version to 0 which will return the default version.
    script_version = '0'

    if 'script_version' in ssm_data["script"]:
        # User has chosen to override the script version.
        script_version = ssm_data["script"]["script_version"]

    try:

        script_selected = get_cmf_script(
            ssm_data["script"]["package_uuid"],
            script_version,
            ssm_data["script"]["script_arguments"]
        )

        ssm_data['script'] = script_selected

        # Check if script is found.
        if not script_selected:
            if script_version != '0':
                error_msg = "Invalid package uuid or version provided. '" + ssm_data["script"][
                    "package_uuid"] + ", version " + ssm_data["script"]["script_version"] + " ' does not exist."
            else:
                error_msg = "Invalid script uuid provided, using default version. UUID:'" + ssm_data["script"][
                    "package_uuid"] + "' does not exist."
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': error_msg}

        ''' SSM API call for remote execution '''
        response = ssm.start_automation_execution(  # API call to SSM Automation Document
            DocumentName=ssm_automation_document,  # Name of the automation document in SSM
            DocumentVersion='$LATEST',
            Parameters={  # Parameters that will be passed to the script file
                'bucketName': [ssm_bucket],
                'cmfInstance': [application],
                'cmfEnvironment': [environment],
                'payload': [json.dumps(ssm_data)],
                'instanceID': [ssm_data["mi_id"]],
            },
        )

        logger.info(f"SSM: POST: create_ssm_automation_job."
                    f" Job created, ExecutionID: {response['AutomationExecutionId']}")

        ssm_data['SSMAutomationExecutionId'] = response['AutomationExecutionId']

        jobs_event = {
            'payload': {
                'httpMethod': 'POST',
                'body': json.dumps(ssm_data)
            }
        }

        logger.debug(f"Invocation: SSM: POST: create_ssm_automation_job, {json.dumps(jobs_event)}")

        lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-jobs',
                             InvocationType='Event',
                             ClientContext='string',
                             Payload=json.dumps(jobs_event))

        return {'headers': {**default_http_headers},
                'body': json.dumps("SSMId: " + ssm_data["SSMId"])}
    except BaseException as err:
        logger.error(f"SSM: POST: create_ssm_automation_job, {err}")
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': str(err)}
