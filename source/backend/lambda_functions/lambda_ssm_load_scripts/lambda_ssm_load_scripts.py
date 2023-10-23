#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import boto3
import json
from datetime import datetime
import uuid
import base64
import logging
import shutil
import zipfile
import requests
import tempfile

log = logging.getLogger()
log.setLevel(logging.INFO)

application = os.environ['application']
environment = os.environ['environment']
code_bucket = os.environ['code_bucket_name']
key_prefix = os.environ['key_prefix']

lambda_client = boto3.client('lambda')
s3 = boto3.client('s3')

CONST_DEFAULT_SCRIPTS_FILE_NANE = 'default_scripts.zip'

default_scripts_s3_key = key_prefix + '/' + CONST_DEFAULT_SCRIPTS_FILE_NANE

# Set maximum size of uncompressed file to 500MBs. This is just under the /tmp max size of 512MB in Lambda.
ZIP_MAX_SIZE = 500000000


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


def respond(event, context, response_status, response_data):
    # Build response payload required by CloudFormation
    response_body = {
        'Status': response_status,
        'Reason': 'Details in: ' + context.log_stream_name,
        'PhysicalResourceId': context.log_stream_name, 'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }

    # Convert json object to string and log it
    json_response_body = json.dumps(response_body)
    log.info('Response body: {}'.format(str(json_response_body)))

    # Set response URL
    response_url = event['ResponseURL']

    # Set headers for preparation for a PUT
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    # Return the response to the signed S3 URL
    try:
        response = requests.put(response_url,
                                data=json_response_body,
                                headers=headers,
                                timeout=30)
        log.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        log.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'


def cleanup_temp(package_uuid):
    # Delete temp package files in /tmp/ to ensure that large files are not left hanging around for longer than required.
    if os.path.exists(tempfile.gettempdir() + '/' + CONST_DEFAULT_SCRIPTS_FILE_NANE):
        os.remove(tempfile.gettempdir() + '/' + CONST_DEFAULT_SCRIPTS_FILE_NANE)

    if os.path.exists(tempfile.gettempdir() + '/' + package_uuid):
        shutil.rmtree(tempfile.gettempdir() + '/' + package_uuid, ignore_errors=True)


def import_script_packages():
    temp_directory_name = tempfile.gettempdir() + '/default_scripts/'

    try:
        temp_path = tempfile.gettempdir() + '/' + CONST_DEFAULT_SCRIPTS_FILE_NANE

        s3.download_file(code_bucket, default_scripts_s3_key, temp_path)

        temp_uuid = str(uuid.uuid4())
        # Extract contents of zip
        my_zip = open(temp_path, "rb")
        try:
            zip_file = zipfile.ZipFile(my_zip)
            total_uncompressed_size = sum(file.file_size for file in zip_file.infolist())
            if total_uncompressed_size > ZIP_MAX_SIZE:
                error_msg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE/1e+6}MBs.'
                print(error_msg)
            zip_file.extractall(tempfile.gettempdir() + '/default_scripts/')
        except (IOError, zipfile.BadZipfile) as e:
            error_msg = 'Invalid zip file.'
            print(error_msg)

        directory = os.fsencode(temp_directory_name)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            fullpath = temp_directory_name + filename
            print(fullpath)

            if not os.path.isdir(fullpath):
                with open(fullpath, 'rb') as script_zip_read:
                    zip_content = script_zip_read.read()
                    script_zip_encoded = base64.b64encode(zip_content)
                    script_zip_read.close()

                scripts_event = {
                    'httpMethod': 'POST',
                    'body': json.dumps({
                       'script_file': script_zip_encoded
                     }, cls=JsonEncoder)
                }

                scripts_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-scripts',
                                                InvocationType='RequestResponse',
                                                Payload=json.dumps(scripts_event, cls=JsonEncoder))

                # Decode return payload message and print to log.
                scripts_response_payload = scripts_response['Payload']
                scripts_response_payload_text = scripts_response_payload.read()
                print(scripts_response_payload_text)

        cleanup_temp(temp_uuid)
    except Exception as e:
        print(e)
        log.info('FAILED!')
        log.info(e)


def lambda_handler(event, context):

    try:
        log.info('Event:\n {}'.format(event))
        log.info('Contex:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            log.info('Create action')
            import_script_packages()
            status = 'SUCCESS'
            message = 'Default script packages loaded successfully'

        elif event['RequestType'] == 'Update':
            log.info('Update action')
            import_script_packages()
            status = 'SUCCESS'
            message = 'No update required'

        elif event['RequestType'] == 'Delete':
            log.info('Delete action')
            status = 'SUCCESS'
            message = 'No deletion required'

        else:
            log.info('SUCCESS!')
            status = 'SUCCESS'
            message = 'Unexpected event received from CloudFormation'

    except Exception as e:
        log.info('FAILED!')
        log.info(e)
        status = 'FAILED'
        message = 'Exception during processing'

    response_data = {'Message': message}
    response = respond(event, context, status, response_data)

    return {
        'Response': response
    }
