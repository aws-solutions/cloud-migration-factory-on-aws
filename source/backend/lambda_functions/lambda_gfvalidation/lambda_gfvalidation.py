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
import sys
import os
import json
from policy import MFAuth

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

            body = json.loads(event['body'])
            if 'accountid' not in body:
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': 'Target Account Id is required'}
                        
        except Exception as e:
            print(e)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'malformed json input'}

        try:
            ValidationList = GetServerList(body['waveid'])
            successfulvalidation='Yes'
            if ValidationList is not None:
                for Validation in ValidationList:
                    if Validation is not None and "ERROR" in Validation:
                        successfulvalidation='No' 
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': Validation}

            if successfulvalidation == 'Yes':
                msg = 'EC2 Input Validation Completed'
                print(msg)
                return {'headers': {**default_http_headers},
                       'statusCode': 200, 'body': msg}   
        except Exception as e:
            
            print('Lambda Handler Main Function Failed' + str(e))
            return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'Lambda Handler Main Function Failed with error : '+str(e)}    
 
def GetServerList(waveid):

    try:

       # Get all Apps and servers from migration factory
        
        validationlist = []
        
        getserver = scan_dynamodb_table('server')

        if getserver is not None and "ERROR" in getserver:
            validationlist.append ("ERROR: Unable to Retrieve Data from Dynamo DB Server table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB Server table')    

        servers = sorted(getserver, key = lambda i: i['server_name'])

        getapp = scan_dynamodb_table('app')
        if getapp is not None and "ERROR" in getapp:
            validationlist.append ("ERROR: Unable to Retrieve Data from Dynamo DB App table")
            print('ERROR: Unable to Retrieve Data from Dynamo DB App table')    
        apps = sorted(getapp, key = lambda i: i['app_name'])    
        # Get App list
        applist = []
        appnamelist = []
        validationvalue=''
        
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
        
   
        # Pull Server List and Attributes
        
            for server in servers:
                if "app_id" in server:
                    addvolcount=0
                    if applist[appnumb] == server['app_id'] and server['r_type'].upper() == 'REPLATFORM':
                        serverlist.append(server)
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
                        if not "add_vols_size" in server:
                            server['add_vols_size']=''
                        print('Input Values Going to be Passed for Validation:')
                        print(server)   
        
        # Call the Validation Script to Validate All Input Required Atrributes 
                        if server['r_type'].upper() == 'REPLATFORM':
                            validation=validateinput(apptotal,applist[appnumb],appnamelist[appnumb],addvolcount,server['server_name'].lower(),
                            server['instanceType'].lower(),server['securitygroup_IDs'],
                            server['subnet_IDs'],server['tenancy'],server['add_vols_size'],server['add_vols_name'],server['add_vols_type'],
                            server['root_vol_size'],server['root_vol_name'],server['root_vol_type'],server['ebs_kmskey_id'],server['availabilityzone']
                            ,server['ami_id'],server['ebs_optimized'],server['detailed_monitoring'],server['iamRole'],server['server_os_family'],server['server_id'],servers_table)
                        
                            validationlist.append(validation)
                       
            
            appnumb=appnumb+1                
        
        # Validate the Input List of Servers  
        
        if len(serverlist) == 0:
            validationlist.append ("ERROR: Server list for wave " + waveid + " in Migration Factory is empty....")

        # Check Any Validation Steps are failed  
 
        for validation in validationlist:

            if validation is not None:

                validationvalue='Yes'    
         
        # Return Validation Message if any Validation Step failed 
         
        if validationvalue=='Yes':
            return validationlist    

    except Exception as e:
        validationlist.append ("ERROR: Getting server list failed...." + str(e))
        print("ERROR: Getting server list failed...." + str(e))
        return validationlist      

# Input Data Validation

def validateinput(apptotal,app_id,app_name,addvolcount,server_name,instance_type,securitygroup_ids,subnet_id,tenancy,add_vols_size,add_vols_name,add_vols_type,root_vol_size,root_vol_name,root_vol_type,ebs_kmskey_id,availabilityzone,ami_id,ebs_optimized,detailed_monitoring,iamRole,server_os,server_id,servers_table):

    try:


        print("************************************")
        print("Input Data Validation Starting....")
        print("************************************")

    # Additional Volume Parameters Validation

        if(add_vols_name!=''):
    
            if ((len(add_vols_size)!=len(add_vols_name)) ):
                msg = 'ERROR:Additional Volume Names are missing for some additional Volume, Please provide value for all additional volumes or Leave as Blank to Use Default ' + server_name
                print(msg)
                return msg          
    
        if(add_vols_type!=''):
    
            if ((len(add_vols_size)!=len(add_vols_type)) ):
        
                msg = 'Additional Volume Types are missing for some additional Volume, Please provide value for all additional volumes or Leave as Blank to Use Default ' + server_name
                print(msg)
                return msg         


        if ( len(add_vols_size)> 0  ):
                addvolcount=len(add_vols_size)
     
        print("addvolcount:"+str(addvolcount))

        for volume_size in add_vols_size:
            if(int(volume_size)< 1 or (int(volume_size)> 16384)):
                msg = 'ERROR:Additional Volume Size Is Incorrect for Server:' + server_name + ' Volume Size needs to between 1 GiB and 16384 GiB'
                print(msg)
                return msg

        listofvolumetypes=["standard", "io1", "io2", "gp2", "gp3",""]
        for volume_type in add_vols_type:
            if (volume_type != ''):

                if (str(volume_type) not in listofvolumetypes):
                    msg = 'ERROR:Additional Volume Type Is Incorrect for Server:' + server_name + ' Allowed List of Volume Types "standard", "io1", "io2", "gp2", "gp3" '
                    print(msg)
                    return msg

        listofvolumenames=["/dev/sdf","/dev/sdg","/dev/sdh","/dev/sdi","/dev/sdj","/dev/sdk","/dev/sdl","/dev/sdm","/dev/sdn","/dev/sdo","/dev/sdp","xvdf","xvdg","xvdh","xvdi","xvdj","xvdk","xvdl","xvdm","xvdn","xvdo","xvdp",""]
        for volume_name in add_vols_name:
            if(volume_name!=''):
                if(str(volume_name) not in listofvolumenames):
                    msg = 'ERROR:Additional Volume Name Is Incorrect for Server:'+server_name+ ' Allowed Values for Linux "/dev/sdf","/dev/sdg","/dev/sdh","/dev/sdi","/dev/sdj","/dev/sdk","/dev/sdl","/dev/sdm","/dev/sdn","/dev/sdo","/dev/sdp", and for Window OS use "xvdf","xvdg","xvdh","xvdi","xvdj","xvdk","xvdl","xvdm","xvdn","xvdo","xvdp",""'
                    print(msg)
                    return msg
    
        if (len(root_vol_size)==0):
            msg = 'ERROR:The Root Volume Size field is empty for Server: ' + server_name
            print(msg)
            return msg

        if (len(subnet_id)==0):
            msg = 'ERROR:The Subnet_IDs field is empty for Server: ' + server_name
            print(msg)
            return msg
    
        if (len(securitygroup_ids)==0):

            msg = 'ERROR:The security group id is empty for Server: ' + server_name
            print(msg)
            return msg 
    
        if (len(instance_type)==0):
            msg = 'ERROR:The instance type is empty for Server: ' + server_name
            print(msg)
            return msg
    
        tenancylist=['Shared','Dedicated','Dedicated host']

        if (tenancy not in tenancylist):
            msg = 'ERROR:The tenancy value is Invalid for Server: ' + server_name + ' Allowed Values "Shared","Dedicated","Dedicated host" '
            print(msg)
            return msg 

    
        if (int(root_vol_size)<8 or int(root_vol_size)>16384 ):

            msg = 'ERROR:The Root Volume Size Is Incorrect for Server: ' + server_name + ' Volume Size needs to between 8 GiB and 16384 GiB '
            print(msg)
            return msg

    
        if (root_vol_type not in listofvolumetypes ):

            msg = 'ERROR:The Root Volume Type Is Incorrect for Server: ' + server_name + ' Allowed List of Volume Types "standard", "io1", "io2", "gp2", "gp3"'
            print(msg)
            return msg

    
        listofrootvolumenames=["/dev/sda1", "/dev/xvda",""]     
 
        if (root_vol_name not in listofrootvolumenames ):

            msg = 'ERROR:The Root Volume Name Is Incorrect for Server: ' + server_name + ' Allowed List of Volume Names "/dev/sda1", "/dev/xvda" '
            print(msg)
            return msg
    
        if (len(ami_id)==0):

            msg = 'ERROR:The AMI Id Value is missing for Server: ' + server_name
            print(msg)
            return msg

    
        if (len(iamRole)==0):

            msg = 'ERROR:The iamRole is missing for Server: ' + server_name
            print(msg)
            return msg

    
        if (len(availabilityzone)==0):

            msg = 'ERROR:The availability zone is missing for Server: ' + server_name
            print(msg)
            return msg
    
        allowedvalues=["", True, False]
    
        if (ebs_optimized not in allowedvalues):

            msg = 'ERROR:The ebs_optimized value is incorrect for Server : ' + server_name + ' Allowed Values [true,false,""]'
            print(msg)
            return msg
    
        if (detailed_monitoring not in allowedvalues):

            msg = 'ERROR:The detailed_monitoring value is incorrect for Server: ' + server_name + ' Allowed Values [true,false,""]'
            print(msg)
            return msg

        # update
        serverresponse = servers_table.get_item(Key={'server_id': server_id})
        serveritem = serverresponse['Item']
        serveritem['migration_status'] = 'Validation Completed'
        servers_table.put_item(Item=serveritem)



    except Exception as e:
        print( "ERROR: EC2 Input Validation Failed.Failed With error: " + str(e))    
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
    