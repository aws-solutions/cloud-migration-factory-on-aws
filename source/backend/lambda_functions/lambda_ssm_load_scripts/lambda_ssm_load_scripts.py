#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import json
import traceback
import uuid
import base64
import shutil
import zipfile
import requests
import tempfile
import jmespath
import cmf_boto
import yaml
from cmf_logger import logger


application = os.environ['application']
environment = os.environ['environment']
code_bucket = os.environ['code_bucket_name']
key_prefix = os.environ['key_prefix']
scripts_table_name = os.environ['ScriptsDynamoDBTable']

lambda_client = cmf_boto.client('lambda')
s3 = cmf_boto.client('s3')

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
    logger.info('Response body: {}'.format(str(json_response_body)))

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
        logger.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        logger.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'


def cleanup_temp(package_uuid):
    # Delete temp package files in /tmp/ to ensure that large files are not left hanging around for longer than required.
    if os.path.exists(tempfile.gettempdir() + '/' + CONST_DEFAULT_SCRIPTS_FILE_NANE):
        os.remove(tempfile.gettempdir() + '/' + CONST_DEFAULT_SCRIPTS_FILE_NANE)

    if os.path.exists(tempfile.gettempdir() + '/' + package_uuid):
        shutil.rmtree(tempfile.gettempdir() + '/' + package_uuid, ignore_errors=True)

def get_script_name_from_script_zip(directory_path: str, zip_file_name: str) -> str:
    script_name = None
    zip_path = directory_path + zip_file_name
    script_package_path = tempfile.gettempdir() + '/unzipped_scripts/' + zip_file_name.replace(".zip", "")
    # Unzip
    logger.info(f"Getting script name from zip: {directory_path}/{zip_file_name}")
    try:
        with open(zip_path , "rb") as script_package_zip_file:
            script_package_zip = zipfile.ZipFile(script_package_zip_file)
            script_package_zip.extractall(script_package_path) # NOSONAR This size of the file is in control
            logger.info("Extract all of zip completed...")
        # Read file as json
        f = open(f"{script_package_path}/Package-Structure.yml", mode = "r", encoding="UTF8")
        package_structure = yaml.full_load(f)
        # Use jmespath to get script name
        script_name = jmespath.search("Name", package_structure)

    except Exception as e:
        logger.info(f"Error while unzip and reading package-structure.yml for {zip_path}, returning script_name as None.")
        logger.info('Error: {}'.format(str(e)))
    return script_name

def import_script_packages():
    temp_directory_name = tempfile.gettempdir() + '/default_scripts/'

    try:
        logger.info("Started processing scripts.. ")
        temp_path = tempfile.gettempdir() + '/' + CONST_DEFAULT_SCRIPTS_FILE_NANE

        s3.download_file(code_bucket, default_scripts_s3_key, temp_path)
        logger.info(f"{CONST_DEFAULT_SCRIPTS_FILE_NANE} downloaded from S3..")
        temp_uuid = str(uuid.uuid4())
        # Extract contents of zip
        my_zip = open(temp_path, "rb")
        try:
            zip_file = zipfile.ZipFile(my_zip)
            total_uncompressed_size = sum(file.file_size for file in zip_file.infolist())
            if total_uncompressed_size > ZIP_MAX_SIZE:
                error_msg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE/1e+6}MBs.'
                logger.info(error_msg)
            zip_file.extractall(tempfile.gettempdir() + '/default_scripts/')    # NOSONAR This size of the file is in control
            logger.info(f"{CONST_DEFAULT_SCRIPTS_FILE_NANE} unzip completed")
        except (IOError, zipfile.BadZipfile) as e:
            error_msg = 'Invalid zip file.'
            logger.info(error_msg)

        # get list of scripts already uploaded
        get_scripts_event =  {
                    'httpMethod': 'GET'
                }
        logger.info("Getting list of existing scripts..")
        all_scripts_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-scripts',
                                                InvocationType='RequestResponse',
                                                Payload=json.dumps(get_scripts_event, cls=JsonEncoder))
        all_scripts_response_payload = json.loads(all_scripts_response['Payload'].read())

        script_package_uuid_mapping = {}
        all_scripts_response_body = json.loads(all_scripts_response_payload['body'])

        script_package_uuid_mapping = dict(jmespath.search("[?version=='0'].[script_name, package_uuid]", all_scripts_response_body))
        logger.info(f"Mapping of script name and package_uuid: {script_package_uuid_mapping}")
        directory = os.fsencode(temp_directory_name)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            fullpath = temp_directory_name + filename
            logger.info(fullpath)

            if not os.path.isdir(fullpath):
                # Get script name from Package-Structure.yml in ZIP file.
                script_name = get_script_name_from_script_zip(temp_directory_name, filename)
                logger.info(f"Script name from Package-Structure.yml in zip {filename} is: {script_name}")

                with open(fullpath, 'rb') as script_zip_read:
                    zip_content = script_zip_read.read()
                    script_zip_encoded = base64.b64encode(zip_content)
                    script_zip_read.close()
                package_uuid = script_package_uuid_mapping.get(script_name)
                logger.info(f"Existing package uuid for script {script_name} is: {package_uuid}")
                scripts_event = None
                if (package_uuid is None or package_uuid == ""):
                    logger.info("Existing package uuid is None, uploading a new script..")
                    scripts_event = {
                        'httpMethod': 'POST',
                        'body': json.dumps({
                        'script_file': script_zip_encoded
                        }, cls=JsonEncoder)
                    }
                else:
                    logger.info("Existing package_uuid is not None, uploading as new version..")
                    scripts_event = {
                        'httpMethod': 'PUT',
                        'pathParameters': {
                            'scriptid': package_uuid
                        },
                        'body': json.dumps({
                        'action': 'update_package',
                        'script_file': script_zip_encoded
                        }, cls=JsonEncoder)
                    }
                scripts_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-scripts',
                                                InvocationType='RequestResponse',
                                                Payload=json.dumps(scripts_event, cls=JsonEncoder))

                # Decode return payload message and print to logger.
                scripts_response_payload = scripts_response['Payload']
                scripts_response_payload_text = scripts_response_payload.read()
                logger.info(scripts_response_payload_text)

        cleanup_temp(temp_uuid)
    except Exception as e:
        print(e)
        logger.info('FAILED!')
        logger.info(e)


def upgrade_scripts():
    all_scripts = get_all_ddb_table_items(scripts_table_name)
    client_ddb = cmf_boto.client('dynamodb')

    for script in all_scripts:
        if ("lambda_function_name_suffix" not in script or "type" not in script) and (script.get("type", {}).get("S", None) != "Manual"):
            logger.info(f'Upgrading script "{script["script_name"]["S"]}" version {script["version"]["N"]} to v4, using default of type=Automated and lambda_function_name_suffix=ssm')
            script["lambda_function_name_suffix"] = {"S": "ssm"}
            script["type"] = {"S": "Automated"}

            client_ddb.put_item(
                TableName=scripts_table_name,
                Item=script
            )


def get_all_ddb_table_items(ddb_table_name):
    client_ddb = cmf_boto.client('dynamodb')
    response = client_ddb.scan(
        TableName=ddb_table_name,
        ConsistentRead=True
    )
    ddb_table_items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = client_ddb.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        ddb_table_items.extend(response['Items'])

    return ddb_table_items


def lambda_handler(event, context):

    try:
        logger.info('Event:\n {}'.format(event))
        logger.info('Context:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            logger.info('Create action')
            import_script_packages()
            status = 'SUCCESS'
            message = 'Default script packages loaded successfully'

        elif event['RequestType'] == 'Update':
            logger.info('Update action')
            upgrade_scripts()
            import_script_packages()
            status = 'SUCCESS'
            message = 'No update required'

        elif event['RequestType'] == 'Delete':
            logger.info('Delete action')
            status = 'SUCCESS'
            message = 'No deletion required'

        else:
            logger.info('SUCCESS!')
            status = 'SUCCESS'
            message = 'Unexpected event received from CloudFormation'

    except Exception as e:
        logger.info('FAILED!')
        logger.info(e)
        status = 'FAILED'
        message = 'Exception during processing'
        traceback.print_exc()

    response_data = {'Message': message}
    response = respond(event, context, status, response_data)

    return {
        'Response': response
    }
