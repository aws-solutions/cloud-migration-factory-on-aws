import json
import boto3
from botocore.exceptions import ClientError
import base64
import os

region = os.environ['region']

def get(event):
    secret_name = event['queryStringParameters']['Name']
    session = boto3.session.Session(region_name=region)
    client = session.client(service_name='secretsmanager')

    extraArgs = {'Filters': [
        {
            'Key': 'tag-key',
            'Values': ['CMFUse']
        },
        {
            'Key': 'tag-value',
            'Values': ['CMF Automation Credential Manager']
        },
        {
            'Key': 'name',
            'Values': [secret_name]
        }
    ]}

    result = client.list_secrets(**extraArgs)
    found = False

    if result['SecretList']:
        for secret in result['SecretList']:
            if secret['Name'] == secret_name:
                try:
                    items = client.get_secret_value(SecretId=secret_name)
                    output = items['SecretString']

                    statusCode = 200
                    data = json.loads(output)
                    if data['SECRET_TYPE'] == 'OS':
                        data['PASSWORD'] = "*********" # NOSONAR This is a password replacement text, not a real password.
                        # data sanitization
                        data['USERNAME'] = data['USERNAME'].replace('\t','\\t')
                        data['USERNAME'] = data['USERNAME'].replace('\n','\\n')
                        data['USERNAME'] = data['USERNAME'].replace('\r','\\r')
                    elif data['SECRET_TYPE'] == 'keyValue':
                        data['SECRET_VALUE'] = "*********"
                        # data sanitization
                        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\t','\\t')
                        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\n','\\n')
                        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\r','\\r')
                    elif data['SECRET_TYPE'] == 'plainText':
                        data['SECRET_STRING'] = "*********"
                    else:
                        data['PASSWORD'] = "*********" # NOSONAR This is a password replacement text, not a real password.
                        data['APIKEY'] = "*********"
                    found = True

                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        statusCode = 404
                        data = 'User {} not found in secret manager' .format(secret_name)
                    elif e.response['Error']['Code'] == 'AccessDeniedException':
                        return {"statusCode": 404, "body": "AccessDenied"}
                    elif e.response['Error']['Code'] == 'InvalidRequestException':
                        return {"statusCode": 404, "body": "Possible this secret was recently deleted"}

                return {
                    'isBase64Encoded': 'false',
                    'statusCode': statusCode,
                    'body': json.dumps(data)
                }
    if not found:
        # Secret not found that matches Credentials Manager signature.
        output = "Secret %s not found, or not under the control of Credentials Manager." % secret_name
        return {"statusCode": 404, "body": output}