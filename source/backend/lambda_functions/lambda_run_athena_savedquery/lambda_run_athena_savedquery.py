#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os

import cmf_boto
from cmf_logger import logger

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

AppTableName = application.lower() + "-" + environment.lower() + \
               "-app-extract-table"
print(f"App Table Name - {AppTableName}")

ServerTableName = application.lower() + "-" + environment.lower() + \
                  "-server-extract-table"
print(f"Server Table Name - {ServerTableName}")

WaveTableName = application.lower() + "-" + environment.lower() + \
                  "-wave-extract-table"
print(f"Wave Table Name - {WaveTableName}")

DatabaseTableName = application.lower() + "-" + environment.lower() + \
                  "-database-extract-table"
print(f"Database Table Name - {DatabaseTableName}")

print("*** Query ***")
query_columns = '"app"."app_name" , ' \
                '"app"."app_id", ' \
                '"app"."wave_id" , '\
                '"wave"."wave_name", '\
                '"wave"."wave_status", ' \
                '"wave"."wave_start_time", ' \
                '"wave"."wave_end_time", ' \
                '"wave"."wave_apps_forecast", ' \
                '"wave"."wave_apps_baseline", ' \
                '"wave"."wave_servers_forecast", ' \
                '"wave"."wave_servers_baseline", ' \
                '"server"."server_name" , '\
                '"server"."instancetype" , '\
                '"server"."migration_status" , ' \
                '"server"."r_type" , ' \
                '"server"."server_id" , '\
                '"server"."server_fqdn" , '\
                '"server"."server_os_family" , '\
                '"server"."server_os_version" , '\
                '"server"."replication_status" , '\
                '"server"."server_environment" '
query_join = (' LEFT JOIN "{}" app ON "server"."app_id" = "app"."app_id"'
              ' LEFT JOIN "{}" wave ON "wave"."wave_id" = "app"."wave_id"')

query_template = 'CREATE OR REPLACE VIEW "{}" AS SELECT ' + query_columns + ' FROM "{}" server' + query_join   # nosec B608
query = query_template.format(ViewName, ServerTableName, AppTableName, WaveTableName)


def lambda_handler(event, context):
    logger.info('Function Starting')
    logger.info(f'Incoming Event:\n{json.dumps(event, indent=2)}')
    logger.info(f'Context Object:\n{vars(context)}')
    aws_account_id = context.invoked_function_arn.split(":")[4]
    athena_result_bucket = "s3://{}-{}-{}-athena-results/".format(
        application, environment, aws_account_id)
    athena_client = cmf_boto.client("athena")
    athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database,
                               'Catalog': 'AwsDataCatalog'},
        ResultConfiguration={
            'OutputLocation': athena_result_bucket,
        },
        WorkGroup=AthenaWorkGroup
    )
