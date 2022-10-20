import boto3
import json
from botocore.exceptions import ClientError
import base64
import os

region = os.environ['region']

def list(event):
    session = boto3.session.Session(region_name=region)
    client = session.client(service_name='secretsmanager')

    if event['body']:
        body = json.loads(event['body'])
        try:
            items = client.get_secret_value(SecretId=body['secretName'])
            # output = base64.b64decode(items['SecretString'].encode("utf-8")).decode("ascii")
            output = items['SecretString']
            statusCode = 200
            data = json.loads(output)
            if data['SECRET_TYPE'] == 'OS':
                data['PASSWORD'] = "*********"
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
                data['PASSWORD'] = "*********"
                data['APIKEY'] = "*********"

            # data sanitization


        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                statusCode = 404
                data = 'User {} not found in secret manager' .format(Name)
            elif e.response['Error']['Code'] == 'AccessDeniedException':
                return {"statusCode": 404, "body": "AccessDenied"}
            elif e.response['Error']['Code'] == 'InvalidRequestException':
                return {"statusCode": 404, "body": "Possible this secret was recently deleted"}

    else:
        try:
            extraArgs = {'Filters': [
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

            raw_list = []
            while True:
                result = client.list_secrets(**extraArgs)

                for key in result['SecretList']:

                    items = client.get_secret_value(SecretId=key['Name'])
                    output = items['SecretString']

                    statusCode = 200
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
                            data['PASSWORD'] = "*********"
                            # data sanitization
                            data['USERNAME'] = data['USERNAME'].replace('\t','\\t')
                            data['USERNAME'] = data['USERNAME'].replace('\n','\\n')
                            data['USERNAME'] = data['USERNAME'].replace('\r','\\r')
                            key['data'] = data
                        elif data['SECRET_TYPE'] == 'keyValue':
                            data['SECRET_VALUE'] = "*********"
                            # data sanitization
                            data['SECRET_KEY'] = data['SECRET_KEY'].replace('\t','\\t')
                            data['SECRET_KEY'] = data['SECRET_KEY'].replace('\n','\\n')
                            data['SECRET_KEY'] = data['SECRET_KEY'].replace('\r','\\r')
                            key['data'] = data
                        elif data['SECRET_TYPE'] == 'plainText':
                            data['SECRET_STRING'] = "*********"
                            key['data'] = data
                        else:
                            data['PASSWORD'] = "*********"
                            data['APIKEY'] = "*********"
                            key['data'] = data
                        raw_list.append(key)
                    except:
                        pass

                if 'NextToken' in result:
                    extraArgs['NextToken'] = result['NextToken']
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
