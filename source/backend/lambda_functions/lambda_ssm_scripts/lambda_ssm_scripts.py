import datetime
import boto3
import json
import base64
import zipfile
import os
import yaml
import uuid
import shutil
import logging
import tempfile
from policy import MFAuth
from boto3.dynamodb.conditions import Key
from decimal import Decimal

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; "
                               "connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; "
                               "font-src 'self' data:; form-action 'self';"
}

script_package_yaml_file_name = "Package-Structure.yml"
log_invocation_message_prefix = 'Invocation: %s, '


class MissingDependencyException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the custom message
        super().__init__(message)


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


bucketName = os.environ['scripts_bucket_name']
application = os.environ['application']
environment = os.environ['environment']

s3_resource = boto3.resource('s3')
s3 = boto3.client('s3')

packages_table = boto3.resource('dynamodb').Table(os.environ['scripts_table'])
# Set maximum size of uncompressed file to 500MBs.
# This is just under the /tmp max size of 512MB in Lambda.
ZIP_MAX_SIZE = 500000000


def add_script_attribute_to_schema(update_exists_attribute, new_attr):
    logging_context = 'add_script_attribute_to_schema'
    if update_exists_attribute:
        schema_method = 'PUT'
        attribute_action = 'update'
    else:
        schema_method = 'POST'
        attribute_action = 'new'
    lambda_client = boto3.client('lambda')
    data = {
        "event": schema_method,
        "name": new_attr['name'],
        attribute_action: new_attr
    }

    scripts_event = {'httpMethod': 'PUT', 'body': json.dumps(data),
                     'pathParameters': {'schema_name': new_attr['schema']}}

    scripts_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-schema',
                                            InvocationType='RequestResponse',
                                            Payload=json.dumps(scripts_event))

    scripts_response_pl = scripts_response['Payload'].read()

    scripts = json.loads(scripts_response_pl)

    if 'statusCode' in scripts and scripts['statusCode'] != 200 and 'already exist' in scripts['body']:
        print(scripts['body'] + ' in schema ' + new_attr['schema'] + ' , performing update...')
        update_result = add_script_attribute_to_schema(True, new_attr)
        if not update_result:
            return update_result
    elif 'statusCode' in scripts and scripts['statusCode'] != 200:
        return scripts['body']
    elif 'body' in scripts and 'ResponseMetadata' in scripts['body']:
        lambda_response = json.loads(scripts['body'])
        if 'ResponseMetadata' in lambda_response:
            if 'HTTPStatusCode' in lambda_response['ResponseMetadata'] \
                and lambda_response['ResponseMetadata']['HTTPStatusCode'] != 200:
                return scripts['body']

    logger.info('Invocation: %s, Attribute added/updated in schema: ' + json.dumps(new_attr), logging_context)

    return None


def process_schema_extensions(script, update=False):
    no_errors = True
    errors = []
    if script.get("SchemaExtensions"):
        # Load any new attributes into the schema
        for script_schema_attribute in script.get("SchemaExtensions"):
            process_schema_extension_attribute_resp = add_script_attribute_to_schema(update, script_schema_attribute)
            if process_schema_extension_attribute_resp is not None:
                no_errors = False
                errors.append(process_schema_extension_attribute_resp)
    return no_errors, errors


def cleanup_temp(package_uuid):
    # Delete temp package files in /tmp/ to ensure that large files are not left hanging around for
    # longer than required.
    if os.path.exists(tempfile.gettempdir() + "/" + package_uuid + ".zip"):
        os.remove(tempfile.gettempdir() + "/" + package_uuid + ".zip")

    if os.path.exists(tempfile.gettempdir() + "/" + package_uuid):
        shutil.rmtree(tempfile.gettempdir() + "/" + package_uuid, ignore_errors=True)


def get_all_default_scripts():
    response = packages_table.query(
        IndexName='version-index',
        KeyConditionExpression=Key('version').eq(0)
    )
    if response["Count"] == 0:
        return {
            "Count": 0,
            "Items": []
        }

    scripts = response['Items']
    while 'LastEvaluatedKey' in response:
        response = packages_table.query(
            IndexName='version-index',
            KeyConditionExpression=Key('version').eq(0),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        scripts.extend(response['Items'])

    return {
        "Count": len(scripts),
        "Items": scripts
    }


def get_script_version(pk, sk):
    return packages_table.get_item(Key={
        'package_uuid': pk,
        'version': sk
    })


def get_scripts(pk):
    return packages_table.query(
        KeyConditionExpression=Key('package_uuid').eq(pk)
    )


# Validate that a key is present in the attribute object.
def check_attribute_key(attribute, key):
    if key not in attribute:
        return f"Attribute '{key}' not provided and is required"
    elif attribute.get('name') == "":
        return f"Attribute key: '{key}' cannot be empty"

    return None


# Validate an attribute has all required keys.
def valid_attribute(attribute):
    validation_errors = []
    # Minimum required keys for a valid attribute in the CMF Schema to allow display in the UI and record functions.
    required_attribute_keys = ['name', 'description', 'type']

    # Check top level keys exist for valid attribute.
    for required_attribute_key in required_attribute_keys:
        error_message = check_attribute_key(attribute, required_attribute_key)
        if error_message is not None:
            validation_errors.append(error_message)

    if len(validation_errors) > 0:
        return validation_errors

    # Perform second level checking on type specific attributes.
    if attribute['type'] == 'list':
        error_message = check_attribute_key(attribute, 'listvalue')
        if error_message is not None:
            validation_errors.append(error_message)

    if len(validation_errors) > 0:
        return validation_errors

    return None


def change_default_script_version(event, package_uuid, default_version):
    logging_context = 'make_default'
    # Update record audit
    auth = MFAuth()
    auth_response = auth.getUserResourceCreationPolicy(event, 'script')

    if auth_response['action'] != 'allow':
        logger.warning(log_invocation_message_prefix + 'Authorisation failed: ' + json.dumps(auth_response), logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': auth_response['cause']}

    if 'user' not in auth_response:
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': f"No user details found from auth. {auth_response['cause']}"}

    db_response = get_script_version(package_uuid, default_version)

    if 'Item' not in db_response:
        error_msg = f"The requested version does not exist for the script {package_uuid}."
        logger.error(log_invocation_message_prefix + error_msg,
                     logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': error_msg}

    last_modified_by = auth_response['user']
    last_modified_timestamp = datetime.datetime.utcnow().isoformat()

    default_item = db_response["Item"]

    packages_table.update_item(
        Key={
            'package_uuid': package_uuid,
            'version': 0
        },
        # Atomic counter is used to increment the latest version
        UpdateExpression='SET #default = :default, ' \
                         '#version_id = :version_id, ' \
                         '#_history.#lastModifiedTimestamp = :lastModifiedTimestamp, ' \
                         '#_history.#lastModifiedBy = :lastModifiedBy, ' \
                         '#script_masterfile = :script_masterfile, ' \
                         '#script_description = :script_description, ' \
                         '#script_update_url = :script_update_url, ' \
                         '#script_group = :script_group, ' \
                         '#script_name = :script_name, ' \
                         '#script_dependencies = :script_dependencies, ' \
                         '#script_arguments = :script_arguments ',
        ExpressionAttributeNames={
            '#default': 'default',
            '#version_id': 'version_id',
            '#_history': '_history',
            '#lastModifiedTimestamp': 'lastModifiedTimestamp',
            '#lastModifiedBy': 'lastModifiedBy',
            '#script_masterfile': 'script_masterfile',
            '#script_description': 'script_description',
            '#script_update_url': 'script_update_url',
            '#script_group': 'script_group',
            '#script_name': 'script_name',
            '#script_dependencies': 'script_dependencies',
            '#script_arguments': 'script_arguments'
        },
        ExpressionAttributeValues={
            ':default': default_version,
            ':version_id': default_item['version_id'],
            ':lastModifiedBy': last_modified_by,
            ':lastModifiedTimestamp': last_modified_timestamp,
            ':script_masterfile': default_item['script_masterfile'],
            ':script_description': default_item['script_description'],
            ':script_update_url': default_item['script_update_url'],
            ':script_group': default_item['script_group'],
            ':script_name': default_item['script_name'],
            ':script_dependencies': default_item['script_dependencies'],
            ':script_arguments': default_item['script_arguments']
        },
    )

    return {
        'headers': {
            **default_http_headers
        },
        'body': f"Default version changed to: {default_version}",
        'statusCode': 200
    }


def does_script_name_exist(script_name, existing_package_uuid=None):
    default_list = get_all_default_scripts()

    def script_name_filter(script):
        if existing_package_uuid and script["package_uuid"] != existing_package_uuid:
            return script['script_name']

    if default_list["Count"] != 0:
        default_list = default_list["Items"]
        script_name_list = list(map(script_name_filter, default_list))
        if script_name in script_name_list:
            return True

    return False


def extract_script_package(base64_encoded_script_package, package_uuid):
    logging_context = 'extract_script_package'

    temp_path = tempfile.gettempdir() + "/" + package_uuid + ".zip"
    script_package_path = tempfile.gettempdir() + "/" + package_uuid

    # Package path to save the uploaded file
    split_data = base64_encoded_script_package.split(',')  # Split data to allow removal of DataURL if present.
    if len(split_data) == 1:
        decoded_data_as_bytes = base64.b64decode(
            split_data[0])  # Decode Base64 to bytes data does not include DataURL header.
    elif len(split_data) == 2:
        decoded_data_as_bytes = base64.b64decode(split_data[1])  # Decode Base64 to bytes
    else:
        cleanup_temp(package_uuid)
        error_msg = 'Zip file is not able to be decoded.'
        logger.error(log_invocation_message_prefix + error_msg,
                     logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': error_msg}

    # Convert binary as UTF-8 --> Binary file
    with open(temp_path, "wb") as text_file:
        text_file.write(decoded_data_as_bytes)
        text_file.close()

    try:
        # Extract contents of zip
        with open(temp_path, "rb") as script_package_zip_file:
            script_package_zip = zipfile.ZipFile(script_package_zip_file)
            total_uncompressed_size = sum(file.file_size for file in script_package_zip.infolist())
        if total_uncompressed_size > ZIP_MAX_SIZE:
            cleanup_temp(package_uuid)
            error_msg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE / 1e+6}MBs.'
            logger.error(log_invocation_message_prefix + error_msg,
                         logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': error_msg}
        else:
            with open(temp_path, "rb") as script_package_zip_file:
                script_package_zip = zipfile.ZipFile(script_package_zip_file)
                script_package_zip.extractall(script_package_path)
            return {'headers': {**default_http_headers},
                'statusCode': 200,
                'body':
                    {'statusMessage': f"Files extracted to {script_package_path}",
                     'scriptPath': script_package_path,
                     'decodedData': decoded_data_as_bytes
                     }
                }
    except (IOError, zipfile.BadZipfile):
        cleanup_temp(package_uuid)
        error_msg = 'Invalid zip file.'
        logger.error(log_invocation_message_prefix + error_msg,
                     logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': error_msg}


def check_script_package_dependencies_exist(package_script_path, file_dependencies):
    if file_dependencies:
        missing_files = []
        for dependency in file_dependencies:
            if os.path.isfile(f"{package_script_path}/{dependency}") is False:
                missing_files.append(dependency)

        if len(missing_files) > 0:
            raise MissingDependencyException("The following dependencies do not exist in the package: " +
                                             " ".join(missing_files))


def check_script_package_master_file_exists(package_script_path, master_filename):
    return os.path.isfile(f"{package_script_path}/{master_filename}")


def validate_script_package_yaml(parsed_yaml_file):
    validation_errors = []
    required_keys = ['Name', 'Description', 'MasterFileName']

    # Check top level keys exist for valid attribute.
    for required_key in required_keys:
        error_message = check_attribute_key(parsed_yaml_file, required_key)
        if error_message is not None:
            validation_errors.append(error_message)

    return validation_errors


def validate_extracted_script_package(script_package_path):
    validation_failures = []
    if os.path.isfile(f"{script_package_path}/{script_package_yaml_file_name}"):
        # validate further.
        config_file_path = f"{script_package_path}/{script_package_yaml_file_name}"
        try:
            with open(config_file_path) as config_file:
                parsed_yaml_file = yaml.full_load(config_file)
        except yaml.YAMLError as error_yaml:
            if hasattr(error_yaml, 'problem_mark'):
                mark = error_yaml.problem_mark
                validation_failures.append(f"Error reading error YAML {script_package_yaml_file_name}. "
                                           f"Error position: {mark.line + 1}:{mark.column + 1}")
            else:
                validation_failures.append(f"Error reading error YAML {script_package_yaml_file_name}.")
        else:

            package_yaml_validation = validate_script_package_yaml(parsed_yaml_file)
            if len(package_yaml_validation) > 0:
                validation_failures.append(f"Missing the following required keys or values in "
                                           f"{script_package_yaml_file_name}, {','.join(package_yaml_validation)}")
            else:
                master_file_exists = check_script_package_master_file_exists(script_package_path,
                                                                             parsed_yaml_file.get("MasterFileName"))
                if master_file_exists is False:
                    validation_failures.append(f"{parsed_yaml_file.get('MasterFileName')} "
                                               f"not found in root of package, "
                                               f"and is referenced as the MasterFileName.")
                try:
                    check_script_package_dependencies_exist(script_package_path, parsed_yaml_file.get("Dependencies"))
                except MissingDependencyException as missing_dependency_error:
                    validation_failures.append(str(missing_dependency_error))

    else:
        validation_failures.append(f"{script_package_yaml_file_name} not found in root of package, this is required.")

    return validation_failures


def load_script_package(event, package_uuid, body, decoded_data_as_byte, new_version=False):
    logging_context = 'load_script_package'
    s3_path = f'scripts/{package_uuid}.zip'

    # Get and load the configuration file from the extracted zip
    config_file_path = f"{tempfile.gettempdir()}/{package_uuid}/{script_package_yaml_file_name}"
    try:
        with open(config_file_path) as config_file:
            parsed_yaml_file = yaml.full_load(config_file)
    except yaml.YAMLError as error_yaml:
        if hasattr(error_yaml, 'problem_mark'):
            mark = error_yaml.problem_mark
            error_msg = f"Error reading error YAML {script_package_yaml_file_name}. " \
                        f"Error position: {mark.line + 1}:{mark.column + 1}"
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': error_msg}
        else:
            error_msg = f"Error reading error YAML {script_package_yaml_file_name}."
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': error_msg}

    # Check if script_name in body
    if 'script_name' in body:
        if body['script_name'] == "" or body['script_name'] is None:
            error_msg = 'Script name provided cannot be empty.'
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': error_msg}
        else:
            script_name = body['script_name']
    else:
        if 'Name' in parsed_yaml_file:
            script_name = parsed_yaml_file.get('Name')
        else:
            error_msg = 'Either script_name in body or Name in Package-Structure.yaml is required.'
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': error_msg}

    if does_script_name_exist(script_name, package_uuid):
        error_msg = 'Script name already defined in another package'
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': error_msg}

    cleanup_temp(package_uuid)

    # Use decoded data and store in S3 bucket
    s3_response = s3.put_object(Bucket=bucketName, Key=s3_path, Body=decoded_data_as_byte)

    # create record audit.
    auth = MFAuth()
    auth_response = auth.getUserResourceCreationPolicy(event, 'script')

    # Check that auth is successful or that this is not an invocation from the system so authentication not req.
    if auth_response['action'] != 'allow' and 'headers' in event:
        logger.warning('Invocation: %s, Authorisation failed: ' + json.dumps(auth_response), logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': auth_response['cause']}

    if 'user' in auth_response:
        created_by = auth_response['user']
        created_timestamp = datetime.datetime.utcnow().isoformat()
    else:
        created_by = {'userRef': '[system]', 'email': '[system]'}
        created_timestamp = datetime.datetime.utcnow().isoformat()

    script_arguments_validation = []
    for script_argument_idx, script_argument_attribute in enumerate(parsed_yaml_file.get("Arguments")):
        attribute_validation_result = valid_attribute(script_argument_attribute)
        if attribute_validation_result:
            script_arguments_validation.append(
                {f'attribute {script_argument_idx} errors': attribute_validation_result}
            )

    if len(script_arguments_validation) > 0:
        cleanup_temp(package_uuid)
        logger.error(log_invocation_message_prefix + json.dumps({'errors': [script_arguments_validation]}),
                     logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [script_arguments_validation]})}

    if new_version:
        updated_master_script_package = increment_script_package_version(package_uuid, auth_response)
        script_package_version = updated_master_script_package["Attributes"]["latest"]
    else:
        script_package_version = 1
        # Define package metadata
        package_data = {
            "package_uuid": package_uuid,
            "version": 0,
            "latest": 1,
            "default": 1,
            "version_id": s3_response["VersionId"],
            "script_masterfile": parsed_yaml_file.get("MasterFileName"),
            "script_description": parsed_yaml_file.get("Description"),
            "script_update_url": parsed_yaml_file.get('UpdateUrl'),
            "script_group": parsed_yaml_file.get('Group'),
            "script_name": script_name,
            "script_dependencies": parsed_yaml_file.get("Dependencies"),
            "script_arguments": parsed_yaml_file.get("Arguments"),
            "_history": {"createdBy": created_by,
                         "createdTimestamp": created_timestamp}
        }

        packages_table.put_item(
            Item=package_data,
        )

    # Define attributes for new item
    script_data = {
        "package_uuid": package_uuid,
        "version": script_package_version,
        "version_id": s3_response["VersionId"],
        "script_masterfile": parsed_yaml_file.get("MasterFileName"),
        "script_description": parsed_yaml_file.get("Description"),
        "script_update_url": parsed_yaml_file.get('UpdateUrl'),
        "script_group": parsed_yaml_file.get('Group'),
        "script_name": script_name,
        "script_dependencies": parsed_yaml_file.get("Dependencies"),
        "script_arguments": parsed_yaml_file.get("Arguments"),
        "_history": {"createdBy": created_by,
                     "createdTimestamp": created_timestamp}
    }

    packages_table.put_item(Item=script_data)

    extensions_result, extension_errors = process_schema_extensions(parsed_yaml_file)

    if not extensions_result:
        # Schema extension failed.
        cleanup_temp(package_uuid)
        error_msg = 'Schema extensions failed to be applied, errors are: ' + json.dumps(extension_errors)
        logger.error(log_invocation_message_prefix + error_msg,
                     logging_context)

        return {'headers': {**default_http_headers},
                'statusCode': 409, 'body': error_msg}

    if '__make_default' in body and body['__make_default']:
        make_default_response = change_default_script_version(event, package_uuid, script_data["version"])
        if make_default_response.get('statusCode') != 200:
            return make_default_response

    return {
        'headers': {
            **default_http_headers
        },
        'body': script_name + " package successfully uploaded with uuid: " + package_uuid,
        'statusCode': 200
    }


def delete_script_package(event, package_uuid):
    logging_context = 'delete_script_package'

    auth = MFAuth()
    auth_response = auth.getUserResourceCreationPolicy(event, 'script')

    if auth_response['action'] != 'allow':
        logger.warning('Invocation: %s, Authorisation failed: ' + json.dumps(auth_response), logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': auth_response['cause']}

    scan = packages_table.query(KeyConditionExpression=Key('package_uuid').eq(package_uuid))

    if scan['Count'] != 0:
        with packages_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'package_uuid': item['package_uuid'], 'version': item['version']})
        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': 'Package ' + package_uuid + " was successfully deleted"}
    else:
        error_msg = 'Package ' + package_uuid + ' does not exist'
        logger.error(log_invocation_message_prefix + error_msg,
                     logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': error_msg}


def increment_script_package_version(package_uuid, user_auth):
    if 'user' in user_auth:
        last_modified_by = user_auth['user']
        last_modified_timestamp = datetime.datetime.utcnow().isoformat()
    else:
        return None

    db_response = packages_table.update_item(
        Key={
            'package_uuid': package_uuid,
            'version': 0
        },
        # Atomic counter is used to increment the latest version
        UpdateExpression='SET latest = latest + :incrval, '
                         '#_history.#lastModifiedTimestamp = :lastModifiedTimestamp, '
                         '#_history.#lastModifiedBy = :lastModifiedBy',
        ExpressionAttributeNames={
            '#_history': '_history',
            '#lastModifiedTimestamp': 'lastModifiedTimestamp',
            '#lastModifiedBy': 'lastModifiedBy'
        },
        ExpressionAttributeValues={
            ':lastModifiedBy': last_modified_by,
            ':lastModifiedTimestamp': last_modified_timestamp,
            ':incrval': 1
        },
        # return the affected attribute after the update
        ReturnValues='UPDATED_NEW'
    )

    return db_response


def lambda_handler(event, context):
    logging_context = event['httpMethod']
    logger.info('Invocation: %s', logging_context)
    if event['httpMethod'] == 'GET':
        response = []
        # GET all default versions
        if 'pathParameters' not in event or event['pathParameters'] is None:
            db_response = get_all_default_scripts()

            if db_response["Count"] == 0:
                return {'headers': {**default_http_headers},
                        'body': json.dumps(response)}

            response = sorted(db_response["Items"], key=lambda d: d['script_name'])

        elif 'scriptid' in event['pathParameters'] and 'version' in event['pathParameters'] and 'action' in event[
            'pathParameters']:
            db_response = get_script_version(event['pathParameters']['scriptid'],
                                             int(event['pathParameters']['version']))

            if 'Item' not in db_response:
                return {'headers': {**default_http_headers},
                        'body': json.dumps(db_response)}

            if event['pathParameters']['action'] == 'download':
                logger.info('Invocation: %s, download script requested.', logging_context)

                package_uuid = event['pathParameters']['scriptid']
                package_zip_key = 'scripts/' + package_uuid + '.zip'

                if 'version_id' in db_response['Item']:
                    # Version id present get specific version from S3.
                    logger.debug('Invocation: %s, downloading version: ' + db_response['Item'][
                        'version_id'] + ' of script: ' + package_zip_key, logging_context)
                    s3_object = s3.get_object(Bucket=bucketName, Key='scripts/' + package_uuid + '.zip',
                                              VersionId=db_response['Item']['version_id'])
                else:
                    # version id not present, get current active version.
                    logger.debug(
                        'Invocation: %s, downloading current version of script: ' + package_zip_key,
                        logging_context)
                    s3_object = s3.get_object(Bucket=bucketName, Key=package_zip_key)
                streaming_body = s3_object["Body"]

                logger.debug('Invocation: %s, reading S3 object into memory.', logging_context)
                zip_content = streaming_body.read()
                logger.debug('Invocation: %s, encoding S3 object, script package to base64.', logging_context)
                script_zip_encoded = base64.b64encode(zip_content)

                scripts_event = {
                    'script_name': db_response['Item']['script_name'],
                    'script_version': event['pathParameters']['version'],
                    'script_file': script_zip_encoded
                }

                response = scripts_event
                logger.info('Invocation: %s, script download response built successfully.', logging_context)

            else:
                response.append(db_response["Item"])

        # GET single version
        elif 'scriptid' in event['pathParameters'] and 'version' in event['pathParameters']:
            logger.info('Invocation: %s, processing request for version:' + event['pathParameters']['version'],
                        logging_context)
            db_response = get_script_version(event['pathParameters']['scriptid'],
                                             int(event['pathParameters']['version']))

            if 'Item' not in db_response:
                return {'headers': {**default_http_headers},
                        'body': json.dumps(response)}

            response.append(db_response["Item"])

        # GET all versions
        elif 'scriptid' in event['pathParameters']:
            logger.info('Invocation: %s, processing request for all versions.',
                        logging_context)
            db_response = get_scripts(event['pathParameters']['scriptid'])
            if db_response["Count"] == 0:
                return {'headers': {**default_http_headers},
                        'body': json.dumps(response)}

            response = db_response["Items"]

        return {'headers': {**default_http_headers},
                'body': json.dumps(response, cls=JsonEncoder)}

    elif event['httpMethod'] == 'POST':
        # Create uuid for this upload, this is required as if multiple of
        # files are being loaded they share the same tmp directory before being cleared.
        package_uuid = str(uuid.uuid4())

        # Set variables
        body = json.loads(event.get('body'))

        extract_script_package_response = extract_script_package(body['script_file'], package_uuid)

        if extract_script_package_response.get('statusCode') != 200:
            return extract_script_package_response

        validate_script_resp = validate_extracted_script_package(extract_script_package_response.get('body')
                                                                 .get('scriptPath'))
        if len(validate_script_resp) != 0:
            cleanup_temp(package_uuid)
            logger.error(log_invocation_message_prefix + ','.join(validate_script_resp),
                         logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': ','.join(validate_script_resp)}

        load_script_response = load_script_package(event,
                                                   package_uuid,
                                                   body,
                                                   extract_script_package_response
                                                   .get('body')
                                                   .get('decodedData'))

        return load_script_response

    elif event['httpMethod'] == 'PUT':
        # Set variables
        package_uuid = event['pathParameters']['scriptid']

        body = json.loads(event.get('body'))

        if body['action'] == 'update_package':
            logger.debug('Invocation: %s, update package processing started.', logging_context)

            extract_script_package_response = extract_script_package(body['script_file'], package_uuid)

            if extract_script_package_response.get('statusCode') != 200:
                return extract_script_package_response

            validate_script_resp = validate_extracted_script_package(extract_script_package_response.get('body')
                                                                     .get('scriptPath'))
            if len(validate_script_resp) != 0:
                cleanup_temp(package_uuid)
                logger.error(log_invocation_message_prefix + ','.join(validate_script_resp),
                             logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': ','.join(validate_script_resp)}

            load_script_response = load_script_package(
                event,
                package_uuid,
                body,
                extract_script_package_response
                .get('body')
                .get('decodedData'),
                True)

            return load_script_response

        elif body['action'] == 'update_default':
            logger.debug('Invocation: %s, updating default version of package. UUID:' +
                         event['pathParameters']['scriptid'], logging_context)

            make_default_response = change_default_script_version(event, package_uuid, int(body['default']))

            return make_default_response

        else:
            error_msg = 'Script update action is not supported.'
            logger.error(log_invocation_message_prefix + error_msg,
                         logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': error_msg}

    elif event['httpMethod'] == 'DELETE':
        logger.debug('Invocation: %s, deleting package version. UUID:' +
                     event['pathParameters']['scriptid'], logging_context)
        package_uuid = event['pathParameters']['scriptid']

        return delete_script_package(event, package_uuid)
