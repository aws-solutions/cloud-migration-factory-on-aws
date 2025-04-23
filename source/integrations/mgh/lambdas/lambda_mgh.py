import csv
import glob
import json
import os
import uuid

from polling2 import TimeoutException, poll
from botocore.vendored import requests
#import requests
import threading
import zipfile
import tempfile
import shutil

import cmf_boto
import cmf_logger
import mfcommon

KEY_SERVER_CONFIG_ID = 'server.configurationId'

USER_APP_ENDPOINT = '/user/app'
USER_SERVER_ENDPOINT = '/user/server'
SCHEMA_ENDPOINT = '/admin/schema/'
# Set maximum size of uncompressed file to 500MBs.
# This is just under the /tmp max size of 512MB in Lambda.
ZIP_MAX_SIZE = 500000000

class InputDataValidationException(Exception):
    pass

class DataImportException(Exception):
    pass

class DataExportException(Exception):
    pass

class InvalidOptionException(Exception):
    pass

def logging_filter(record):
    record.task_execution_id = logging_context.task_execution_id
    record.status = logging_context.status
    return True


logging_context = threading.local()
logger = cmf_logger.init_task_execution_logger(logging_filter)


def validate_event_body(body):
    try:
        json.loads(body)
    except ValueError:
        raise ValueError("Event body is invalid")


def delete_home_region(current_home_region):
    mh_config_client = cmf_boto.client('migrationhub-config', region_name=current_home_region)
    home_region_controls = mh_config_client.describe_home_region_controls()["HomeRegionControls"]
    if len(home_region_controls) == 0:
        logger.info("Home region not set. Skipping.")
        return
    control_id = home_region_controls[0]["ControlId"]  # It is currently not possible to have multiple home regions

    logger.info("Deleting home region with controlId " + control_id)
    mh_config_client.delete_home_region_control(ControlId=control_id)


def wait_for_home_region_deletion(mh_config_client):
    logger.info("Confirming home region is deleted")
    try:
        # There may be a cross-region replication delay to complete deletion.
        # The replication is expected to be completed on the order of milliseconds.
        poll(lambda: mh_config_client.get_home_region(),
             step=1,
             timeout=30,
             check_success=lambda result: not bool(result.get("HomeRegion")))
    except TimeoutException:
        msg = "ERROR: Unable to confirm original MGH Home Region was deleted"
        raise TimeoutException(msg)


def create_home_region(task_arguments):
    input_home_region = task_arguments['home_region']
    mh_config_client = cmf_boto.client('migrationhub-config', region_name=input_home_region)

    current_home_region = mh_config_client.get_home_region().get('HomeRegion')
    if current_home_region:
        if input_home_region == current_home_region:
            logger.info("Correct home region is already set")
            return
        else:
            logger.info("Deleting current home region " + current_home_region)
            delete_home_region(current_home_region)
            wait_for_home_region_deletion(mh_config_client)

    account_id = os.environ["AWS_ACCOUNT_ID"]
    target = {
        "Type": "ACCOUNT",
        "Id": account_id
    }

    logger.info("Setting home region as " + input_home_region)
    mh_config_client.create_home_region_control(HomeRegion=input_home_region, Target=target)

    logger.info("SUCCESS: MGH Home Region set to %s" % input_home_region)


def check_for_completed_export(describe_exports_result):
    for export in describe_exports_result['exportsInfo']:
        if export["exportStatus"] == "SUCCEEDED":
            return True
        elif export["exportStatus"] == "FAILED":
            raise DataExportException("ERROR: " + export["statusMessage"])
    return False


def wait_for_export_task_complete(ads_client, export_id):
    logger.info("Confirming export ID %s is completed" % export_id)
    try:
        poll(lambda: ads_client.describe_export_tasks(exportIds=[export_id]),
             step=1,
             timeout=180,
             check_success=check_for_completed_export)
    except TimeoutException:
        msg = "ERROR: Unable to confirm export ID %s was completed" % export_id
        raise TimeoutException(msg)


def get_export_download_url(ads_client, export_id):
    response = ads_client.describe_export_tasks(exportIds=[export_id])
    return response['exportsInfo'][0]['configurationsDownloadUrl']


def extract_ec2_rec_file(download_url):
    req = requests.get(download_url)
    export_uuid = str(uuid.uuid4())
    export_uuid_folder = f'{tempfile.gettempdir()}/{export_uuid}'

    zip_file_name = os.path.join(tempfile.gettempdir(), f'{export_uuid}.zip')
    with open(zip_file_name, 'wb') as output_file:
        output_file.write(req.content)
        logger.info(f'Downloaded exported zip file to: {zip_file_name}')

    with open(zip_file_name, "rb") as zip_file:
        exported_zip = zipfile.ZipFile(zip_file)
        total_uncompressed_size = sum(file.file_size for file in exported_zip.infolist())
    if total_uncompressed_size > ZIP_MAX_SIZE:
        cleanup_temp(export_uuid)
        msg = f'Zip file uncompressed contents exceeds maximum size of {ZIP_MAX_SIZE / 1e+6}MBs.'
        logger.error(msg)
        raise IOError(msg)

    logger.info('Looking for EC2InstanceRecommendations*.csv')
    with zipfile.ZipFile(zip_file_name, 'r') as exporter_zip:
        exporter_zip.extractall(export_uuid_folder)  # NOSONAR This size of the file is in control
    server_csv_file = glob.glob(os.path.join(export_uuid_folder, 'EC2InstanceRecommendations*.csv'))[0]
    logger.info(f'Found recommendations csv: {server_csv_file}')
    return server_csv_file, export_uuid


def import_ec2_recs(csv_file):
    factory_login_token = mfcommon.factory_login(False, get_factory_config())
    cmf_servers = get_cmf_items(factory_login_token, USER_SERVER_ENDPOINT)

    with open(csv_file, mode='r') as servers_file:
        exported_servers = csv.DictReader(servers_file)

        for row in exported_servers:
            if not row.get('Recommendation.EC2.Instance.Model', ''):
                continue
            cmf_server = get_cmf_server_by_name(cmf_servers, row['ServerId'])
            if cmf_server is None:
                continue

            payload = {
                'instanceType': row['Recommendation.EC2.Instance.Model'],
                'tenancy': row['UserPreference.EC2.Tenancy']
            }
            response = mfcommon.put_data_to_api(
                factory_login_token,
                os.environ["USER_API"],
                f'{USER_SERVER_ENDPOINT}/{cmf_server["server_id"]}',
                payload,
                get_factory_config()
            )

            validate_msg = validate_user_api_response(response)
            if validate_msg is not None:
                raise DataImportException(validate_msg)

    logger.info("SUCCESS: Completed EC2 Recommendations Import")


def get_excluded_instance_types(rec_preferences, instance_family_exclusions):
    instance_types = []
    for type in rec_preferences['InstanceTypes']:
        for family in type['InstanceFamilies']:
            if family['InstanceFamily'] in (family.upper() for family in instance_family_exclusions):
                instance_types.extend(family['InstanceTypeList'])
    return instance_types


def import_ec2_rec(task_arguments):
    home_region = task_arguments['home_region']
    ads_client = cmf_boto.client('discovery', region_name=home_region)
    logger.info("Importing EC2 Recommendations")

    with open('recommendation-preferences.json') as rec_preferences_file:
        rec_preferences = json.load(rec_preferences_file)
    excluded_instance_types = get_excluded_instance_types(rec_preferences,
                                                          task_arguments.get('ec2_instance_family_exclusions', [])),

    sizing_type = rec_preferences['SizingPreferenceOptions'][task_arguments['sizing_preference']]
    cpu_performance = {
        "name": f'p{task_arguments["percent_of_cpu_specification"]}' if sizing_type == "PERCENTILE" else sizing_type
    }
    if sizing_type == 'SPEC' and task_arguments['current_server_specification_match_preference'] == 'Custom Match':
        cpu_performance['percentageAdjust'] = task_arguments['percent_of_cpu_specification']

    ram_performance = {
        "name": f'p{task_arguments["percent_of_ram_specification"]}' if sizing_type == "PERCENTILE" else sizing_type
    }
    if sizing_type == 'SPEC' and task_arguments['current_server_specification_match_preference'] == 'Custom Match':
        ram_performance['percentageAdjust'] = task_arguments['percent_of_ram_specification']

    preferences = {
        "ec2RecommendationsPreferences": {
            "enabled": True,
            "preferredRegion": task_arguments['aws_region'],
            "tenancy": "SHARED",
            "cpuPerformanceMetricBasis": cpu_performance,
            "ramPerformanceMetricBasis": ram_performance
        }
    }
    if excluded_instance_types:
        preferences['excludedInstanceTypes']: excluded_instance_types

    response = ads_client.start_export_task(preferences=preferences)
    logger.info("Started export with ID " + response["exportId"])

    wait_for_export_task_complete(ads_client, response["exportId"])

    download_url = get_export_download_url(ads_client, response["exportId"])
    csv_file, export_uuid = extract_ec2_rec_file(download_url)
    import_ec2_recs(csv_file)
    cleanup_temp(export_uuid)


def get_factory_config():
    return {
        "LoginApi": os.environ["LOGIN_API"],
        "UserApi": os.environ["USER_API"],
        "Region": os.environ["region"],
        "UserPoolId": os.environ["USER_POOL_ID"],
        "UserPoolClientId": os.environ["USER_POOL_CLIENT_ID"]
    }


def get_schema(factory_login_token, schema_type):
    path = SCHEMA_ENDPOINT + schema_type
    response = mfcommon.get_data_from_api(
        factory_login_token,
        os.environ["ADMIN_API"],
        path,
        get_factory_config()
    )
    return json.loads(response.text)


def convert_ads_to_cmf_server_attribute(attribute, cmf_apps, ads_server, r_type):

    match attribute['name']:
        case 'app_id':
            # An ADS server can be a part of multiple applications. A CMF server can be associated with a single application
            # If there are multiple applications, the correct association is indeterminant. Throwing 4xx error so customer is aware of the discrepancy.
            apps = json.loads(ads_server.get('server.applications', '[]'))
            if len(apps) == 1:
                app_name = apps[0]['name']
                matched_app = get_cmf_app_by_name(cmf_apps, app_name)
                if matched_app is None:
                    raise InputDataValidationException('ERROR: Application with name %s not found' % app_name)
                return matched_app['app_id']
            elif len(apps) > 1:
                msg = f'ERROR: Multiple applications found for ADS server ID {ads_server["server.configurationId"]}'
                logger.error(msg)
                raise InputDataValidationException(msg)
        case 'server_name':
            return ads_server[KEY_SERVER_CONFIG_ID]
        case 'server_os_family':
            for os_family in attribute['listvalue'].split(","):
                if os_family in ads_server.get('server.osName', '').lower():
                    return os_family
        case 'server_os_version':
            return ads_server.get('server.osVersion')
        case 'server_fqdn':
            return ads_server.get('server.hostName')
        case 'r_type':
            return r_type

    return None


def convert_ads_server_to_cmf(schema, ads_client, cmf_apps, ads_server, r_type, processing_errors):
    ads_server_details = ads_client.describe_configurations(configurationIds=[ads_server[KEY_SERVER_CONFIG_ID]])
    cmf_server = {}

    for attribute in schema['attributes']:
        attr_value = convert_ads_to_cmf_server_attribute(attribute, cmf_apps, ads_server_details['configurations'][0],
                                                         r_type)
        if attribute.get('hidden', False):
            continue
        if attr_value is not None:
            cmf_server[attribute['name']] = attr_value
            continue
        if attribute.get('required', False):
            logger.debug("ADS server %s does not have all required attribute \"%s\", not importing" % (
                ads_server[KEY_SERVER_CONFIG_ID], attribute['name']))
            processing_errors[ads_server[KEY_SERVER_CONFIG_ID]] = {'missing required attributes': [attribute['name']]}
            return None

    return cmf_server


def validate_user_api_response(response):
    if response.status_code != 200:
        msg = 'Bad response from API: %s' % response.text
        logger.warning(msg)
        return msg

    response_json = json.loads(response.text)
    if 'errors' in response_json:
        msg = 'ERROR: The following errors occurred when attempting to create user objects: %s' % json.dumps(
            response_json['errors'])
        logger.warn(msg)
        return msg
    return None


# Validating user has not created new required application attributes.
# These attributes would not be populated by default, which would cause import failures.
def validate_app_schema(factory_login_token):
    supported_attributes = ['app_name', 'aws_accountid', 'aws_region']
    schema = get_schema(factory_login_token, "app")
    for attribute in schema['attributes']:
        if attribute.get('required', False) and attribute['name'] not in supported_attributes and not attribute.get(
                'hidden', False):
            msg = 'ERROR: Can not populate required application attributed: %s' % attribute['name']
            logger.warning(msg)
            return msg
    return None


def get_cmf_items(factory_login_token, endpoint):
    apps_api_response = mfcommon.get_data_from_api(
        factory_login_token,
        os.environ['USER_API'],
        endpoint,
        get_factory_config()
    )
    return json.loads(apps_api_response.text)


def get_cmf_app_by_name(cmf_apps, app_name):
    return next((cmf_app for cmf_app in cmf_apps if str(cmf_app['app_name']).lower() == str(app_name).lower()), None)


def get_cmf_server_by_name(cmf_servers, server_name):
    return next((cmf_server for cmf_server in cmf_servers if str(cmf_server['server_name']).lower() == str(server_name).lower()), None)


def import_ads_app_data(factory_login_token, ads_client, task_arguments):
    logger.info("Importing ADS application data")
    validation_result = validate_app_schema(factory_login_token)
    if validation_result is not None:
        return validation_result

    cmf_apps = get_cmf_items(factory_login_token, USER_APP_ENDPOINT)
    apps_to_create = []
    validation_results = []

    paginator = ads_client.get_paginator('list_configurations')
    page_iterator = paginator.paginate(configurationType='APPLICATION', PaginationConfig={'PageSize': 25})
    logger.info("Paginating through ADS applications")

    for page in page_iterator:
        for app in page['configurations']:
            payload = {
                'app_name': app['application.name'],
                'aws_accountid': task_arguments['aws_accountid'],
                'aws_region': task_arguments['aws_region']
            }

            # Acquiring existing CMF app ID
            matched_app = get_cmf_app_by_name(cmf_apps, app['application.name'])

            if matched_app is not None:
                logger.info("Updating application with ID %s" % matched_app['app_id'])
                response = mfcommon.put_data_to_api(
                    factory_login_token,
                    os.environ["USER_API"],
                    f'{USER_APP_ENDPOINT}/{matched_app["app_id"]}',
                    payload,
                    get_factory_config()
                )
                validation_results.append(validate_user_api_response(response))
            else:
                apps_to_create.append(payload)

        logger.info("Creating %d new applications" % len(apps_to_create))
        response = mfcommon.post_data_to_api(
            factory_login_token,
            os.environ["USER_API"],
            USER_APP_ENDPOINT,
            apps_to_create,
            get_factory_config()
        )
        validation_results.append(validate_user_api_response(response))

        validate = next((result for result in validation_results if result is not None), None)
        if validate is not None:
            return validate


def update_existing_servers_extract_new(factory_login_token, ads_client, server, r_type, validation_results, servers_to_create, schema, cmf_apps, cmf_servers, processing_errors):
    try:
        payload = convert_ads_server_to_cmf(schema, ads_client, cmf_apps, server, r_type, processing_errors)
    except Exception as e:
        if 'ERROR: Multiple applications' in str(e):
            logger.error(e)
            raise InputDataValidationException(
                'Server belongs to multiple applications. User must take action to correct.')
        raise e

    if payload is not None:
        # Acquiring existing CMF server ID
        matched_server = get_cmf_server_by_name(cmf_servers, server[KEY_SERVER_CONFIG_ID])

        if matched_server is not None:
            logger.info("Updating server with name %s" % matched_server['server_name'])
            response = mfcommon.put_data_to_api(
                factory_login_token,
                os.environ["USER_API"],
                f'{USER_SERVER_ENDPOINT}/{matched_server["server_id"]}',
                payload,
                get_factory_config()
            )
            validation_results.append(validate_user_api_response(response))
        else:
            servers_to_create.append(payload)


def import_ads_server_data(factory_login_token, ads_client, r_type):
    logger.info("Importing ADS server data")
    processing_errors = {}

    schema = get_schema(factory_login_token, "server")

    logger.info("Getting existing CMF inventory items")
    cmf_apps = get_cmf_items(factory_login_token, USER_APP_ENDPOINT)
    cmf_servers = get_cmf_items(factory_login_token, USER_SERVER_ENDPOINT)

    paginator = ads_client.get_paginator('list_configurations')
    page_iterator = paginator.paginate(configurationType='SERVER', PaginationConfig={'PageSize': 25})
    for page in page_iterator:
        validation_results = []
        servers_to_create = []

        for server in page['configurations']:
            update_existing_servers_extract_new(
                factory_login_token, ads_client, server, r_type, validation_results, servers_to_create, schema, cmf_apps, cmf_servers, processing_errors
            )

        logger.info("Creating %d new servers" % len(servers_to_create))
        response = mfcommon.post_data_to_api(
            factory_login_token,
            os.environ["USER_API"],
            USER_SERVER_ENDPOINT,
            servers_to_create,
            get_factory_config()
        )
        validation_results.append(validate_user_api_response(response))

        validate = next((result for result in validation_results if result is not None), None)
        if validate is not None:
            return validate

    if len(processing_errors) > 0:
        logger.warn(f'Some ADS servers could not be imported: {processing_errors}')


def import_ads_discovery_data(task_arguments):
    factory_login_token = mfcommon.factory_login(False, get_factory_config())
    home_region = task_arguments['home_region']
    ads_client = cmf_boto.client('discovery', region_name=home_region)
    r_type = task_arguments['r_type']

    import_result = import_ads_app_data(factory_login_token, ads_client, task_arguments)
    if import_result is not None:
        raise DataImportException(import_result)

    import_result = import_ads_server_data(factory_login_token, ads_client, r_type)
    if import_result is not None:
        raise DataImportException(import_result)

    logger.info("SUCCESS: Completed import of ADS discovery data")


def manage_mgh_actions(body):
    action = body['action']
    logger.info(f"Received event with action: {action}")

    if action == 'Create Home Region':
        create_home_region(body)
    elif action == 'Import EC2 Recommendations':
        import_ec2_rec(body)
    elif action == 'Import ADS Discovery Data':
        import_ads_discovery_data(body)
    else:
        raise InvalidOptionException("Invalid action")


def cleanup_temp(export_uuid):
    # Delete temp package files in /tmp/ to ensure that large files are not left hanging around for
    # longer than required.
    if os.path.exists(tempfile.gettempdir() + "/" + export_uuid):
        shutil.rmtree(tempfile.gettempdir() + "/" + export_uuid, ignore_errors=True)


def lambda_handler(event, _):
    cmf_logger.log_event_received(event)
    logging_context.status = "In Progress"
    logging_context.task_execution_id = ""

    try:
        validate_event_body(event['body'])
        # Assuming task arguments are already validated by the pipeline logic
        body = json.loads(event['body'])
        logging_context.task_execution_id = body['task_execution_id']

        manage_mgh_actions(body)
        logging_context.status = "Complete"
        logger.info("Processing successfully completed")
    except Exception as e:
        logging_context.status = "Failed"
        logger.error("Processing failed with the following error message: %s", str(e))
        raise e
