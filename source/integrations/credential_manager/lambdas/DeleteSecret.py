import json
import boto3
from botocore.exceptions import ClientError
import os

region = os.environ['region']

def delete(event):
    body = json.loads(event['body'])
    secret_name = body['secretName']
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
    deleted = False

    if result['SecretList']:
        for secret in result['SecretList']:
            if secret['Name'] == secret_name:
                # Secret found that is under the control of Credentials Manager, proceed with deletion.
                try:
                    response = client.delete_secret(
                                                    SecretId=secret_name,
                                                    ForceDeleteWithoutRecovery=True
                                                    )
                    output = "Successfully deleted secret - %s" %secret_name
                    statusCode = 200
                    deleted = True

                except ClientError as e:
                    if e.response['Error']['Code'] == 'AccessDeniedException':
                        return {"statusCode": 404, "body": "AccessDenied"}

                return {
                    'statusCode': statusCode,
                    'body': output
                }

    if not deleted:
        # Secret not found that matches Credentials Manager signature.
        output = "Secret %s not found, or not under the control of Credentials Manager." % secret_name
        return {"statusCode": 404, "body": output}
