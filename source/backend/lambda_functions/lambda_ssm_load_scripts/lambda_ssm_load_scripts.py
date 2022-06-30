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

log = logging.getLogger()
log.setLevel(logging.INFO)

application = os.environ['application']
environment = os.environ['environment']
code_bucket = os.environ['code_bucket_name']
key_prefix = os.environ['key_prefix']

lambda_client = boto3.client('lambda')
s3 = boto3.client('s3')
default_scripts_s3_key = key_prefix + '/default_scripts.zip'

ZIP_MAX_SIZE = 500000000 # Set maximum size of uncompressed file to 500MBs. This is just under the /tmp max size of 512MB in Lambda.

class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)

def respond(event, context, responseStatus, responseData, physicalResourceId):
    #Build response payload required by CloudFormation
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'Details in: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['Data'] = responseData

    #Convert json object to string and log it
    json_responseBody = json.dumps(responseBody)
    log.info('Response body: {}'.format(str(json_responseBody)))

    #Set response URL
    responseUrl = event['ResponseURL']

    #Set headers for preparation for a PUT
    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    #Return the response to the signed S3 URL
    try:
        response = requests.put(responseUrl,
        data=json_responseBody,
        headers=headers)
        log.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        log.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'

def cleanup_temp(packageUUID):

    # Delete temp package files in /tmp/ to ensure that large files are not left hanging around for longer than required.
    if os.path.exists("/tmp/default_scripts.zip"):
        os.remove("/tmp/default_scripts.zip")

    if os.path.exists("/tmp/" + packageUUID):
        shutil.rmtree("/tmp/" + packageUUID, ignore_errors=True)

def import_script_packages():
    temp_directory_name = '/tmp/default_scripts/'

    try:
        temp_path = "/tmp/default_scripts.zip"

        s3.download_file(code_bucket, default_scripts_s3_key, temp_path)

        tempUUID = str(uuid.uuid4())
        # Extract contents of zip
        myZip = open(temp_path, "rb")
        try:
            zip = zipfile.ZipFile(myZip)
            total_uncompressed_size = sum(file.file_size for file in zip.infolist())
            if total_uncompressed_size > ZIP_MAX_SIZE:
                errorMsg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE/1e+6}MBs.'
                print(errorMsg)
            zip.extractall("/tmp/default_scripts/")
        except (IOError, zipfile.BadZipfile) as e:
            errorMsg = 'Invalid zip file.'
            print(errorMsg)

        directory = os.fsencode(temp_directory_name)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            fullpath = temp_directory_name + filename
            print(fullpath)

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

        cleanup_temp(tempUUID)
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
            status='SUCCESS'
            message='Default script packages loaded successfully'

        elif event['RequestType'] == 'Update':
            log.info('Update action')
            import_script_packages()
            status='SUCCESS'
            message='No update required'

        elif event['RequestType'] == 'Delete':
            log.info('Delete action')
            status='SUCCESS'
            message='No deletion required'

        else:
            log.info('SUCCESS!')
            status='SUCCESS'
            message='Unexpected event received from CloudFormation'

    except Exception as e:
        log.info('FAILED!')
        log.info(e)
        status='FAILED'
        message='Exception during processing'

    response_data = {'Message' : message}
    response=respond(event, context, status, response_data, None)

    return {
        'Response' :response
    }