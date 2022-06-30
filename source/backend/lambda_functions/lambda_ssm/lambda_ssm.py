import os
import boto3
import json
from datetime import datetime
import uuid
from policy import MFAuth
from botocore import config

if 'solution_identifier' in os.environ:
    solution_identifier= json.loads(os.environ['solution_identifier'])
    user_agent_extra_param = {"user_agent_extra":solution_identifier}
    boto_config = config.Config(**user_agent_extra_param)
else:
    boto_config = None

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}
application = os.environ['application']
environment = os.environ['environment']
ssm_bucket = os.environ['ssm_bucket']
ssm_automation_document = os.environ['ssm_automation_document']

mf_userapi = os.environ['mf_userapi']
mf_loginapi = os.environ['mf_loginapi']
mf_cognitouserpoolid = os.environ['userpool']
mf_region = os.environ['region']

lambda_client = boto3.client('lambda')

ssm = boto3.client("ssm", config=boto_config)
ec2 = boto3.client('ec2')

def lambda_handler(event, context):

    if event['httpMethod'] == 'GET':

        combined = []

        rtypes = ['ManagedInstance', 'EC2Instance']
        for rtype in rtypes:
            paginator = ssm.get_paginator('describe_instance_information')
            response_iterator = paginator.paginate(
                Filters=[
                    {
                        'Key': 'ResourceType',
                        'Values': [
                            rtype],
                    },
                        ],
                PaginationConfig={
                    # 'MaxItems': 100,
                }
            )
            combined.append(list(response_iterator))

        # get management instance ids that are online
        mi_list = []
        for r in combined:
          for resp in r:
            if len(resp['InstanceInformationList']) > 0:
              for mi in resp['InstanceInformationList']:
                  if mi['PingStatus'] == "Online":
                      if mi['ResourceType'] == 'ManagedInstance':
                        tags = ssm.list_tags_for_resource(ResourceType='ManagedInstance', ResourceId=mi['InstanceId'])
                        if 'TagList' in tags:
                            if len(tags['TagList']) > 0:
                                dict = {}
                                dict['Key'] = 'role'
                                dict['Value'] = 'mf_automation'
                                if dict in tags['TagList']:
                                    mi_list.append({
                                        "mi_id" : mi['InstanceId'],
                                        "online" : (True if mi['PingStatus'] == "Online" else False),
                                        "mi_name" : (mi["ComputerName"] if 'ComputerName' in mi else '')
                                    })
                      else:
                        tags = ec2.describe_tags(Filters=[
                                    {
                                        'Name': 'resource-id',
                                        'Values': [mi['InstanceId']]
                                    }
                                ])
                        if 'Tags' in tags:
                            if len(tags['Tags']) > 0:
                                dict = {}
                                dict['Key'] = 'role'
                                dict['Value'] = 'mf_automation'
                                dict['ResourceType'] = 'instance'
                                dict['ResourceId'] = mi['InstanceId']
                                if dict in tags['Tags']:
                                    mi_list.append({
                                      "mi_id": mi['InstanceId'],
                                      "online": (True if mi['PingStatus'] == "Online" else False),
                                      "mi_name": (mi["ComputerName"] if 'ComputerName' in mi else '')
                        })
        print(mi_list)
        return {'headers': {**default_http_headers},
                'body': json.dumps(mi_list)}

    elif event['httpMethod'] == 'POST':
      ''' Local Variables '''

      print(json.dumps(event["body"]))
      SSMData = json.loads(event["body"])

      # Update record audit
      auth = MFAuth()
      authResponse = auth.getUserResourceCreationPolicy(event, 'ssm_job')
      if authResponse['action'] == 'allow':

        jobUUID = str(uuid.uuid4())

        if 'user' in authResponse:
          lastModifiedBy = authResponse['user']
          lastModifiedTimestamp = datetime.utcnow().isoformat()

        SSMData["_history"] = {}
        SSMData["_history"]["createdBy"] = lastModifiedBy
        SSMData["_history"]["createdTimestamp"] = lastModifiedTimestamp


        SSMData['uuid'] = jobUUID

        #Perform payload validation.

        validation_error = []

        if "jobname" not in SSMData.keys():
            validation_error.append('jobname')

        if "mi_id" not in SSMData.keys():
            validation_error.append('mi_id')

        if "script" not in SSMData.keys():
            validation_error.append('script')

        if len(validation_error) > 0:
            errorMsg = "Request parameters missing: " + ",".join(validation_error)
            print(errorMsg)
            return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': errorMsg}

        #Build payload for SSM request.

        SSMData["SSMId"] = SSMData["mi_id"] + "+" + SSMData["uuid"] + "+" + SSMData["_history"]["createdTimestamp"]
        SSMData['output'] = ''

        #Add MF endpoint details to payload.
        SSMData['mf_endpoints'] = {
                        'LoginApiUrl': 'https://' + mf_loginapi + '.execute-api.' + mf_region + '.amazonaws.com',
                        'UserApiUrl': 'https://' + mf_userapi + '.execute-api.' + mf_region + '.amazonaws.com',
                        'UserPoolId': mf_cognitouserpoolid,
                        'Region': mf_region
                    }

        #Default script version to 0 which will return the default version.
        script_version = '0'

        if 'script_version' in SSMData["script"]:
          # User has chosen to override the script version.
          script_version = SSMData["script"]["script_version"]

        scripts_event = {
                'httpMethod': 'GET',
                'pathParameters': {
                  'scriptid': SSMData["script"]["package_uuid"],
                  'version': script_version
                }
        }
        try:
            scripts_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-scripts',
                                 InvocationType='RequestResponse',
                                 Payload=json.dumps(scripts_event))

            scripts_response_pl = scripts_response['Payload'].read()

            scripts = json.loads(scripts_response_pl)

            #Get body which contains the script item if found.
            scripts_list = json.loads(scripts['body'])

            script_selected = None
            print(scripts_list)

            for script in scripts_list:
                if script['package_uuid'] == SSMData["script"]["package_uuid"]:
                    script_selected = script
                    #replace args with user provided data.
                    script_selected['script_arguments'] = SSMData["script"]["script_arguments"]
                    SSMData['script'] = script_selected
                    break

            #Check if script is found.
            if not script_selected:
                if script_version != '0':
                  errorMsg = "Invalid package uuid or version provided. '" + SSMData["script"]["package_uuid"] + ", version " + SSMData["script"]["script_version"] + " ' does not exist."
                else:
                  errorMsg = "Invalid script uuid provided, using default version. UUID:'" + SSMData["script"]["package_uuid"] + "' does not exist."
                print(errorMsg)
                return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': errorMsg}

            ''' SSM API call for remote execution '''
            response = ssm.start_automation_execution(                                  # API call to SSM Automation Document
                DocumentName= ssm_automation_document,                                  # Name of the automation document in SSM
                DocumentVersion='$LATEST',
                Parameters={                                                            # Parameters that will be passed to the script file
                    'bucketName': [ ssm_bucket ],
                    'cmfInstance': [ application ],
                    'cmfEnvironment': [ environment ],
                    'payload': [ json.dumps(SSMData) ],
                    'instanceID': [ SSMData["mi_id"] ],
                },
            )

            print("ExecutionID: " + response['AutomationExecutionId'])

            SSMData['SSMAutomationExecutionId'] = response['AutomationExecutionId']

            """ Debug """
            print(SSMData)

            jobs_event = {
                'payload': {
                    'httpMethod': 'POST',
                    'body': json.dumps(SSMData)
                }
            }

            print(jobs_event)

            lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-jobs',
                                 InvocationType='Event',
                                 ClientContext='string',
                                 Payload=json.dumps(jobs_event))

            return {'headers': {**default_http_headers},
                    'body': json.dumps("SSMId: " + SSMData["SSMId"])}
        except BaseException as err:
            print(err)
            return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': err}
      else:
          return {'headers': {**default_http_headers},
                  'statusCode': 401,
                  'body': json.dumps(authResponse)}