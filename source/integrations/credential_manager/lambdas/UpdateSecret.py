import json
import cmf_boto
from botocore.exceptions import ClientError
import os

region = os.environ['region']


def update(event):
    body = json.loads(event['body'])
    secret_name = body['secretName']

    client = cmf_boto.client('secretsmanager', region_name=region)

    extra_args = {'Filters': [
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

    result = client.list_secrets(**extra_args)

    if result['SecretList']:
        for secret in result['SecretList']:
            if secret['Name'] == secret_name:
                return process_secret(client, secret_name, body)

    output = "Secret %s not found, or not under the control of Credentials Manager." % secret_name
    return {"statusCode": 404, "body": output}


def process_secret(client, secret_name, body):
    try:
        items = client.get_secret_value(SecretId=secret_name)
        output = json.loads(items['SecretString'])
        secret_type = output['SECRET_TYPE']
        if body.get('description'):
            description = body['description']
        else:
            key_metadata = client.describe_secret(SecretId=secret_name)
            if key_metadata.get('Description'):
                description = key_metadata['Description']
        if secret_type == 'keyValue':
            data = update_secret_data_key_value(body, output)
        elif secret_type == 'plainText':
            data = update_secret_data_plain_text(body, output)
        else:
            data = update_secret_data_other(body, output, secret_type)

        client.update_secret(SecretId=secret_name, Description=description, SecretString=data)

        return {"statusCode": 200, "body": "Successfully updated Secret - " + secret_name}
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDeniedException':
            msg = "AccessDenied"
            print(msg)
            return {"statusCode": 404, "body": msg}
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            msg = "Secret - " + secret_name + " not found."
            print(msg)
            return {"statusCode": 404, "body": msg}


def update_secret_data_key_value(body, output):
    # checking if secretKey and secretValue is updated
    # else fetches existing value and updates
    if body.get('secretKey'):
        secret_key = body['secretKey'].replace('\\', '\\\\')
    else:
        secret_key = list(output.keys())[0]
    if body.get('secretValue'):
        secret_value = body['secretValue'].replace('\\', '\\\\')
    else:
        secret_value = list(output.values())[0]

    data = "{\"SECRET_KEY\": \"%s\", \"SECRET_VALUE\": \"%s\", \"SECRET_TYPE\": \"%s\"}" % (
        secret_key, secret_value, 'keyValue')
    return data


def update_secret_data_plain_text(body, output):
    # checking if secretString is updated
    # else fetches existing value and updates
    if body.get('secretString'):
        secret_string = body['secretString'].replace('\\', '\\\\')
    else:
        secret_string = list(output.values())[0]

    data = "{\"SECRET_STRING\": \"%s\", \"SECRET_TYPE\": \"%s\"}" % (secret_string, 'plainText')
    return data


def update_secret_data_other(body, output, secret_type):
    # checking if username, password and osType is updated
    # else fetches original value from secret manager and updates
    if body.get('user'):
        username = body['user'].replace('\\', '\\\\')
    else:
        username = output.get("USERNAME")
    if body.get('password'):
        password = body['password'].replace('\\', '\\\\')
    else:
        password = output.get("PASSWORD")
    if body.get('osType'):
        os_type = body['osType']
    else:
        os_type = output.get("OS_TYPE")

    if body.get('isSSHKey'):
        iskey = body['isSSHKey']
    else:
        iskey = output.get("isSSHKey")

    data = "{\"USERNAME\": \"%s\", \"PASSWORD\": \"%s\", \"SECRET_TYPE\": \"%s\", \"OS_TYPE\": \"%s\", \"IS_SSH_KEY\": \"%s\"}" % (
        username, password, secret_type, os_type, iskey)
    return data
