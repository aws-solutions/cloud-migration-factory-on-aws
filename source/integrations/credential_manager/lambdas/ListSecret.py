import boto3
import json
from botocore.exceptions import ClientError
import base64
import os

region = os.environ['region']
pass_mask = "*********"


def list(event):
    session = boto3.session.Session(region_name=region)
    client = session.client(service_name='secretsmanager')

    raw_list = []
    try:
        extra_args = {'Filters': [
            {
                'Key': 'tag-key',
                'Values': ['CMFUse']
            },
            {
                'Key': 'tag-value',
                'Values': ["CMF Automation Credential Manager"]
            }
        ]
        }

        while True:
            result = client.list_secrets(**extra_args)

            for key in result['SecretList']:

                items = client.get_secret_value(SecretId=key['Name'])
                output = items['SecretString']

                try:
                    data = json.loads(output)

                    if data['SECRET_TYPE'] == 'OS':
                        if 'IS_SSH_KEY' in data:
                            # convert to boolean.
                            if data['IS_SSH_KEY'].lower() == 'true':
                                data['IS_SSH_KEY'] = True
                            else:
                                data['IS_SSH_KEY'] = False
                        else:
                            data['IS_SSH_KEY'] = False
                        data['PASSWORD'] = pass_mask
                        # data sanitization
                        data['USERNAME'] = data['USERNAME'].replace('\t', '\\t')
                        data['USERNAME'] = data['USERNAME'].replace('\n', '\\n')
                        data['USERNAME'] = data['USERNAME'].replace('\r', '\\r')
                        key['data'] = data
                    elif data['SECRET_TYPE'] == 'keyValue':
                        data['SECRET_VALUE'] = pass_mask
                        # data sanitization
                        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\t', '\\t')
                        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\n', '\\n')
                        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\r', '\\r')
                        key['data'] = data
                    elif data['SECRET_TYPE'] == 'plainText':
                        data['SECRET_STRING'] = pass_mask
                        key['data'] = data
                    else:
                        data['PASSWORD'] = pass_mask
                        data['APIKEY'] = pass_mask
                        key['data'] = data
                    raw_list.append(key)
                except:
                    pass

            if 'NextToken' in result:
                extra_args['NextToken'] = result['NextToken']
            else:
                break
    except ClientError as e:
        if e.response['Error']['Code'] == 'InternalServiceError':
            return {"statusCode": 500, "body": "An error occurred on the server side."}
        elif e.response['Error']['Code'] == 'InvalidNextTokenException':
            return {"statusCode": 400, "body": "You provided an invalid NextToken value."}
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            return {"statusCode": 400, "body": "You provided an invalid value for a parameter."}

    sorted_list = sorted(raw_list, key=lambda x: x['LastChangedDate'], reverse=True)
    return {
        'statusCode': 200,
        'body': json.dumps(sorted_list, default=str)
    }
