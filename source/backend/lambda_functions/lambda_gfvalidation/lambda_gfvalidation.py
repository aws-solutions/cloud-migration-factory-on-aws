#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from __future__ import print_function
import os
import json
from policy import MFAuth

import cmf_boto
from cmf_utils import cors, default_http_headers
from cmf_logger import logger, log_event_received

application = os.environ['application']
environment = os.environ['environment']
servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)
waves_table_name = '{}-{}-waves'.format(application, environment)
servers_table = cmf_boto.resource('dynamodb').Table(servers_table_name)
apps_table = cmf_boto.resource('dynamodb').Table(apps_table_name)
waves_table = cmf_boto.resource('dynamodb').Table(waves_table_name)


def extract_validation_list_error(validation_list):
    if validation_list is not None:
        for validation in validation_list:
            if validation is not None and "ERROR" in validation:
                return validation


def lambda_handler(event, _):
    log_event_received(event)

    # Verify user has access to run ec2 replatform functions.
    auth = MFAuth()
    auth_response = auth.get_user_resource_creation_policy(event, 'EC2')
    if auth_response['action'] != 'allow':
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': json.dumps(auth_response)}

    try:
        body = json.loads(event['body'])
        if 'waveid' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'waveid is required'}

        body = json.loads(event['body'])
        if 'accountid' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'Target AWS Account Id is required'}

    except Exception as e:
        print(e)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    try:
        validation_list = get_server_list(body['waveid'])
        validation_error = extract_validation_list_error(validation_list)
        if validation_error is not None:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': validation_error}

        msg = 'EC2 Input Validation Completed'
        print(msg)
        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': msg}
    except Exception as e:

        print('Lambda Handler Main Function Failed' + str(e))
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'Lambda Handler Main Function Failed with error : ' + str(e)}


def init_server_params(server):
    if "add_vols_name" not in server:
        server['add_vols_name'] = ''
    if "add_vols_type" not in server:
        server['add_vols_type'] = ''
    if "ebs_optimized" not in server:
        server['ebs_optimized'] = ''
    if "detailed_monitoring" not in server:
        server['detailed_monitoring'] = ''
    if "root_vol_name" not in server:
        server['root_vol_name'] = ''
    if "root_vol_type" not in server:
        server['root_vol_type'] = ''
    if "ebs_kms_key_id" not in server:
        server['ebs_kms_key_id'] = ''
    if "add_vols_size" not in server:
        server['add_vols_size'] = ''
    if "iamRole" not in server:
        server['iamRole'] = ''


def process_server(server, app_list, server_list, app_numb, validation_list):
    if "app_id" in server:
        addvolcount = 0
        if app_list[app_numb] == server['app_id'] and server['r_type'].upper() == 'REPLATFORM':
            server_list.append(server)
            init_server_params(server)

            print('Input Values Going to be Passed for Validation:')
            print(server)

            # Call the Validation Script to Validate All Input Required Atrributes
            if server['r_type'].upper() == 'REPLATFORM':
                validation = validate_input(addvolcount, server)
                if validation is None:
                    serverresponse = servers_table.get_item(Key={'server_id': server['server_id']})
                    serveritem = serverresponse['Item']
                    serveritem['migration_status'] = 'Validation Completed'
                    servers_table.put_item(Item=serveritem)
                else:
                    validation_list.append(validation)


def populate_app_lists(apps, app_list, app_name_list, wave_id):
    for app in apps:
        if 'wave_id' in app and str(app['wave_id']) == wave_id:
            app_list.append(app['app_id'])
            app_name_list.append(app['app_name'])


def get_server_list(wave_id):
    try:
        # Get all Apps and servers from migration factory
        validation_list = []
        getserver = scan_dynamodb_table('server')

        if getserver is not None and "ERROR" in getserver:
            validation_list.append("ERROR: Unable to Retrieve Data from Dynamo DB Server table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB Server table')

        servers = sorted(getserver, key=lambda i: i['server_name'])

        getapp = scan_dynamodb_table('app')
        if getapp is not None and "ERROR" in getapp:
            validation_list.append("ERROR: Unable to Retrieve Data from Dynamo DB App table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB App table')
        apps = sorted(getapp, key=lambda i: i['app_name'])
        # Get App list
        app_list = []
        app_name_list = []
        validation_value = ''

        # Pull App Id and App Name from Apps Dynamo table
        populate_app_lists(apps, app_list, app_name_list, wave_id)

        serverlist = []
        apptotal = int(len(app_list))
        appnumb = 0

        # Read App by app and pull the server list

        while appnumb < apptotal:
            # Pull Server List and Attributes
            for server in servers:
                process_server(server, app_list, serverlist, appnumb, validation_list)
            appnumb = appnumb + 1

            # Validate the Input List of Servers

        if len(serverlist) == 0:
            validation_list.append("ERROR: Server list for wave " + wave_id + " in Migration Factory is empty....")

        # Check Any Validation Steps are failed

        for validation in validation_list:
            if validation is not None:
                validation_value = 'Yes'

                # Return Validation Message if any Validation Step failed

        if validation_value == 'Yes':
            return validation_list

    except Exception as e:
        validation_list.append("ERROR: Getting server list failed...." + str(e))
        print("ERROR: Getting server list failed...." + str(e))
        return validation_list


def validate_lengths(root_vol_size, subnet_id, securitygroup_ids, instance_type, ami_id, availabilityzone, server_name):
    if len(root_vol_size) == 0:
        msg = 'ERROR:The Root Volume Size field is empty for Server: ' + server_name
        print(msg)
        return msg

    if len(subnet_id) == 0:
        msg = 'ERROR:The Subnet_IDs field is empty for Server: ' + server_name
        print(msg)
        return msg

    if len(securitygroup_ids) == 0:
        msg = 'ERROR:The security group id is empty for Server: ' + server_name
        print(msg)
        return msg

    if len(instance_type) == 0:
        msg = 'ERROR:The instance type is empty for Server: ' + server_name
        print(msg)
        return msg

    if len(ami_id) == 0:
        msg = 'ERROR:The AMI Id Value is missing for Server: ' + server_name
        print(msg)
        return msg

    if len(availabilityzone) == 0:
        msg = 'ERROR:The availability zone is missing for Server: ' + server_name
        print(msg)
        return msg


def validate_volume_type(volume_type, server_name):
    listofvolumetypes = ["standard", "io1", "io2", "gp2", "gp3", ""]
    if (volume_type not in listofvolumetypes):
        msg = 'ERROR:The Root Volume Type Is Incorrect for Server: ' + server_name + ' Allowed List of Volume Types "standard", "io1", "io2", "gp2", "gp3"'
        print(msg)
        return msg


def validate_volume_types(add_vols_type, server_name):
    listofvolumetypes = ["standard", "io1", "io2", "gp2", "gp3", ""]
    for volume_type in add_vols_type:
        if volume_type != '' and str(volume_type) not in listofvolumetypes:
            msg = 'ERROR:Additional Volume Type Is Incorrect for Server:' + server_name + ' Allowed List of Volume Types "standard", "io1", "io2", "gp2", "gp3" '
            print(msg)
            return msg


def validate_volume_names(add_vols_name, server_name):
    listofvolumenames = ["/dev/sdf", "/dev/sdg", "/dev/sdh", "/dev/sdi", "/dev/sdj", "/dev/sdk", "/dev/sdl",
                         "/dev/sdm", "/dev/sdn", "/dev/sdo", "/dev/sdp", "xvdf", "xvdg", "xvdh", "xvdi", "xvdj",
                         "xvdk", "xvdl", "xvdm", "xvdn", "xvdo", "xvdp", ""]
    for volume_name in add_vols_name:
        if volume_name != '' and str(volume_name) not in listofvolumenames:
            msg = 'ERROR:Additional Volume Name Is Incorrect for Server:' + server_name + ' Allowed Values for Linux "/dev/sdf","/dev/sdg","/dev/sdh","/dev/sdi","/dev/sdj","/dev/sdk","/dev/sdl","/dev/sdm","/dev/sdn","/dev/sdo","/dev/sdp", and for Window OS use "xvdf","xvdg","xvdh","xvdi","xvdj","xvdk","xvdl","xvdm","xvdn","xvdo","xvdp",""'
            print(msg)
            return msg


def validate_volume_sizes(add_vols_size, server_name):
    for volume_size in add_vols_size:
        if int(volume_size) < 1 or int(volume_size) > 16384:
            msg = 'ERROR:Additional Volume Size Is Incorrect for Server:' + server_name + ' Volume Size needs to between 1 GiB and 16384 GiB'
            print(msg)
            return msg


def validate_add_vols_name_size_type(add_vols_name, add_vols_size, add_vols_type, server_name):
    if add_vols_name != '' and len(add_vols_size) != len(add_vols_name):
        msg = 'ERROR:Additional Volume Names are missing for some additional Volume, Please provide value for all additional volumes or Leave as Blank to Use Default ' + server_name
        print(msg)
        return msg

    if add_vols_type != '' and len(add_vols_size) != len(add_vols_type):
        msg = 'ERROR:Additional Volume Types are missing for some additional Volume, Please provide value for all additional volumes or Leave as Blank to Use Default ' + server_name
        print(msg)
        return msg


# Input Data Validation
def validate_input(addvolcount, server):
    try:

        print("************************************")
        print("Input Data Validation Starting....")
        print("************************************")

        server_name = server['server_name'].lower()
        instance_type = server['instanceType'].lower()
        securitygroup_ids = server['securitygroup_IDs']
        subnet_id = server['subnet_IDs']
        tenancy = server['tenancy']
        add_vols_size = server['add_vols_size']
        add_vols_name = server['add_vols_name']
        add_vols_type = server['add_vols_type']
        root_vol_size = server['root_vol_size']
        root_vol_name = server['root_vol_name']
        root_vol_type = server['root_vol_type']
        availabilityzone = server['availabilityzone']
        ami_id = server['ami_id']
        ebs_optimized = server['ebs_optimized']
        detailed_monitoring = server['detailed_monitoring']

        msg = validate_add_vols_name_size_type(add_vols_name, add_vols_size, add_vols_type, server_name)
        if msg is not None:
            return msg

        if len(add_vols_size) > 0:
            addvolcount = len(add_vols_size)

        print("addvolcount:" + str(addvolcount))

        msg = validate_volume_sizes(add_vols_size, server_name)
        if msg is not None:
            return msg

        msg = validate_volume_types(add_vols_type, server_name)
        if msg is not None:
            return msg

        msg = validate_volume_names(add_vols_name, server_name)
        if msg is not None:
            return msg

        msg = validate_lengths(root_vol_size, subnet_id, securitygroup_ids, instance_type, ami_id, availabilityzone,
                               server_name)
        if msg is not None:
            return msg

        tenancylist = ['Shared', 'Dedicated', 'Dedicated host']
        if tenancy not in tenancylist:
            msg = 'ERROR:The tenancy value is Invalid for Server: ' + server_name + ' Allowed Values "Shared","Dedicated","Dedicated host" '
            print(msg)
            return msg

        if int(root_vol_size) < 8 or int(root_vol_size) > 16384:
            msg = 'ERROR:The Root Volume Size Is Incorrect for Server: ' + server_name + ' Volume Size needs to between 8 GiB and 16384 GiB '
            print(msg)
            return msg

        msg = validate_volume_type(root_vol_type, server_name)
        if msg is not None:
            return msg

        listofrootvolumenames = ["/dev/sda1", "/dev/xvda", ""]
        if root_vol_name not in listofrootvolumenames:
            msg = 'ERROR:The Root Volume Name Is Incorrect for Server: ' + server_name + ' Allowed List of Volume Names "/dev/sda1", "/dev/xvda" '
            print(msg)
            return msg

        allowedvalues = ["", True, False]
        if ebs_optimized not in allowedvalues:
            msg = 'ERROR:The ebs_optimized value is incorrect for Server : ' + server_name + ' Allowed Values [true,false,""]'
            print(msg)
            return msg

        if detailed_monitoring not in allowedvalues:
            msg = 'ERROR:The detailed_monitoring value is incorrect for Server: ' + server_name + ' Allowed Values [true,false,""]'
            print(msg)
            return msg

    except Exception as e:
        print("ERROR: EC2 Input Validation Failed.Failed With error: " + str(e))
        return "ERROR: EC2 Input Validation Failed.Failed With error: " + str(e)


def scan_dynamodb_table(datatype):
    try:
        if datatype == 'server':
            response = servers_table.scan(ConsistentRead=True)
        elif datatype == 'app':
            response = apps_table.scan(ConsistentRead=True)
        elif datatype == 'wave':
            response = waves_table.scan(ConsistentRead=True)
        scan_data = response['Items']
        while 'LastEvaluatedKey' in response:
            print("Last Evaluate key is   " + str(response['LastEvaluatedKey']))
            if datatype == 'server':
                response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
            elif datatype == 'app':
                response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
            elif datatype == 'wave':
                response = waves_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
            scan_data.extend(response['Items'])
        return (scan_data)

    except Exception as e:
        print("ERROR: Unable to retrieve the data from Dynamo DB table: " + str(e))
        return "ERROR: Unable to retrieve the data from Dynamo DB table: " + str(e)
