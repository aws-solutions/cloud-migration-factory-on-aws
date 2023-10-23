#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


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
VPCE_API_ID = os.getenv('VPCE_API_ID')
APP_CLIENT_ID = os.getenv('APP_CLIENT_ID')
COGNITO_HOSTED_UI_URL = os.getenv('COGNITO_HOSTED_UI_URL')
FRONTEND_BUCKET = os.getenv('FRONTEND_BUCKET')
SOURCE_BUCKET = os.getenv('SOURCE_BUCKET')
SOURCE_KEY = os.getenv('SOURCE_KEY')
VERSION = os.getenv('VERSION')

FRONTEND_CONFIG_FILENAME = 'env.js'
FRONTEND_INDEX_FILENAME = 'index.html'

PLACEHOLDER_HOSTED_UI = '{{cognito-hosted_ui_url}}'
PLACEHOLDER_REGION = '{{region}}'
PLACEHOLDER_USER_API = '{{user-api}}'
PLACEHOLDER_ADMIN_API = '{{admin-api}}'
PLACEHOLDER_LOGIN_API = '{{login-api}}'
PLACEHOLDER_TOOLS_API = '{{tools-api}}'
PLACEHOLDER_SSM_WS_API = '{{ssm-ws-api}}'
PLACEHOLDER_USER_POOL_ID = '{{user-pool-id}}'
PLACEHOLDER_APP_CLIENT = '{{app-client-id}}'
PLACEHOLDER_UI_VERSION = '{{version}}'
PLACEHOLDER_VPCE = '{{vpce-id}}'

temp_directory_name = tempfile.gettempdir() + '/frontend/'
temp_path = tempfile.gettempdir() + '/frontend.zip'

s3 = boto3.client('s3')

ZIP_MAX_SIZE = 500000000  # Set maximum size of uncompressed file to 500MBs. This is just under the /tmp max size of 512MB in Lambda.


def get_files(directory_path):
    files = []

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

    with open(temp_directory_name + FRONTEND_CONFIG_FILENAME, encoding='utf8') as r:
        config = r.read()

    if SSM_WS_API == 'PrivateNotDeployed':
        config = config.replace('wss://{{ssm-ws-api}}.execute-api.{{region}}.amazonaws.com/prod', SSM_WS_API)

    if VPCE_API_ID:
        config = config.replace(PLACEHOLDER_VPCE, VPCE_API_ID)
    else:
        config = config.replace(PLACEHOLDER_VPCE, '')

    config = config.replace(PLACEHOLDER_REGION, region)
    config = config.replace(PLACEHOLDER_USER_API, USER_API)
    config = config.replace(PLACEHOLDER_ADMIN_API, ADMIN_API)
    config = config.replace(PLACEHOLDER_LOGIN_API, LOGIN_API)
    config = config.replace(PLACEHOLDER_TOOLS_API, TOOLS_API)
    config = config.replace(PLACEHOLDER_SSM_WS_API, SSM_WS_API)
    config = config.replace(PLACEHOLDER_USER_POOL_ID, USER_POOL_ID)
    config = config.replace(PLACEHOLDER_APP_CLIENT, APP_CLIENT_ID)
    config = config.replace(PLACEHOLDER_UI_VERSION, VERSION)
    config = config.replace(PLACEHOLDER_HOSTED_UI, COGNITO_HOSTED_UI_URL)

    with open(temp_directory_name + FRONTEND_CONFIG_FILENAME, "w", encoding='utf8') as w:
        w.write(config)


def update_index_html():
    session = boto3.session.Session()
    region = session.region_name
    log.info("Updating index.html CSP with API GW URLs")

    with open(temp_directory_name + FRONTEND_INDEX_FILENAME, encoding='utf8') as r:
        index_html = r.read()

    if VPCE_API_ID != '':
        index_html = index_html.replace(PLACEHOLDER_VPCE, '-' + VPCE_API_ID)
    else:
        index_html = index_html.replace(PLACEHOLDER_VPCE, '')

    if COGNITO_HOSTED_UI_URL != '':
        index_html = index_html.replace(PLACEHOLDER_HOSTED_UI, 'https://' + COGNITO_HOSTED_UI_URL)
    else:
        index_html = index_html.replace(PLACEHOLDER_HOSTED_UI, '')

    index_html = index_html.replace(PLACEHOLDER_REGION, region)
    index_html = index_html.replace(PLACEHOLDER_USER_API, USER_API)
    index_html = index_html.replace(PLACEHOLDER_ADMIN_API, ADMIN_API)
    index_html = index_html.replace(PLACEHOLDER_LOGIN_API, LOGIN_API)
    index_html = index_html.replace(PLACEHOLDER_TOOLS_API, TOOLS_API)
    index_html = index_html.replace(PLACEHOLDER_SSM_WS_API, SSM_WS_API)

    with open(temp_directory_name + FRONTEND_INDEX_FILENAME, "w", encoding='utf8') as w:
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
            log.debug(f"Copying file: {file_name}")
            mimetype, _ = mimetypes.guess_type(file_name)
            if mimetype is None:
                log.error(f"Failed to guess mimetype for file {file_name} Defaulting to application/json.")
                mimetype = 'application/json'
            s3.upload_file(file_name, FRONTEND_BUCKET, file_name.replace(temp_directory_name, ""),
                           ExtraArgs={"ContentType": mimetype})
        except ClientError as e:
            log.error(e)
            raise e


def lambda_handler(event, context):
    try:
        log.info(f"Event:\n {event}")
        log.info(f"Context:\n {context}")

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
            message = f"S3 Bucket should be manually emptied : {FRONTEND_BUCKET}"

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


def respond(event, context, response_status, response_data):
    # Build response payload required by CloudFormation
    response_body = {
        'Status': response_status,
        'Reason': f"Details in: {context.log_stream_name}",
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }

    # Convert json object to string and log it
    json_response_body = json.dumps(response_body)
    log.info(f"Response body: {str(json_response_body)}")

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
        log.info(f"Status code: {str(response.reason)}")
        return 'SUCCESS'

    except Exception as e:
        log.error(f"Failed to put message: {str(e)}")
        return 'FAILED'
