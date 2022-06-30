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

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

from policy import MFAuth
from boto3.dynamodb.conditions import Key
from decimal import Decimal


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

ZIP_MAX_SIZE = 500000000  # Set maximum size of uncompressed file to 500MBs. This is just under the /tmp max size of 512MB in Lambda.


def process_schema_extensions(script, update=False):
    if update:
        schema_method = 'PUT'
        attribute_action = 'update'
    else:
        schema_method = 'POST'
        attribute_action = 'new'
    no_errors = True
    errors = []
    if script.get("SchemaExtensions"):
        # Load any new attributes into the schema
        lambda_client = boto3.client('lambda')
        for new_attr in script.get("SchemaExtensions"):
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

            print(scripts)
            if 'statusCode' in scripts and scripts['statusCode'] != 200 and 'already exist' in scripts['body']:
                print(scripts['body'] + ' in schema ' + new_attr['schema'] + ' , performing update...')
                update_result, update_errors = process_schema_extensions(script, True)
                if not update_result:
                    no_errors = False
                    errors.extend(update_errors)
            elif 'statusCode' in scripts and scripts['statusCode'] != 200:
                no_errors = False
                errors.append(scripts['body'])
            elif 'body' in scripts and 'ResponseMetadata' in scripts['body']:
                lambda_response = json.loads(scripts['body'])
                if 'ResponseMetadata' in lambda_response:
                    if 'HTTPStatusCode' in lambda_response['ResponseMetadata'] and lambda_response['ResponseMetadata']['HTTPStatusCode'] != 200:
                        no_errors = False
                        errors.append(scripts['body'])
    return no_errors, errors


def cleanup_temp(packageUUID):
    # Delete temp package files in /tmp/ to ensure that large files are not left hanging around for longer than required.
    if os.path.exists("/tmp/" + packageUUID + ".zip"):
        os.remove("/tmp/" + packageUUID + ".zip")

    if os.path.exists("/tmp/" + packageUUID):
        shutil.rmtree("/tmp/" + packageUUID, ignore_errors=True)


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


def make_default(event, packageUUID, default_item, default_version):
    # Update record audit
    auth = MFAuth()
    authResponse = auth.getUserAttributePolicy(event, 'script')

    if 'user' in authResponse:
        lastModifiedBy = authResponse['user']
        lastModifiedTimestamp = datetime.datetime.utcnow().isoformat()

    packages_table.update_item(
        Key={
            'package_uuid': packageUUID,
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
            '#script_name': 'script_name',
            '#script_dependencies': 'script_dependencies',
            '#script_arguments': 'script_arguments'
        },
        ExpressionAttributeValues={
            ':default': default_version,
            ':version_id': default_item['version_id'],
            ':lastModifiedBy': lastModifiedBy,
            ':lastModifiedTimestamp': lastModifiedTimestamp,
            ':script_masterfile': default_item['script_masterfile'],
            ':script_description': default_item['script_description'],
            ':script_update_url': default_item['script_update_url'],
            ':script_name': default_item['script_name'],
            ':script_dependencies': default_item['script_dependencies'],
            ':script_arguments': default_item['script_arguments']
        },
    )


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
                temp_uuid = str(uuid.uuid4())
                temp_path = "/tmp/" + temp_uuid + ".zip"

                package_uuid = event['pathParameters']['scriptid']

                if 'version_id' in db_response['Item']:
                    # Version id present get specific version from S3.
                    logger.debug('Invocation: %s, downloading version: ' + db_response['Item']['version_id'] + ' of script: ' + 'scripts/' + package_uuid + '.zip', logging_context)
                    s3_object = s3.get_object(Bucket=bucketName, Key='scripts/' + package_uuid + '.zip', VersionId=db_response['Item']['version_id'])
                else:
                    # version id not present, get current active version.
                    logger.debug('Invocation: %s, downloading current version of script: ' + 'scripts/' + package_uuid + '.zip', logging_context)
                    s3_object = s3.get_object(Bucket=bucketName, Key='scripts/' + package_uuid + '.zip')
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
        # Create uuid for this upload, this is required as if multiple of files are being loaded they share the same tmp directory before being cleared.
        packageUUID = str(uuid.uuid4())

        # Set variables
        body = json.loads(event.get('body'))

        tempPath = "/tmp/" + packageUUID + ".zip"
        s3Path = f'scripts/{packageUUID}.zip'

        # Package path to save the uploaded file
        splitData = body['script_file'].split(',')  # Split data to allow removal of DataURL if present.
        if len(splitData) == 1:
            decodedDataAsBytes = base64.b64decode(
                splitData[0])  # Decode Base64 to bytes data does not include DataURL header.
        elif len(splitData) == 2:
            decodedDataAsBytes = base64.b64decode(splitData[1])  # Decode Base64 to bytes
        else:
            cleanup_temp(packageUUID)
            errorMsg = 'Zip file is not able to be decoded.'
            logger.error('Invocation: %s, ' + errorMsg,
                         logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': errorMsg}

        # Convert binary as UTF-8 --> Binary file
        textFile = open(tempPath, "wb")
        textFile.write(decodedDataAsBytes)
        textFile.close()

        # Extract contents of zip
        myZip = open(tempPath, "rb")
        try:
            zip = zipfile.ZipFile(myZip)
            total_uncompressed_size = sum(file.file_size for file in zip.infolist())
            if total_uncompressed_size > ZIP_MAX_SIZE:
                cleanup_temp(packageUUID)
                errorMsg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE / 1e+6}MBs.'
                logger.error('Invocation: %s, ' + errorMsg,
                             logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': errorMsg}
            zip.extractall("/tmp/" + packageUUID)
        except (IOError, zipfile.BadZipfile) as e:
            cleanup_temp(packageUUID)
            errorMsg = 'Invalid zip file.'
            logger.error('Invocation: %s, ' + errorMsg,
                         logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': errorMsg}

        # Check if yaml file exist
        if os.path.isfile('/tmp/' + packageUUID + '/Package-Structure.yml'):
            # Get and load the configuration file from the extracted zip
            configFilePath = "/tmp/" + packageUUID + "/Package-Structure.yml"
            configFile = open(configFilePath)
            parsedYamlFile = yaml.full_load(configFile)

            # Check if script_name in body
            script_name = ''
            if 'script_name' in body:
                if body['script_name'] == "" or body['script_name'] == None:
                    errorMsg = 'Script name provided cannot be empty.'
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': errorMsg}
                else:
                    script_name = body['script_name']
            else:
                if 'Name' in parsedYamlFile:
                    script_name = parsedYamlFile.get('Name')
                else:
                    errorMsg = 'Either script_name in body or Name in Package-Structure.yaml is required.'
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': errorMsg}

            default_list = get_all_default_scripts()

            def script_name_filter(script):
                return script['script_name']

            if default_list["Count"] != 0:
                default_list = default_list["Items"]
                script_name_list = list(map(script_name_filter, default_list))
                errorMsg = ""
                if script_name in script_name_list:
                    errorMsg = 'Script name already defined in another package'
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': errorMsg}

            # Validate if dependencies exist in the package
            dependencies = parsedYamlFile.get("Dependencies")

            if (dependencies):
                missingFiles = []
                for dependency in dependencies:
                    if os.path.isfile('/tmp/' + packageUUID + '/' + dependency["FileName"]) is False:
                        missingFiles.append(dependency["FileName"])

                if len(missingFiles) > 0:
                    cleanup_temp(packageUUID)
                    errorMsg = "The following dependencies do not exist in the package: " + " ".join(missingFiles)
                    logger.error('Invocation: %s, ' + errorMsg,
                                 logging_context)
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': errorMsg}

            cleanup_temp(packageUUID)

            # Use decoded data and store in S3 bucket
            s3_response = s3.put_object(Bucket=bucketName, Key=s3Path, Body=decodedDataAsBytes)

            # create record audit.
            auth = MFAuth()
            authResponse = auth.getUserResourceCreationPolicy(event, 'script')

            if 'user' in authResponse:
                createdBy = authResponse['user']
                createdTimestamp = datetime.datetime.utcnow().isoformat()
            else:
                createdBy = {'userRef': '[system]', 'email': '[system]'}
                createdTimestamp = datetime.datetime.utcnow().isoformat()

            # Define package metadata
            packageData = {}
            packageData["package_uuid"] = packageUUID
            packageData["version"] = 0
            packageData["latest"] = 1
            packageData["default"] = 1
            packageData["version_id"] = s3_response["VersionId"]
            packageData["script_masterfile"] = parsedYamlFile.get("MasterFileName")
            packageData["script_description"] = parsedYamlFile.get("Description")
            packageData["script_update_url"] = parsedYamlFile.get('UpdateUrl')
            packageData["script_name"] = script_name
            packageData["script_dependencies"] = dependencies
            packageData["script_arguments"] = parsedYamlFile.get("Arguments")
            packageData["_history"] = {}
            packageData["_history"]["createdBy"] = createdBy
            packageData["_history"]["createdTimestamp"] = createdTimestamp

            packages_table.put_item(
                Item=packageData,
            )

            # Define attributes for new item
            scriptData = {}
            scriptData["package_uuid"] = packageUUID
            scriptData["version"] = 1
            scriptData["version_id"] = s3_response["VersionId"]
            scriptData["script_masterfile"] = parsedYamlFile.get("MasterFileName")
            scriptData["script_description"] = parsedYamlFile.get("Description")
            scriptData["script_update_url"] = parsedYamlFile.get('UpdateUrl')
            scriptData["script_name"] = script_name
            scriptData["script_dependencies"] = dependencies
            scriptData["script_arguments"] = parsedYamlFile.get("Arguments")
            scriptData["_history"] = {}
            packageData["_history"]["createdBy"] = createdBy
            packageData["_history"]["createdTimestamp"] = createdTimestamp

            packages_table.put_item(Item=scriptData)

            extensions_result, extension_errors = process_schema_extensions(parsedYamlFile)

            if not extensions_result:
                # Schema extension failed.
                cleanup_temp(packageUUID)
                errorMsg = 'Schema extensions failed to be applied, errors are: ' + json.dumps(extension_errors)
                logger.error('Invocation: %s, ' + errorMsg,
                             logging_context)

                return {'headers': {**default_http_headers},
                        'statusCode': 409, 'body': errorMsg}

            return {
                'headers': {
                    **default_http_headers
                },
                'body': script_name + " package successfully uploaded with uuid: " + packageUUID,
                'statusCode': 200
            }

        else:
            cleanup_temp(packageUUID)
            errorMsg = 'Package-Structure.yml not found, invalid script zip package structure.'
            logger.error('Invocation: %s, ' + errorMsg,
                         logging_context)

            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': errorMsg}

    elif event['httpMethod'] == 'PUT':
        # Set variables
        packageUUID = event['pathParameters']['scriptid']

        body = json.loads(event.get('body'))

        tempPath = "/tmp/" + packageUUID + ".zip"
        s3Path = f'scripts/{packageUUID}.zip'

        if body['action'] == 'update_package':
            logger.debug('Invocation: %s, update package processing started.', logging_context)

            # Package path to save the uploaded file
            splitData = body['script_file'].split(',')  # Split data to allow removal of DataURL if present.
            if len(splitData) == 1:
                decodedDataAsBytes = base64.b64decode(
                    splitData[0])  # Decode Base64 to bytes data does not include DataURL header.
            elif len(splitData) == 2:
                decodedDataAsBytes = base64.b64decode(splitData[1])  # Decode Base64 to bytes
            else:
                cleanup_temp(packageUUID)
                errorMsg = 'Zip file is not able to be decoded.'
                logger.error('Invocation: %s, ' + errorMsg,
                             logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': errorMsg}

            # Convert binary as UTF-8 --> Binary file
            textFile = open(tempPath, "wb")
            textFile.write(decodedDataAsBytes)
            textFile.close()

            # Extract contents of zip
            myZip = open(tempPath, "rb")
            try:
                zip = zipfile.ZipFile(myZip)
                total_uncompressed_size = sum(file.file_size for file in zip.infolist())
                if total_uncompressed_size > ZIP_MAX_SIZE:
                    cleanup_temp(packageUUID)
                    errorMsg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE / 1e+6}MBs.'
                    logger.error('Invocation: %s, ' + errorMsg,
                                 logging_context)
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': errorMsg}
                zip.extractall("/tmp/" + packageUUID)
            except (IOError, zipfile.BadZipfile) as e:
                cleanup_temp(packageUUID)
                errorMsg = 'Invalid zip file.'
                logger.error('Invocation: %s, ' + errorMsg,
                             logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': errorMsg}

            # Check if yaml file exist,
            if os.path.isfile('/tmp/' + packageUUID + '/Package-Structure.yml'):
                # Get and load the configuration file from the extracted zip
                configFilePath = "/tmp/" + packageUUID + "/Package-Structure.yml"
                configFile = open(configFilePath)
                parsedYamlFile = yaml.full_load(configFile)

                # Check if script_name in body
                script_name = ''
                if 'script_name' in body:
                    if body['script_name'] == "" or body['script_name'] == None:
                        errorMsg = 'Script name provided cannot be empty.'
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': errorMsg}
                    else:
                        script_name = body['script_name']
                else:
                    if 'Name' in parsedYamlFile:
                        script_name = parsedYamlFile.get('Name')
                    else:
                        errorMsg = 'Either script_name in body or Name in Package-Structure.yaml is required.'
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': errorMsg}

                # Check if script name already used
                def script_name_filter(script):
                    if script["package_uuid"] != event['pathParameters']['scriptid']:
                        return script['script_name']

                default_list = get_all_default_scripts()

                if default_list["Count"] != 0:
                    default_list = default_list["Items"]
                    script_name_list = list(map(script_name_filter, default_list))
                    print(script_name_list)
                    if script_name in script_name_list:
                        errorMsg = 'Script name already defined in another package'
                        logger.error('Invocation: %s, ' + errorMsg,
                                     logging_context)
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': errorMsg}

                # Validate if dependencies exist in the package
                dependencies = parsedYamlFile.get("Dependencies")

                if (dependencies):
                    missingFiles = []
                    for dependency in dependencies:
                        if os.path.isfile('/tmp/' + packageUUID + '/' + dependency["FileName"]) is False:
                            missingFiles.append(dependency["FileName"])

                    if len(missingFiles) > 0:
                        cleanup_temp(packageUUID)
                        errorMsg = "The following dependencies do not exist in the package: " + " ".join(missingFiles)
                        logger.error('Invocation: %s, ' + errorMsg,
                                     logging_context)
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': errorMsg}

                cleanup_temp(packageUUID)

                # Use decoded data and store in S3 bucket
                s3_response = s3.put_object(Bucket=bucketName, Key=s3Path, Body=decodedDataAsBytes)

                # Update record audit
                auth = MFAuth()
                authResponse = auth.getUserAttributePolicy(event, 'script')

                if 'user' in authResponse:
                    lastModifiedBy = authResponse['user']
                    lastModifiedTimestamp = datetime.datetime.utcnow().isoformat()

                db_response = packages_table.update_item(
                    Key={
                        'package_uuid': packageUUID,
                        'version': 0
                    },
                    # Atomic counter is used to increment the latest version
                    UpdateExpression='SET latest = latest + :incrval, #_history.#lastModifiedTimestamp = :lastModifiedTimestamp, #_history.#lastModifiedBy = :lastModifiedBy',
                    ExpressionAttributeNames={
                        '#_history': '_history',
                        '#lastModifiedTimestamp': 'lastModifiedTimestamp',
                        '#lastModifiedBy': 'lastModifiedBy'
                    },
                    ExpressionAttributeValues={
                        ':lastModifiedBy': lastModifiedBy,
                        ':lastModifiedTimestamp': lastModifiedTimestamp,
                        ':incrval': 1
                    },
                    # return the affected attribute after the update
                    ReturnValues='UPDATED_NEW'
                )

                # Define attributes for new item
                scriptData = {}
                scriptData["package_uuid"] = packageUUID
                scriptData["version"] = db_response["Attributes"]["latest"]
                scriptData["version_id"] = s3_response["VersionId"]
                scriptData["script_masterfile"] = parsedYamlFile.get("MasterFileName")
                scriptData["script_description"] = parsedYamlFile.get("Description")
                scriptData["script_update_url"] = parsedYamlFile.get('UpdateUrl')
                scriptData["script_name"] = script_name
                scriptData["script_dependencies"] = dependencies
                scriptData["script_arguments"] = parsedYamlFile.get("Arguments")
                scriptData["_history"] = {}
                scriptData["_history"]["lastModifiedBy"] = lastModifiedBy
                scriptData["_history"]["lastModifiedTimestamp"] = lastModifiedTimestamp

                # Add new item
                packages_table.put_item(Item=scriptData)

                if '__make_default' in body and body['__make_default']:
                    make_default(event, packageUUID, scriptData, scriptData["version"])

                return {
                    'headers': {
                        **default_http_headers
                    },
                    'body': script_name + " package successfully updated.",
                    'statusCode': 200
                }

        elif body['action'] == 'update_default':
            logger.debug('Invocation: %s, updating default version of package. UUID:' +
                         event['pathParameters']['scriptid'], logging_context)
            # Update record audit
            auth = MFAuth()
            authResponse = auth.getUserAttributePolicy(event, 'script')

            if 'user' in authResponse:
                lastModifiedBy = authResponse['user']
                lastModifiedTimestamp = datetime.datetime.utcnow().isoformat()

            db_response = get_script_version(event['pathParameters']['scriptid'], int(body['default']))

            if 'Item' not in db_response:
                errorMsg = "The selected version does not exist in the package"
                logger.error('Invocation: %s, ' + errorMsg,
                             logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': errorMsg}

            default_item = db_response["Item"]

            make_default(event, packageUUID, default_item, body['default'])

            return {
                'headers': {
                    **default_http_headers
                },
                'body': "Default version changed to: " + str(body['default']),
                'statusCode': 200
            }
        else:
            errorMsg = 'Update action is not recognized'
            logger.error('Invocation: %s, ' + errorMsg,
                         logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': errorMsg}

    elif event['httpMethod'] == 'DELETE':
        logger.debug('Invocation: %s, deleting package version. UUID:' +
                     event['pathParameters']['scriptid'], logging_context)
        packageUUID = event['pathParameters']['scriptid']

        scan = packages_table.query(KeyConditionExpression=Key('package_uuid').eq(packageUUID))

        if scan['Count'] != 0:
            with packages_table.batch_writer() as batch:
                for item in scan['Items']:
                    batch.delete_item(Key={'package_uuid': item['package_uuid'], 'version': item['version']})
            return {'headers': {**default_http_headers},
                    'statusCode': 200, 'body': 'Package ' + packageUUID + " was successfully deleted"}
        else:
            errorMsg = 'Package ' + packageUUID + ' does not exist'
            logger.error('Invocation: %s, ' + errorMsg,
                         logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': errorMsg}
