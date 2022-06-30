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

from __future__ import print_function
import boto3
import json
import sys
import os
import troposphere.ec2 as ec2
from troposphere import Base64, Tags,FindInMap, GetAtt, Output, Parameter, Ref, Template
from policy import MFAuth
import traceback

headers = {'Content-Type': 'application/json'}
if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

application = os.environ['application']
environment = os.environ['environment']
servers_table_name = '{}-{}-servers'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)
waves_table_name = '{}-{}-waves'.format(application, environment)
servers_table = boto3.resource('dynamodb').Table(servers_table_name)
apps_table = boto3.resource('dynamodb').Table(apps_table_name)
waves_table = boto3.resource('dynamodb').Table(waves_table_name)

def lambda_handler(event, context):
        # Verify user has access to run ec2 replatform functions.
        auth = MFAuth()
        authResponse = auth.getUserResourceCreationPolicy(event, 'EC2')
        if authResponse['action'] != 'allow':
            return {'headers': {**default_http_headers},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}

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
            Templategenlist = GetServerList(body['waveid'],servers_table)
            print(" Main Templategenlist:")
            print(Templategenlist)
            successfultempgen='Yes'
            if Templategenlist is not None:
                for Tempaltegen in Templategenlist:
                    if Tempaltegen is not None and "ERROR" in Tempaltegen:
                        successfultempgen='No'
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': Tempaltegen}


          # Read Apps Dynamo DB Table
            getapp = scan_dynamodb_table('app')
            msgapp= 'Unable to Retrieve Data from Dynamo DB App Table'
            if getapp is not None and "ERROR" in getapp:
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body':msgapp }

            apps = sorted(getapp, key = lambda i: i['app_name'])

            # Read Waves Dynamo DB Table
            getwave = scan_dynamodb_table('wave')
            msgwave= 'Unable to Retrieve Data from Dynamo DB Wave Table'
            if getwave is not None and "ERROR" in getwave:
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': msgwave}

            waves = sorted(getwave, key = lambda i: i['wave_name'])

            for app in apps:
                appname=''
                appid=''
                projectname=''
                accountid=''

            # Read App Name and App Id

                if 'wave_id' in app:
                    if str(app['wave_id']) == body['waveid']:

                        for character in app['app_name']:
                            if character.isalnum():
                                appname += character
                        for character in app['app_id']:
                            if character.isalnum():
                                appid += character


            # Get Wave name

            wavename=''
            for wave in waves:
                if str(wave['wave_id']) == body['waveid']:
                    for character in wave['wave_name']:
                        if character.isalnum():
                            wavename += character

            # App Table Attributes for S3 Path Generation

            generated_template_uris = []

            for app in apps:
                appname=''
                appid=''
                projectname=''
                accountid=''

                if 'wave_id' in app:
                    if str(app['wave_id']) == body['waveid']:

                        for character in app['app_name']:
                            if character.isalnum():
                                appname += character

                        print('App Name :' + appname)

                        for character in app['app_id']:
                            if character.isalnum():
                                appid += character

                        print('App Id :' + appid)


                        for character in app['aws_accountid']:
                            if character.isnumeric():
                                accountid += character

                        #AWS Account Id to Create S3 Path
                        aws_account_id = context.invoked_function_arn.split(":")[4]

                        gfbuild_bucket = "{}-{}-{}-gfbuild-cftemplates".format(
                        application, environment, aws_account_id)

                        print('S3 Bucket to Load Cloud formation Templates :'+gfbuild_bucket)

                        #lambda path and Json File

                        lambda_path='/tmp/'+'CFN_Template_'+appid+'_'+appname+'.yaml'

                        #S3 path and Json File

                        s3_path=accountid+'/'+wavename+'/CFN_Template_'+appid+'_'+appname+'.yaml'

                        print('S3 Path Along with JSON File: '+ s3_path)

                        #Upload Template into S3 Bucket

                        s3 = boto3.resource('s3')
                        s3.meta.client.upload_file(lambda_path, gfbuild_bucket.replace(" ", ""), s3_path)
                        generated_template_uris.append('s3://' +  gfbuild_bucket.replace(" ", "") + '/' + s3_path)


            if successfultempgen == 'Yes':
                msg = 'EC2 Cloud Formation Template Generation Completed. ' + str(len(generated_template_uris)) + ' template S3 URIs created: [' + ','.join(generated_template_uris) + '].'
                print(msg)
                return {'headers': {**default_http_headers},
                       'statusCode': 200, 'body': msg}

        except Exception as e:
            traceback.print_exc()
            print('Lambda Handler Main Function Failed' + str(e))
            return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'Lambda Handler Main Function Failed with error : '+str(e)}


def GetServerList(waveid,servers_table):

    try:

        templategenlist = []
        # Get all Apps and servers from migration factory

        getserver = scan_dynamodb_table('server')

        if getserver is not None and "ERROR" in getserver:
            templategenlist.append ("ERROR: Unable to Retrieve Data from Dynamo DB Server table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB Server table')

        servers = sorted(getserver, key = lambda i: i['server_name'])

        getapp = scan_dynamodb_table('app')
        if getapp is not None and "ERROR" in getapp:
            templategenlist.append ("ERROR: Unable to Retrieve Data from Dynamo DB App table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB App table')

        apps = sorted(getapp, key = lambda i: i['app_name'])

        # Get App list
        applist = []
        appnamelist = []

        templategenerror= 'No'

        # Pull App Id and App Name from Apps Dynamo table

        for app in apps:
            if 'wave_id' in app:
                if str(app['wave_id']) == waveid:
                    applist.append(app['app_id'])
                    appnamelist.append(app['app_name'])


        serverlist = []


        apptotal=int(len(applist))
        appnumb=0

        #Read App by app and pull the server list

        while appnumb < apptotal:

        # Open Cloud Formation template at Application level

            template = Template()
            template.set_version("2010-09-09")
            template.set_description("Builds stack for EC2 Servers for the Application " +str(appnamelist[appnumb]) )

        # Pull Server List and Attributes

            for server in servers:
                if "app_id" in server and "r_type" in server:
                    addvolcount=0
                    print(server['r_type'].upper())
                    if applist[appnumb] == server['app_id'] and server['r_type'].upper() == 'REPLATFORM' :
                        serverlist.append(server)


        # Call Generate Cloud Formation Template Function for each Server
                if not "add_vols_size" in server:
                    server['add_vols_size']=''
                if not "add_vols_name" in server:
                    server['add_vols_name']=''
                if not "add_vols_type" in server:
                    server['add_vols_type']=''
                if not "ebs_optimized" in server:
                    server['ebs_optimized']=''
                if not "detailed_monitoring" in server:
                    server['detailed_monitoring']=''
                if not "root_vol_name" in server:
                    server['root_vol_name']=''
                if not "root_vol_type" in server:
                    server['root_vol_type']=''
                if not "ebs_kmskey_id" in server:
                    server['ebs_kmskey_id']=''

                print('Input Values Going to be Passed for CFT Generation:')
                print(server)
                if "r_type" in server and server['r_type'].upper() == 'REPLATFORM':
                    tags = []
                    if 'tags' in server:
                        tags = server['tags']
                    server_name_short = server['server_name'].lower().split(".")[0]
                    templategen=generate_cft(apptotal,applist[appnumb],appnamelist[appnumb],template,addvolcount,server_name_short,server['instanceType'].lower(),server['securitygroup_IDs'],
                    server['subnet_IDs'],server['tenancy'],server['add_vols_size'],server['add_vols_name'],server['add_vols_type'],
                    server['root_vol_size'],server['root_vol_name'],server['root_vol_type'],server['ebs_kmskey_id'],server['availabilityzone']
                    ,server['ami_id'],server['ebs_optimized'],server['detailed_monitoring'],server['iamRole'],tags,server['server_os_family'])
                    templategenlist.append(templategen)

                    # update
                    serverresponse = servers_table.get_item(Key={'server_id': server['server_id']})
                    serveritem = serverresponse['Item']
                    serveritem['migration_status'] = 'CF Template Generated'
                    servers_table.put_item(Item=serveritem)

            appnumb=appnumb+1


        if len(serverlist) == 0:
            templategenlist.append ("ERROR: Server list for wave " + waveid + " in Migration Factory is empty....")

        print("templategenlist:")
        print(templategenlist)

        for templategenval in templategenlist:

            if templategenval is not None:

                templategenerror='Yes'

        if templategenerror == 'Yes':

            return templategenlist

    except Exception as e:
        templategenlist.append ("ERROR: Getting server list failed. Failed with Error:" + str(e))
        print("ERROR: Getting server list failed. Failed with Error: " + str(e))
        return templategenlist

# Cloud Formation Template Generation

def generate_cft(apptotal,app_id,app_name,template,addvolcount,server_name,instance_type,securitygroup_ids,subnet_id,tenancy,add_vols_size,add_vols_name,add_vols_type,root_vol_size,root_vol_name,root_vol_type,ebs_kmskey_id,availabilityzone,ami_id,ebs_optimized,detailed_monitoring,iamRole,tags,server_os_family):

    try:
        print("************************************")
        print("Cloud Formation Template Generation ....")
        print("************************************")

        str_subnet_id = ",".join(subnet_id)
        str_securitygroup_ids = ",".join(securitygroup_ids)
        if (len(add_vols_size)>0 ):
            addvolcount=len(add_vols_size)


        if ebs_optimized == '' :
            Derived_ebs_optimized='false'
        elif ebs_optimized:
            Derived_ebs_optimized='true'
        else:
            Derived_ebs_optimized='false'

        if detailed_monitoring == '' :
            Derived_detailed_monitoring='false'
        elif detailed_monitoring :
            Derived_detailed_monitoring='true'
        else:
            Derived_detailed_monitoring='false'

        if root_vol_name == '' and server_os_family == 'windows' :
            Derived_root_vol_name='/dev/sda1'
        if root_vol_name == '' and server_os_family == 'linux' :
            Derived_root_vol_name='/dev/xvda'
        if root_vol_name != '' :
            Derived_root_vol_name=root_vol_name

        if root_vol_type == '' :
            Derived_root_vol_type='gp2'
        if root_vol_type != '' :
            Derived_root_vol_type=root_vol_type

        param_az = template.add_parameter(
            Parameter(
                server_name+"AZName",
                Description="The Availability Zone that you want to launch the instance and volumes",
                Type="String",
                Default=availabilityzone
            )
        )

        param_instancetype = template.add_parameter(
            Parameter(
                server_name+"InstanceType",
                Description="The EC2 instance type. Choose an InstanceType that supports EBS optimization if InstanceEBSOptimized = true.",
                Type="String",
                Default=instance_type

            )
        )


        param_amiid = template.add_parameter(
            Parameter(
                server_name+"AMIId",
                Description="The ID of the AMI to deploy the instance with.",
                Type= "AWS::EC2::Image::Id",
                Default=ami_id
            )
        )

        param_subnetid = template.add_parameter(
            Parameter(
                server_name+"SubnetId",
                Description="The subnet that you want to launch the instance into, in the form subnet-0123abcd or subnet-01234567890abcdef",
                Type="String",
                Default=str_subnet_id

            )
         )

        param_ebsoptimized = template.add_parameter(
            Parameter(
                server_name+"EbsOptimized",
                Description="True for the instance to be optimized for Amazon Elastic Block Store I/O. False for it to not be. If you set this to true, choose an InstanceType that supports EBS optimization.",
                Type="String",
                AllowedValues =[ "true", "false" ],
                Default=Derived_ebs_optimized

            )
         )

        param_ebskmskey = template.add_parameter(
            Parameter(
                server_name+"EbsKmsKeyId",
                Description="ID or ARN of the KMS master key to be used to encrypt EBS Volumes",
                Type="String",
                AllowedPattern= "^(arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/){0,1}[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$|^$",
                Default=ebs_kmskey_id

            )
         )


        param_securitygroupids = template.add_parameter(
            Parameter(
                server_name+"securitygroupids",
                Description="Comma-separated list of up to three security group (SG) identifiers. These control access to the EC2 instance",
                Type="CommaDelimitedList",
                Default=str_securitygroup_ids
            )
        )

        param_detailedmonitoring = template.add_parameter(
            Parameter(
                server_name+"detailedmonitoring",
                Description="True to enable detailed monitoring on the instance, false to use only basic monitoring.",
                Type="String",
                AllowedValues= [ "true", "false" ],
                Default=Derived_detailed_monitoring
            )
        )
        param_instance_profile = template.add_parameter(
            Parameter(
                server_name+"instanceprofile",
                Description="An IAM instance profile defined in your account. The default is an AWS-provided role.",
                Type="String",
                Default=iamRole
            )
        )

        param_rootvolumename = template.add_parameter(
            Parameter(
                server_name+"rootvolumename",
                Description="The device name of the root volume (for example /dev/xvda or /dev/sda1).",
                Type="String",
                AllowedValues= ["/dev/sda1", "/dev/xvda"],
                Default=Derived_root_vol_name
            )
        )

        param_rootvolumesize = template.add_parameter(
            Parameter(
                server_name+"rootvolumesize",
                Description="The size of the root volume for the instance in GiB.",
                Type="Number",
                MinValue=8,
                MaxValue=16384,
                Default=root_vol_size
            )
        )

        param_rootvolumetype = template.add_parameter(
            Parameter(
                server_name+"rootvolumetype",
                Description="The volume type for root volume. Choose io1, io2, gp2 or gp3 for SSD-backed volumes optimized for transactional workloads. Choose standard for HDD-backed volumes suitable for workloads where data is infrequently accessed.",
                Type="String",
                AllowedValues=[ "standard", "io1", "io2", "gp2", "gp3" ],
                Default=Derived_root_vol_type
            )
        )

  # Adding Additional Volume Parameters into template
        linuxlistofvolumenames=["/dev/sdf","/dev/sdg","/dev/sdh","/dev/sdi","/dev/sdj","/dev/sdk","/dev/sdl","/dev/sdm","/dev/sdn","/dev/sdo","/dev/sdp","/dev/sdq","/dev/sdr","/dev/sds","/dev/sdt","/dev/sdu","/dev/sdv","/dev/sdw","/dev/sdx","/dev/sdy","/dev/sdz"]
        windowslistofvolumenames=["xvdf","xvdg","xvdh","xvdi","xvdj","xvdk","xvdl","xvdm","xvdn","xvdo","xvdp","xvdq","xvdr","xvds","xvdt","xvdu","xvdv","xvdw","xvdy","xvdz"]
        volumeparmid=1
        while volumeparmid <= addvolcount :
            if add_vols_name == '' and server_os_family == 'windows':
                DerivedVolumename=windowslistofvolumenames[volumeparmid-1]
            elif add_vols_name == '' and server_os_family == 'linux':
                DerivedVolumename=linuxlistofvolumenames[volumeparmid-1]
            else:
                DerivedVolumename=add_vols_name[volumeparmid-1]

            if add_vols_type == '':
                DerivedVolumtype='gp2'
            else:
                DerivedVolumtype=add_vols_type[volumeparmid-1]

            param_addvolumename = template.add_parameter(
                Parameter(
                    server_name+"volume" + str(volumeparmid) +"name",
                    Description="The device name for additional Volumes ( example, /dev/sdf through /dev/sdp for Linux or xvdf through xvdp for Windows).",
                    Type="String",
                    Default=DerivedVolumename
                )
                )
            param_addvolumetype = template.add_parameter(
                Parameter(
                    server_name+"volume" + str(volumeparmid) +"type",
                    Description="The volume type for additional volume. Choose io1, io2, gp2 or gp3 for SSD-backed volumes optimized for transactional workloads. Choose standard for HDD-backed volumes suitable for workloads where data is infrequently accessed.",
                    Type="String",
                    AllowedValues=[ "standard", "io1", "io2", "gp2", "gp3" ],
                    Default=DerivedVolumtype
                )
                )

            param_addvolumesize = template.add_parameter(
                Parameter(
                    server_name+"volume" + str(volumeparmid) +"size",
                    Description="The size of the additional volume in GiB.",
                    Type="Number",
                    MinValue=1,
                    MaxValue=16384,
                    Default=add_vols_size[volumeparmid-1]
                )
                )
            volumeparmid=volumeparmid+1

  # Adding Required Resources into template

        ec2_instance = template.add_resource(
            ec2.Instance(
                server_name+"Ec2Instance",
                ImageId=Ref(param_amiid),
                AvailabilityZone=Ref(param_az),
                InstanceType=Ref(param_instancetype),
                SecurityGroupIds=Ref(param_securitygroupids),
                BlockDeviceMappings=[ec2.BlockDeviceMapping(DeviceName=Ref(param_rootvolumename),Ebs=ec2.EBSBlockDevice(VolumeSize=Ref(param_rootvolumesize),Encrypted='true',VolumeType=Ref(param_rootvolumetype)))],
                EbsOptimized=Ref(param_ebsoptimized),
                IamInstanceProfile=Ref(param_instance_profile),
                Tenancy='default',
                SubnetId=Ref(param_subnetid),
                Monitoring=Ref(param_detailedmonitoring)

            )
        )

        updatedTags = []
        for element in tags:
            updatedTag = {}
            updatedTag['Key'] = element['key']
            updatedTag['Value'] = element['value']
            updatedTags.append(updatedTag)

        ec2_instance.Tags = updatedTags

        volumeid=1

     # Adding Additional Volume and Volume Attachment Resource into template

        while volumeid <= addvolcount :


            if len(str(ebs_kmskey_id)) == 0:
                volume= template.add_resource(
                                ec2.Volume(
                                server_name+"Volume"+str(volumeid),
                                Encrypted='true',
                                AvailabilityZone=Ref(param_az),
                                Size=Ref(server_name+'volume'+str(volumeid)+'size'),
                                VolumeType=Ref(server_name+'volume'+str(volumeid)+'type') ) )
                volume.Tags = tags
            else:
                volume= template.add_resource(
                                ec2.Volume(
                                server_name+"Volume"+str(volumeid),
                                Encrypted='true',
                                AvailabilityZone=Ref(param_az),
                                KmsKeyId=Ref(param_ebskmskey),
                                Size=Ref(server_name+'volume'+str(volumeid)+'size'),
                                VolumeType=Ref(server_name+'volume'+str(volumeid)+'type') ) )
                volume.Tags = tags

            volume= template.add_resource(
                            ec2.VolumeAttachment(
                            server_name+"Volume"+str(volumeid)+"Attachment",
                             VolumeId=Ref(server_name+'Volume'+str(volumeid)),
                             Device=Ref(server_name+'volume'+str(volumeid)+'name'),
                             InstanceId=Ref(ec2_instance)
                           ) )

            volumeid=volumeid+1


      # Adding Output Parameters into template

        template.add_output(
            [
                Output(
                    server_name+"InstanceId",
                    Description="InstanceId of the newly created EC2 instance",
                    Value=Ref(ec2_instance),
                ),
                Output(
                    server_name+"AZ",
                    Description="Availability Zone of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "AvailabilityZone"),
                ),
                Output(
                    server_name+"PublicIP",
                    Description="Public IP address of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PublicIp"),
                ),
                Output(
                    server_name+"PrivateIP",
                    Description="Private IP address of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PrivateIp"),
                ),
                Output(
                    server_name+"PublicDNS",
                    Description="Public DNSName of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PublicDnsName"),
                ),
                Output(
                    server_name+"PrivateDNS",
                    Description="Private DNSName of the newly created EC2 instance",
                    Value=GetAtt(ec2_instance, "PrivateDnsName"),
                ),
            ]
        )
        appname=''
        appid=''
        for character in app_name:
            if character.isalnum():
                appname += character


        for character in app_id:
            if character.isalnum():
                appid += character

        original_stdout = sys.stdout
        with open('/tmp/'+'CFN_Template_'+app_id+'_'+app_name+'.yaml', 'w') as f:
              sys.stdout = f
              sys.stdout = print(template.to_yaml())


        f.close()
        sys.stdout = original_stdout

        print('CFN_Template_'+app_id+'_'+app_name+'.json' + ' Generated Successfully')

    except Exception as e:
        traceback.print_exc()
        print( "ERROR: EC2 CFT Template Generation Failed With Error: " + str(e))
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
                response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
            elif datatype == 'app':
                response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
            elif datatype == 'wave':
                response = waves_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
            scan_data.extend(response['Items'])
        return(scan_data)

    except Exception as e:
        print( "ERROR: Unable to retrieve the data from Dynamo DB table: " + str(e) )
        return "ERROR: Unable to retrieve the data from Dynamo DB table: " + str(e)
