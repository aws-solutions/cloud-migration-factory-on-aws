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
from policy import MFAuth
from botocore import config

if 'solution_identifier' in os.environ:
    solution_identifier= json.loads(os.environ['solution_identifier'])
    user_agent_extra_param = {"user_agent_extra":solution_identifier}
    boto_config = config.Config(**user_agent_extra_param)
else:
    boto_config = None

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

        stackresultset = []
        
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

        try:    

   
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

            
            getserver = scan_dynamodb_table('server')
            
            msgserver= 'Unable to Retrieve Data from Dynamo DB Server Table'
            if getserver is not None and "ERROR" in getserver:
                 return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': msgserver}  

            servers = sorted(getserver, key = lambda i: i['server_name'])
    
            

            # Get Wave name 
        
            wavename=''
            for wave in waves:
                if str(wave['wave_id']) == body['waveid']:
                    for character in wave['wave_name']:
                        if character.isalnum():
                            wavename += character 
                        
            # App Table Attributes for S3 Path Generation
        

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
                        
                        #gfbuild_bucket='mfcloudformationtemplates'

                        print('S3 Bucket to Load Cloud formation Templates'+gfbuild_bucket)

                    
                        #S3 path and Json File 
                    
                        s3_path=accountid+'/'+wavename+'/CFN_Template_'+appid+'_'+appname+'.yaml'
                        #s3_path='CFN_Template_'+appid+'_'+appname+'.json'
                    
                        print('S3 Path Along with JSON File:'+ s3_path)
                    


                        #Later Enchancement to deploy the stack
                        template_url='https://'+gfbuild_bucket+'.s3.amazonaws.com/'+s3_path;
                        s3 = boto3.client('s3')
                        try:
                            result = s3.get_bucket_policy(Bucket=gfbuild_bucket)
                            data = json.loads(result['Policy'])
                            totalstatements=len(data['Statement'])
                        except Exception:
                            pass
                            json_data = json.dumps({})
                            totalstatements = 0
                            data={"Statement": []}

                        
                        
                        
                        ObjectPermission = {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456:root"
                                },
                            "Action": ["s3:GetObject","s3:GetObjectVersion"],
                            "Resource": "arn:aws:s3:::s3bcucket/*"
                           }

                        
                        
                        i=0
                        
                        accountarnval='arn:aws:iam::'+accountid+':root'
                        s3bucketname='arn:aws:s3:::'+gfbuild_bucket
                        s3bucketobjects='arn:aws:s3:::'+gfbuild_bucket+'/*'
                        
                        accountexists='No'
                        
                        while i<totalstatements:
                            if (data['Statement'][i]['Principal']['AWS'] ==accountarnval):
                                accountexists='Yes'
                            i=i+1
                        
                        
                        if(accountexists=='No'):
                        
                            data['Statement'].append(ObjectPermission)
                            data['Statement'][totalstatements]['Principal']['AWS']=accountarnval
                            data['Statement'][totalstatements]['Resource']=s3bucketobjects
                            bucket_policy = json.dumps(data)
                            print(bucket_policy)

                            # Set the new policy
                            s3.put_bucket_policy(Bucket=gfbuild_bucket, Policy=bucket_policy)
                        
                        print(data)
                        
                        stack_result=launch_stack(template_url,appid,appname,gfbuild_bucket,accountid)
                        stackresultset.append(stack_result)
            

            successfulstackdep='Yes'
            if stackresultset is not None:
                for stackresult in stackresultset:
                    if stackresult is not None and "ERROR" in stackresult:
                        successfultempgen='No' 
                        
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': stackresult} 

            if successfulstackdep == 'Yes':
                
                msg = 'EC2 Deployment has been completed'
                for server in servers:
                    if "app_id" in server and "r_type" in server:
                        print(server['r_type'].upper())
                        if server['r_type'].upper() == 'REPLATFORM' :
                            # update
                            serverresponse = servers_table.get_item(Key={'server_id': server['server_id']})
                            serveritem = serverresponse['Item']
                            serveritem['migration_status'] = 'CF Deployment Submitted'
                            servers_table.put_item(Item=serveritem)
                        
                print(msg)
                return {'headers': {**default_http_headers},
                       'statusCode': 200, 'body': msg}   
                                
        except Exception as e:
            
            print('Lambda Handler Main Function Failed' + str(e))
            return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'Lambda Handler Main Function Failed with error : '+str(e)}      




#Launch Stack based on Cloud Formation template Generate , It's Future Enhancement , not used at the moment
  
def launch_stack(template_url,appid,appname,bucketname,targetaccountid):
    # try:
    

        sts_client = boto3.client('sts', region_name=os.environ.get('region'))
        rolearnvalue="arn:aws:iam::"+targetaccountid+":role/Factory-Replatform-EC2Deploy"
        assumed_role_object=sts_client.assume_role(
        RoleArn=rolearnvalue,
        RoleSessionName="AssumeRoleSessionMFReplatform"
        )
        credentials=assumed_role_object['Credentials']
        cfn=boto3.client(
        'cloudformation',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        config=boto_config
        )
        stackname = 'Create-EC2-Servers-for-App-Id-'+appid+appname
        capabilities = ['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND','CAPABILITY_NAMED_IAM']
        stackdata = cfn.create_stack(
        StackName=stackname,
        DisableRollback=True,
        TemplateURL=template_url,
        Capabilities=capabilities
        )
        return stackdata         
    # except Exception as e:
        # print( "ERROR: Cloud Formation Stack Creation Failed with Error: " + str(e) )    
        # return "ERROR: Cloud Formation Stack Creation Failed with Error: " + str(e) 
        
#Pagination for DDB table scan  


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
    