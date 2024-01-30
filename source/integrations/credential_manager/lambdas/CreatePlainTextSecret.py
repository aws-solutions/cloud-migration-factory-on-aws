import json
import cmf_boto
from botocore.exceptions import ClientError
import os

region = os.environ['region']


def create(event):
    body = json.loads(event['body'])
    secret_string = body['secretString'].replace('\\', '\\\\')
    secret_name = body['secretName']
    secret_type = body['secretType']
    description = body['description']

    client = cmf_boto.client('secretsmanager', region_name=region)

    try:
        data = "{\"SECRET_STRING\": \"%s\", \"SECRET_TYPE\": \"%s\"}" % (secret_string, secret_type)
        client.create_secret(Name=secret_name,
                             Description=description,
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
