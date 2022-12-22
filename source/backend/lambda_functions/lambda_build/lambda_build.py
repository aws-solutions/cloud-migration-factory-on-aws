#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################

import json, boto3, logging, os
from botocore.exceptions import ClientError
import requests
import zipfile
import mimetypes
import tempfile

log = logging.getLogger()
log.setLevel(logging.INFO)

USER_API = os.getenv('USER_API')
ADMIN_API = os.getenv('ADMIN_API')
LOGIN_API = os.getenv('LOGIN_API')
TOOLS_API = os.getenv('TOOLS_API')
SSM_WS_API = os.getenv('SSM_WS_API')
USER_POOL_ID = os.getenv('USER_POOL_ID')
APP_CLIENT_ID = os.getenv('APP_CLIENT_ID')
COGNITO_HOSTED_UI_URL = os.getenv('COGNITO_HOSTED_UI_URL')
FRONTEND_BUCKET = os.getenv('FRONTEND_BUCKET')
SOURCE_BUCKET = os.getenv('SOURCE_BUCKET')
SOURCE_KEY = os.getenv('SOURCE_KEY')
VERSION = os.getenv('VERSION')

temp_directory_name = tempfile.gettempdir() + '/frontend/'
temp_path = tempfile.gettempdir() + '/frontend.zip'

s3 = boto3.client('s3')

ZIP_MAX_SIZE = 500000000  # Set maximum size of uncompressed file to 500MBs. This is just under the /tmp max size of 512MB in Lambda.


def get_files(directory_path):
    files = []

    # r=root, d=directories, f = files
    for r, d, f in os.walk(directory_path):
        for file in f:
            files.append(os.path.join(r, file))
        for folder in d:
            sub_files = get_files(os.path.join(r, folder))
            files = files + sub_files

    return files


def update_configuration_file():
    session = boto3.session.Session()
    region = session.region_name

    with open(temp_directory_name + 'env.js', encoding='utf8') as r:
        config = r.read()

    if SSM_WS_API == 'PrivateNotDeployed':
        config = config.replace('wss://{{ssm-ws-api}}.execute-api.{{region}}.amazonaws.com/prod', SSM_WS_API)

    config = config.replace('{{region}}', region)
    config = config.replace('{{user-api}}', USER_API)
    config = config.replace('{{admin-api}}', ADMIN_API)
    config = config.replace('{{login-api}}', LOGIN_API)
    config = config.replace('{{tools-api}}', TOOLS_API)
    config = config.replace('{{ssm-ws-api}}', SSM_WS_API)
    config = config.replace('{{user-pool-id}}', USER_POOL_ID)
    config = config.replace('{{app-client-id}}', APP_CLIENT_ID)
    config = config.replace('{{version}}', VERSION)
    config = config.replace('{{cognito-hosted_ui_url}}', COGNITO_HOSTED_UI_URL)

    with open(temp_directory_name + 'env.js', "w", encoding='utf8') as w:
        w.write(config)


def update_index_html():
    session = boto3.session.Session()
    region = session.region_name
    log.info("Updating index.html CSP with API GW URLs")

    with open(temp_directory_name + 'index.html', encoding='utf8') as r:
        index_html = r.read()

    index_html = index_html.replace('{{region}}', region)
    index_html = index_html.replace('{{user-api}}', USER_API)
    index_html = index_html.replace('{{admin-api}}', ADMIN_API)
    index_html = index_html.replace('{{login-api}}', LOGIN_API)
    index_html = index_html.replace('{{tools-api}}', TOOLS_API)
    index_html = index_html.replace('{{ssm-ws-api}}', SSM_WS_API)
    index_html = index_html.replace('{{cognito-hosted_ui_url}}', COGNITO_HOSTED_UI_URL)

    with open(temp_directory_name + 'index.html', "w", encoding='utf8') as w:
        w.write(index_html)


def remove_static_site():
    log.info('Removing S3 site content.')
    try:
        s3 = boto3.resource('s3')
        s3_bucket = s3.Bucket(FRONTEND_BUCKET)
        bucket_versioning = s3.BucketVersioning(FRONTEND_BUCKET)
        if bucket_versioning.status == 'Enabled':
            s3_bucket.object_versions.delete()
        else:
            s3_bucket.objects.all().delete()
        log.info('CMF S3 site content deleted.')
    except (ClientError) as e:
        log.error(e)
        raise e


def deploy_static_site():
    log.info('Downloading source zip.')
    try:
        s3.download_file(SOURCE_BUCKET, SOURCE_KEY, temp_path)
    except (ClientError) as e:
        log.error(e)
        raise e

    log.info('Extracting source zip.')
    fe_zip_file = open(temp_path, "rb")
    try:
        fe_zip = zipfile.ZipFile(fe_zip_file)
        total_uncompressed_size = sum(file.file_size for file in fe_zip.infolist())
        if total_uncompressed_size > ZIP_MAX_SIZE:
            error_msg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE / 1e+6}MBs.'
            log.error(error_msg)
        fe_zip.extractall(temp_directory_name)
    except (IOError, zipfile.BadZipfile) as e:
        error_msg = 'Invalid zip file.'
        log.error(error_msg)
        raise e

    update_configuration_file()
    update_index_html()

    files_to_copy = get_files(temp_directory_name)
    log.debug('Files to copy')
    log.debug(files_to_copy)

    for file_name in files_to_copy:
        try:
            log.debug('Copying file: ' + file_name)
            mimetype, _ = mimetypes.guess_type(file_name)
            if mimetype is None:
                log.error("Failed to guess mimetype for file " + file_name + " Defaulting to application/json.")
                mimetype = 'application/json'
            response = s3.upload_file(file_name, FRONTEND_BUCKET, file_name.replace(temp_directory_name, ""),
                                      ExtraArgs={"ContentType": mimetype})
        except ClientError as e:
            log.error(e)
            raise e


def lambda_handler(event, context):
    try:
        log.info('Event:\n {}'.format(event))
        log.info('Context:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            log.info('Create action')

            deploy_static_site()

            status = 'SUCCESS'
            message = 'Frontend deployment process complete.'

        elif event['RequestType'] == 'Update':
            log.info('Update action')

            deploy_static_site()

            status = 'SUCCESS'
            message = 'Frontend redeployed from AWS master.'

        elif event['RequestType'] == 'Delete':
            log.info('Delete action')

#             remove_static_site()

            status = 'SUCCESS'
#             message = 'Emptied CMF Frontend S3 bucket : ' + FRONTEND_BUCKET
            message = 'S3 Bucket should be manually emptied : ' + FRONTEND_BUCKET

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
    response = respond(event, context, status, response_data, None)

    return {
        'Response': response
    }


def respond(event, context, responseStatus, responseData, physicalResourceId):
    # Build response payload required by CloudFormation
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'Details in: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['Data'] = responseData

    # Convert json object to string and log it
    json_responseBody = json.dumps(responseBody)
    log.info('Response body: {}'.format(str(json_responseBody)))

    # Set response URL
    responseUrl = event['ResponseURL']

    # Set headers for preparation for a PUT
    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    # Return the response to the signed S3 URL
    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        log.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        log.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'
