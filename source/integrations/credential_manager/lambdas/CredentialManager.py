import json
import ListSecret
import CreateOsSecret
import CreateKeyValueSecret
import DeleteSecret
import UpdateSecret
import CreatePlainTextSecret

from cmf_utils import default_http_headers


def lambda_handler(event, _):
    if event['httpMethod'] == 'GET':
        print("sending to ListSecret")
        return {**{'headers': default_http_headers}, **ListSecret.list()}
    if event['body']:
        body = json.loads(event['body'])
        secret_type = body['secretType']
    if event['httpMethod'] == 'POST':
        return process_post(secret_type, event)
    if event['httpMethod'] == 'DELETE':
        if secret_type == 'keyValue' or secret_type == 'OS' or secret_type == 'plainText':
            print("sending to DeleteSecret")
            return {**{'headers': default_http_headers}, **DeleteSecret.delete(event)}
    if event['httpMethod'] == 'PUT':
        if secret_type == 'keyValue' or secret_type == 'OS' or secret_type == 'plainText':
            print("sending to UpdateSecret")
            return {**{'headers': default_http_headers}, **UpdateSecret.update(event)}


def process_post(secret_type, event):
    if secret_type == 'OS':
        print("sending to CreateOsSecret")
        return {**{'headers': default_http_headers}, **CreateOsSecret.create(event)}
    if secret_type == 'keyValue':
        print("sending to CreateKeyValueSecret")
        return {**{'headers': default_http_headers}, **CreateKeyValueSecret.create(event)}
    if secret_type == 'plainText':
        print("sending to CreatePlainTextSecret")
        return {**{'headers': default_http_headers}, **CreatePlainTextSecret.create(event)}
