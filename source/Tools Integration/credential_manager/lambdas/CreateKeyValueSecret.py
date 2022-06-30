import json
import boto3
from botocore.exceptions import ClientError
import base64
import os
from botocore import config

if 'solution_identifier' in os.environ:
    solution_identifier = json.loads(os.environ['solution_identifier'])
    user_agent_extra_param = {"user_agent_extra": solution_identifier}
    boto_config = config.Config(**user_agent_extra_param)
else:
    boto_config = None

region = os.environ['region']


def create(event):
    body = json.loads(event['body'])
    secret_name = body['secretName']
    secret_key = body['secretKey'].replace('\\', '\\\\')
    secret_value = body['secretValue'].replace('\\', '\\\\')
    secret_type = body['secretType']
    description = body['description']

    session = boto3.session.Session(region_name=region)
    client = session.client(service_name='secretsmanager', config=boto_config)

    try:
        data = "{\"SECRET_KEY\": \"%s\", \"SECRET_VALUE\": \"%s\", \"SECRET_TYPE\": \"%s\"}" % (
        secret_key, secret_value, secret_type)
        client.create_secret(Name=secret_name,
                             Description=description,
                             # SecretString=base64.b64encode(data.encode("utf-8")).decode("ascii"),
                             SecretString=data,
                             Tags=[{"Key": "CMFUse", "Value": "CMF Automation Credential Manager"}]
                             )
        return {"statusCode": 200, "body": "Successfully created Secret - " + secret_name}
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceExistsException':
            msg = "Secret " + secret_name + " Already created"
            print(msg)
            return {"statusCode": 202, "body": msg}
        elif e.response['Error']['Code'] == 'AccessDeniedException':
            msg = "AccessDenied"
            print(msg)
            return {"statusCode": 404, "body": msg}
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            msg = "Possible a credential with the same name was recently deleted, please attempt this again later."
            print(msg)
            return {"statusCode": 405, "body": msg}
        elif e.response['Error']['Code'] == 'ValidationException':
            msg = "Invalid secret name. Must be a valid name containing alphanumeric characters, or any of the following: -/_+=.@!"
            print(msg)
            return {"statusCode": 405, "body": msg}
        else:
            msg = str(e)
            print(msg)
            return {"statusCode": 403, "body": msg}
