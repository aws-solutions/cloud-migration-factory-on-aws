#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import boto3
import logging
import os
import datetime
import time

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

application = os.environ['application']
environment = os.environ['environment']
database = os.environ['database']
AthenaWorkGroup = os.environ['workgroup']
print("*** View Name ***")
newapp = ''
newenv = ''
if "-" in application:
    newapp = application.lower().replace("-", "_")
else:
    newapp = application.lower()
if "-" in environment:
    newenv = environment.lower().replace("-", "_")
else:
    newenv = environment.lower()
ViewName = newapp + "_" + newenv + "_" + "tracker_general_view"
print(ViewName)
print("*** App Table Name ***")
AppTableName = application.lower() + "-" + environment.lower() + \
               "-app-extract-table"
print(AppTableName)
print("*** Server Table Name ***")
ServerTableName = application.lower() + "-" + environment.lower() + \
                  "-server-extract-table"
print(ServerTableName)
print("*** Query ***")
query_columns = '"a"."cloudendure_projectname" , "a"."app_name" , ' \
                '"a"."wave_id" , '\
                '"a"."app_id", '\
                '"b"."server_name" , '\
                '"b"."instancetype" , '\
                '"b"."migration_status" , '\
                '"b"."server_id" , '\
                '"b"."server_fqdn" , '\
                '"b"."server_os_family" , '\
                '"b"."server_os_version" , '\
                '"b"."replication_status" , '\
                '"b"."server_environment" '
query_join = ' LEFT JOIN "{}" a ON "b"."app_id" = "a"."app_id"'
query_template = 'CREATE OR REPLACE VIEW "{}" AS SELECT ' + query_columns + ' FROM "{}" b' + query_join   # nosec B608
query = query_template.format(ViewName, ServerTableName, AppTableName)

def lambda_handler(event, context):
    log.info('Function Starting')
    log.info(f'Incoming Event:\n{json.dumps(event, indent=2)}')
    log.info(f'Context Object:\n{vars(context)}')
    aws_account_id = context.invoked_function_arn.split(":")[4]
    athena_result_bucket = "s3://{}-{}-{}-athena-results/".format(
        application, environment, aws_account_id)
    athena_client = boto3.client("athena")
    athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database,
                               'Catalog': 'AwsDataCatalog'},
        ResultConfiguration={
            'OutputLocation': athena_result_bucket,
        },
        WorkGroup=AthenaWorkGroup
    )
