import json
import ListSecret
import CreateOsSecret
import CreateKeyValueSecret
import DeleteSecret
import UpdateSecret
import CreatePlainTextSecret
import os

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

def lambda_handler(event, context):

    if event['httpMethod'] == 'GET':
        print("sending to ListSecret")
        return {**{'headers': default_http_headers}, **ListSecret.list(event)}
    if event['body']:
        body = json.loads(event['body'])
        secret_type = body['secretType']
    if event['httpMethod'] == 'POST':
        if secret_type == 'OS':
            print("sending to CreateOsSecret")
            return {**{'headers': default_http_headers}, **CreateOsSecret.create(event)}
        # if ("/getsecret") in event['path']:
        #     print("sending to get-secret")
        #     return GetSecret.get(event)
        if secret_type == 'keyValue':
            print("sending to CreateKeyValueSecret")
            return {**{'headers': default_http_headers}, **CreateKeyValueSecret.create(event)}
        if secret_type == 'plainText':
            print("sending to CreatePlainTextSecret")
            return {**{'headers': default_http_headers}, **CreatePlainTextSecret.create(event)}
    if event['httpMethod'] == 'DELETE':
        if (secret_type == 'keyValue' or secret_type == 'OS' or secret_type == 'plainText'):
            print("sending to DeleteSecret")
            return {**{'headers': default_http_headers}, **DeleteSecret.delete(event)}
    if event['httpMethod'] == 'PUT':
        if (secret_type == 'keyValue' or secret_type == 'OS' or secret_type == 'plainText'):
            print("sending to UpdateSecret")
            return {**{'headers': default_http_headers}, **UpdateSecret.update(event)}
