#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from __future__ import print_function
import json
import os
import troposphere.ec2 as ec2
from troposphere import GetAtt, Output, Parameter, Ref, Template
from policy import MFAuth
import traceback
import re
import tempfile

import cmf_boto
from cmf_utils import cors, default_http_headers

headers = {'Content-Type': 'application/json'}

application = os.environ['application']
environment = os.environ['environment']
servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)
waves_table_name = '{}-{}-waves'.format(application, environment)
servers_table = cmf_boto.resource('dynamodb').Table(servers_table_name)
apps_table = cmf_boto.resource('dynamodb').Table(apps_table_name)
waves_table = cmf_boto.resource('dynamodb').Table(waves_table_name)
template_generated_prefix = '/CFN_Template_'
template_generated_suffix = '.yaml'


def extract_template_gen_error(templates_generated):
    if templates_generated is not None:
        for template_generated in templates_generated:
            if template_generated is not None and "ERROR" in template_generated:
                return template_generated


def get_wave_name(waves, body):
    wave_name = ''
    for wave in waves:
        if str(wave['wave_id']) == body['waveid']:
            wave_name += extract_alnum(wave['wave_name'])
    return wave_name


def extract_alnum(input_str):
    alnum_str = ''
    for character in input_str:
        if character.isalnum():
            alnum_str += character
    return alnum_str


def extract_numeric(input_str):
    num_str = ''
    for character in input_str:
        if character.isnumeric():
            num_str += character
    return num_str


def process_app(app, body, context, wave_name, generated_template_uris):
    if 'wave_id' in app and str(app['wave_id']) == body['waveid']:
        app_name = extract_alnum(app['app_name'])
        print('App Name :' + app_name)

        app_id = extract_alnum(app['app_id'])
        print('App Id :' + app_id)

        account_id = extract_numeric(app['aws_accountid'])

        # AWS Account Id to Create S3 Path
        aws_account_id = context.invoked_function_arn.split(":")[4]

        gfbuild_bucket = "{}-{}-{}-gfbuild-cftemplates".format(
            application, environment, aws_account_id)
        print('S3 Bucket to Load Cloud formation Templates :' + gfbuild_bucket)

        # lambda path and Json File
        lambda_path = tempfile.gettempdir() + template_generated_prefix + app_id + '_' + app_name + template_generated_suffix

        # S3 path and Json File
        s3_path = account_id + '/' + wave_name + template_generated_prefix + app_id + '_' + app_name + template_generated_suffix
        print('S3 Path Along with JSON File: ' + s3_path)

        # Upload Template into S3 Bucket
        s3 = cmf_boto.resource('s3')
        s3.meta.client.upload_file(lambda_path, gfbuild_bucket.replace(" ", ""), s3_path)
        generated_template_uris.append('s3://' + gfbuild_bucket.replace(" ", "") + '/' + s3_path)


def lambda_handler(event, context):
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

        if 'accountid' not in body:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'Target AWS Account Id is required'}

    except Exception as e:
        print(e)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}
    # Call Server List Function
    try:
        templates_generated = get_server_list(body['waveid'])
        print(" Main templates_generated:")
        print(templates_generated)
        template_gen_error = extract_template_gen_error(templates_generated)
        if template_gen_error is not None:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': template_gen_error}

        # Read Apps Dynamo DB Table
        getapp = scan_dynamodb_table('app')
        msgapp = 'Unable to Retrieve Data from Dynamo DB App Table'
        if getapp is not None and "ERROR" in getapp:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msgapp}

        apps = sorted(getapp, key=lambda i: i['app_name'])

        # Read Waves Dynamo DB Table
        getwave = scan_dynamodb_table('wave')
        msgwave = 'Unable to Retrieve Data from Dynamo DB Wave Table'
        if getwave is not None and "ERROR" in getwave:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msgwave}

        waves = sorted(getwave, key=lambda i: i['wave_name'])

        wave_name = get_wave_name(waves, body)

        # App Table Attributes for S3 Path Generation
        generated_template_uris = []

        for app in apps:
            process_app(app, body, context, wave_name, generated_template_uris)

        msg = 'EC2 Cloud Formation Template Generation Completed. ' + str(
            len(generated_template_uris)) + ' template S3 URIs created: [' + ','.join(
            generated_template_uris) + '].'
        print(msg)
        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': msg}

    except Exception as e:
        traceback.print_exc()
        print('Lambda Handler Main Function Failed' + str(e))
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'Lambda Handler Main Function Failed with error : ' + str(e)}


def process_server(server, applist, appnamelist, appnumb, template, templates_generated):
    addvolcount = 0
    # Call Generate Cloud Formation Template Function for each Server
    if "add_vols_size" not in server:
        server['add_vols_size'] = ''
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
    if "ebs_kmskey_id" not in server:
        server['ebs_kmskey_id'] = ''
    if "iamRole" not in server:
        server['iamRole'] = ''

    print('Input Values Going to be Passed for CFT Generation:')
    print(server)
    tags = []
    if 'tags' in server:
        tags = server['tags']
    server_name_short = server['server_name'].lower().split(".")[0]
    templategen = generate_cft(applist[appnumb], appnamelist[appnumb], template, addvolcount,
                               server_name_short, server, tags)
    templates_generated.append(templategen)

    # update
    serverresponse = servers_table.get_item(Key={'server_id': server['server_id']})
    serveritem = serverresponse['Item']
    serveritem['migration_status'] = 'CF Template Generated'
    servers_table.put_item(Item=serveritem)


def get_servers_for_app(servers, applist, appnumb):
    server_list = []
    # Gather servers for this application that are Replatform.
    for server in servers:
        if "app_id" in server and "r_type" in server:
            if applist[appnumb] == server['app_id'] and server['r_type'].upper() == 'REPLATFORM':
                server_list.append(server)

    return server_list


def populate_app_lists(apps, applist, appnamelist, waveid):
    for app in apps:
        if 'wave_id' in app and str(app['wave_id']) == waveid:
            applist.append(app['app_id'])
            appnamelist.append(app['app_name'])


def get_server_list(waveid):
    try:

        templates_generated = []
        # Get all Apps and servers from migration factory

        getserver = scan_dynamodb_table('server')

        if getserver is not None and "ERROR" in getserver:
            templates_generated.append("ERROR: Unable to Retrieve Data from Dynamo DB Server table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB Server table')

        servers = sorted(getserver, key=lambda i: i['server_name'])

        getapp = scan_dynamodb_table('app')
        if getapp is not None and "ERROR" in getapp:
            templates_generated.append("ERROR: Unable to Retrieve Data from Dynamo DB App table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB App table')

        apps = sorted(getapp, key=lambda i: i['app_name'])

        # Get App list
        applist = []
        appnamelist = []

        templategenerror = 'No'

        # Pull App Id and App Name from Apps Dynamo table
        populate_app_lists(apps, applist, appnamelist, waveid)

        apptotal = int(len(applist))
        appnumb = 0
        serverlist_all = []

        # Read App by app and pull the server list

        while appnumb < apptotal:

            # Open Cloud Formation template at Application level

            template = Template()
            template.set_version("2010-09-09")
            template.set_description("Builds stack for EC2 Servers for the Application " + str(appnamelist[appnumb]))

            serverlist = get_servers_for_app(servers, applist, appnumb)
            serverlist_all.extend(serverlist)

            # Process all servers that required Replatform.
            for server in serverlist:
                process_server(server, applist, appnamelist, appnumb, template, templates_generated)

            appnumb = appnumb + 1

        if len(serverlist_all) == 0:
            templates_generated.append("ERROR: Server list for wave " + waveid + " in Migration Factory is empty....")

        print("templates_generated:")
        print(templates_generated)

        for templategenval in templates_generated:
            if templategenval is not None:
                templategenerror = 'Yes'

        if templategenerror == 'Yes':
            return templates_generated

    except Exception as e:
        templates_generated.append("ERROR: Getting server list failed. Failed with Error:" + str(e))
        print("ERROR: Getting server list failed. Failed with Error: " + str(e))
        return templates_generated


def add_volumes(addvolcount, ebs_kmskey_id, template, server_name_alpha, param_az, param_ebskmskey, tags, ec2_instance):
    volume_id = 1
    while volume_id <= addvolcount:
        volume_id_str = str(volume_id)
        if len(str(ebs_kmskey_id)) == 0:
            volume = template.add_resource(
                ec2.Volume(
                    server_name_alpha + "Volume" + volume_id_str,
                    Encrypted='true',
                    AvailabilityZone=Ref(param_az),
                    Size=Ref(server_name_alpha + 'volume' + volume_id_str + 'size'),
                    VolumeType=Ref(server_name_alpha + 'volume' + volume_id_str + 'type')))
            volume.Tags = tags
        else:
            volume = template.add_resource(
                ec2.Volume(
                    server_name_alpha + "Volume" + volume_id_str,
                    Encrypted='true',
                    AvailabilityZone=Ref(param_az),
                    KmsKeyId=Ref(param_ebskmskey),
                    Size=Ref(server_name_alpha + 'volume' + volume_id_str + 'size'),
                    VolumeType=Ref(server_name_alpha + 'volume' + volume_id_str + 'type')))
            volume.Tags = tags

        template.add_resource(
            ec2.VolumeAttachment(
                server_name_alpha + "Volume" + volume_id_str + "Attachment",
                VolumeId=Ref(server_name_alpha + 'Volume' + volume_id_str),
                Device=Ref(server_name_alpha + 'volume' + volume_id_str + 'name'),
                InstanceId=Ref(ec2_instance)
            ))
        volume_id = volume_id + 1


def add_volume_params(addvolcount, add_vols_name, server_os_family, add_vols_type, template, server_name_alpha,
                      add_vols_size):
    # Adding Additional Volume Parameters into template
    linuxlistofvolumenames = ["/dev/sdf", "/dev/sdg", "/dev/sdh", "/dev/sdi", "/dev/sdj", "/dev/sdk", "/dev/sdl",
                              "/dev/sdm", "/dev/sdn", "/dev/sdo", "/dev/sdp", "/dev/sdq", "/dev/sdr", "/dev/sds",
                              "/dev/sdt", "/dev/sdu", "/dev/sdv", "/dev/sdw", "/dev/sdx", "/dev/sdy", "/dev/sdz"]
    windowslistofvolumenames = ["xvdf", "xvdg", "xvdh", "xvdi", "xvdj", "xvdk", "xvdl", "xvdm", "xvdn", "xvdo",
                                "xvdp", "xvdq", "xvdr", "xvds", "xvdt", "xvdu", "xvdv", "xvdw", "xvdy", "xvdz"]

    volume_param_id = 1
    while volume_param_id <= addvolcount:
        if add_vols_name == '' and server_os_family.lower() == 'windows':
            derived_volume_name = windowslistofvolumenames[volume_param_id - 1]
        elif add_vols_name == '' and server_os_family.lower() == 'linux':
            derived_volume_name = linuxlistofvolumenames[volume_param_id - 1]
        else:
            derived_volume_name = add_vols_name[volume_param_id - 1]

        if add_vols_type == '':
            derived_volume_type = 'gp3'
        else:
            derived_volume_type = add_vols_type[volume_param_id - 1]

        template.add_parameter(
            Parameter(
                server_name_alpha + "volume" + str(volume_param_id) + "name",
                Description="The device name for additional Volumes ( example, /dev/sdf through /dev/sdp for Linux or xvdf through xvdp for Windows).",
                Type="String",
                Default=derived_volume_name
            )
        )
        template.add_parameter(
            Parameter(
                server_name_alpha + "volume" + str(volume_param_id) + "type",
                Description="The volume type for additional volume. Choose io1, io2, gp2 or gp3 for SSD-backed volumes optimized for transactional workloads. Choose standard for HDD-backed volumes suitable for workloads where data is infrequently accessed.",
                Type="String",
                AllowedValues=["standard", "io1", "io2", "gp2", "gp3"],
                Default=derived_volume_type
            )
        )

        template.add_parameter(
            Parameter(
                server_name_alpha + "volume" + str(volume_param_id) + "size",
                Description="The size of the additional volume in GiB.",
                Type="Number",
                MinValue=1,
                MaxValue=16384,
                Default=add_vols_size[volume_param_id - 1]
            )
        )
        volume_param_id = volume_param_id + 1


def get_updated_tags(tags, server_name):
    updated_tags = []
    for element in tags:
        updated_tag = {'Key': element['key'], 'Value': element['value']}
        updated_tags.append(updated_tag)

    server_tag = {'Key': 'Name', 'Value': server_name}
    updated_tags.append(server_tag)

    return updated_tags


# Cloud Formation Template Generation
def generate_cft(app_id, app_name, template, addvolcount, server_name, server, tags):
    try:
        print("************************************")
        print("Cloud Formation Template Generation ....")
        print("************************************")

        instance_type = server['instanceType'].lower()
        securitygroup_ids = server['securitygroup_IDs']
        subnet_id = server['subnet_IDs']
        add_vols_size = server['add_vols_size']
        add_vols_name = server['add_vols_name']
        add_vols_type = server['add_vols_type']
        root_vol_size = server['root_vol_size']
        root_vol_name = server['root_vol_name']
        root_vol_type = server['root_vol_type']
        ebs_kmskey_id = server['ebs_kmskey_id']
        availabilityzone = server['availabilityzone']
        ami_id = server['ami_id']
        ebs_optimized = server['ebs_optimized']
        detailed_monitoring = server['detailed_monitoring']
        iam_role = server['iamRole']
        server_os_family = server['server_os_family']

        server_name_alpha = re.sub('[^0-9a-zA-Z]+', '', server_name)

        str_subnet_id = ",".join(subnet_id)
        str_securitygroup_ids = ",".join(securitygroup_ids)
        if (len(add_vols_size) > 0):
            addvolcount = len(add_vols_size)

        if ebs_optimized == '':
            derived_ebs_optimized = 'false'
        elif ebs_optimized:
            derived_ebs_optimized = 'true'
        else:
            derived_ebs_optimized = 'false'

        if detailed_monitoring == '':
            derived_detailed_monitoring = 'false'
        elif detailed_monitoring:
            derived_detailed_monitoring = 'true'
        else:
            derived_detailed_monitoring = 'false'

        if root_vol_name == '' and server_os_family.lower() == 'windows':
            derived_root_vol_name = '/dev/sda1'
        if root_vol_name == '' and server_os_family.lower() == 'linux':
            derived_root_vol_name = '/dev/xvda'
        if root_vol_name != '':
            derived_root_vol_name = root_vol_name

        if root_vol_type == '':
            derived_root_vol_type = 'gp3'
        if root_vol_type != '':
            derived_root_vol_type = root_vol_type

        param_az = template.add_parameter(
            Parameter(
                server_name_alpha + "AZName",
                Description="The Availability Zone that you want to launch the instance and volumes",
                Type="String",
                Default=availabilityzone
            )
        )

        param_instancetype = template.add_parameter(
            Parameter(
                server_name_alpha + "InstanceType",
                Description="The EC2 instance type. Choose an InstanceType that supports EBS optimization if InstanceEBSOptimized = true.",
                Type="String",
                Default=instance_type

            )
        )

        param_amiid = template.add_parameter(
            Parameter(
                server_name_alpha + "AMIId",
                Description="The ID of the AMI to deploy the instance with.",
                Type="AWS::EC2::Image::Id",
                Default=ami_id
            )
        )

        param_subnetid = template.add_parameter(
            Parameter(
                server_name_alpha + "SubnetId",
                Description="The subnet that you want to launch the instance into, in the form subnet-0123abcd or subnet-01234567890abcdef",
                Type="String",
                Default=str_subnet_id

            )
        )

        param_ebsoptimized = template.add_parameter(
            Parameter(
                server_name_alpha + "EbsOptimized",
                Description="True for the instance to be optimized for Amazon Elastic Block Store I/O. False for it to not be. If you set this to true, choose an InstanceType that supports EBS optimization.",
                Type="String",
                AllowedValues=["true", "false"],
                Default=derived_ebs_optimized

            )
        )

        param_ebskmskey = template.add_parameter(
            Parameter(
                server_name_alpha + "EbsKmsKeyId",
                Description="ID or ARN of the KMS master key to be used to encrypt EBS Volumes",
                Type="String",
                AllowedPattern="^(arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/){0,1}[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$|^$",
                Default=ebs_kmskey_id

            )
        )

        param_securitygroupids = template.add_parameter(
            Parameter(
                server_name_alpha + "securitygroupids",
                Description="Comma-separated list of up to three security group (SG) identifiers. These control access to the EC2 instance",
                Type="CommaDelimitedList",
                Default=str_securitygroup_ids
            )
        )

        param_detailedmonitoring = template.add_parameter(
            Parameter(
                server_name_alpha + "detailedmonitoring",
                Description="True to enable detailed monitoring on the instance, false to use only basic monitoring.",
                Type="String",
                AllowedValues=["true", "false"],
                Default=derived_detailed_monitoring
            )
        )
        param_instance_profile = template.add_parameter(
            Parameter(
                server_name_alpha + "instanceprofile",
                Description="An IAM instance profile defined in your account. The default is an AWS-provided role.",
                Type="String",
                Default=iam_role
            )
        )

        param_rootvolumename = template.add_parameter(
            Parameter(
                server_name_alpha + "rootvolumename",
                Description="The device name of the root volume (for example /dev/xvda or /dev/sda1).",
                Type="String",
                AllowedValues=["/dev/sda1", "/dev/xvda"],
                Default=derived_root_vol_name
            )
        )

        param_rootvolumesize = template.add_parameter(
            Parameter(
                server_name_alpha + "rootvolumesize",
                Description="The size of the root volume for the instance in GiB.",
                Type="Number",
                MinValue=8,
                MaxValue=16384,
                Default=root_vol_size
            )
        )

        param_rootvolumetype = template.add_parameter(
            Parameter(
                server_name_alpha + "rootvolumetype",
                Description="The volume type for root volume. Choose io1, io2, gp2 or gp3 for SSD-backed volumes optimized for transactional workloads. Choose standard for HDD-backed volumes suitable for workloads where data is infrequently accessed.",
                Type="String",
                AllowedValues=["standard", "io1", "io2", "gp2", "gp3"],
                Default=derived_root_vol_type
            )
        )

        add_volume_params(addvolcount, add_vols_name, server_os_family, add_vols_type, template, server_name_alpha,
                          add_vols_size)

        # Adding Required Resources into template
        ec2_instance = template.add_resource(
            ec2.Instance(
                server_name_alpha + "Ec2Instance",
                ImageId=Ref(param_amiid),
                AvailabilityZone=Ref(param_az),
                InstanceType=Ref(param_instancetype),
                SecurityGroupIds=Ref(param_securitygroupids),
                BlockDeviceMappings=[ec2.BlockDeviceMapping(DeviceName=Ref(param_rootvolumename),
                                                            Ebs=ec2.EBSBlockDevice(VolumeSize=Ref(param_rootvolumesize),
                                                                                   Encrypted='true', VolumeType=Ref(
                                                                    param_rootvolumetype)))],
                EbsOptimized=Ref(param_ebsoptimized),
                IamInstanceProfile=Ref(param_instance_profile),
                Tenancy='default',
                SubnetId=Ref(param_subnetid),
                Monitoring=Ref(param_detailedmonitoring)
            )
        )

        ec2_instance.Tags = get_updated_tags(tags, server_name)

        # Adding Additional Volume and Volume Attachment Resource into template
        add_volumes(addvolcount, ebs_kmskey_id, template, server_name_alpha, param_az, param_ebskmskey, tags,
                    ec2_instance)

        # Adding Output Parameters into template
        template.add_output(
            [
                Output(
                    server_name_alpha + "InstanceId",
                    Description="InstanceId of the newly created EC2 instance",
                    Value=Ref(ec2_instance),
                ),
                Output(
                    server_name_alpha + "AZ",
                    Description="Availability Zone of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "AvailabilityZone"),
                ),
                Output(
                    server_name_alpha + "PublicIP",
                    Description="Public IP address of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PublicIp"),
                ),
                Output(
                    server_name_alpha + "PrivateIP",
                    Description="Private IP address of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PrivateIp"),
                ),
                Output(
                    server_name_alpha + "PublicDNS",
                    Description="Public DNSName of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PublicDnsName"),
                ),
                Output(
                    server_name_alpha + "PrivateDNS",
                    Description="Private DNSName of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PrivateDnsName"),
                ),
            ]
        )

        with open(
                tempfile.gettempdir() + template_generated_prefix + app_id + '_' + app_name + template_generated_suffix,
                'w') as f:
            f.write(template.to_yaml())
            f.close()

        print(
            template_generated_prefix + app_id + '_' + app_name + template_generated_suffix + ' Generated Successfully')

    except Exception as e:
        traceback.print_exc()
        print("ERROR: EC2 CFT Template Generation Failed With Error: " + str(e))
        return "ERROR: EC2 CFT Template Generation Failed With Error: " + str(e)


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
