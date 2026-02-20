#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os

import cmf_boto
from cmf_logger import logger

application = os.environ["application"]
environment = os.environ["environment"]
database = os.environ["database"]
athena_workgroup = os.environ["workgroup"]
print("*** View Name ***")
newapp = ""
newenv = ""
if "-" in application:
    newapp = application.lower().replace("-", "_")
else:
    newapp = application.lower()
if "-" in environment:
    newenv = environment.lower().replace("-", "_")
else:
    newenv = environment.lower()
view_name = newapp + "_" + newenv + "_" + "tracker_general_view"
print(f"General view name: {view_name}")

app_table_name = application.lower() + "-" + environment.lower() + "-app-extract-table"
print(f"App table name - {app_table_name}")

server_Table_name = application.lower() + "-" + environment.lower() + "-server-extract-table"
print(f"Server table name - {server_Table_name}")

wave_table_name = application.lower() + "-" + environment.lower() + "-wave-extract-table"
print(f"Wave table name - {wave_table_name}")

# Not used at the moment
database_table_name = application.lower() + "-" + environment.lower() + "-database-extract-table"
print(f"Database table name - {database_table_name}")

print("*** Query ***")
query_columns = (
    "server.server_name, "
    "server.instancetype, "
    "server.migration_status, "
    "server.r_type, "
    "server.server_id, "
    "server.wave_id, "
    "server.server_fqdn, "
    "server.server_os_family, "
    "server.server_os_version, "
    "server.replication_status, "
    "server.server_environment, "
    "server.app_ids AS app_ids_array, "
    "(SELECT array_agg(app.app_name ORDER BY app.app_id) FROM \"{}\" app "
    " WHERE contains(server.app_ids, app.app_id)) AS app_names_array, "
    "array_join(server.app_ids, ',') AS app_ids, "
    "(SELECT array_join(array_agg(app.app_name ORDER BY app.app_id), ',') FROM \"{}\" app "
    " WHERE contains(server.app_ids, app.app_id)) AS app_names, "
    "wave.wave_name, "
    "wave.wave_status, "
    "wave.wave_start_time, "
    "wave.wave_end_time, "
    "wave.wave_apps_forecast, "
    "wave.wave_apps_baseline, "
    "wave.wave_servers_forecast, "
    "wave.wave_servers_baseline "
)
query_join = " LEFT JOIN \"{}\" wave ON wave.wave_id = server.wave_id"

query_template = "CREATE OR REPLACE VIEW \"{}\" AS SELECT " + query_columns + " FROM \"{}\" server" + query_join  # nosec B608
query = query_template.format(view_name, app_table_name, app_table_name, server_Table_name, wave_table_name)


def lambda_handler(event, context):
    logger.info("Function Starting")
    logger.info(f"Incoming Event:\n{json.dumps(event, indent=2)}")
    logger.info(f"Context Object:\n{vars(context)}")
    aws_account_id = context.invoked_function_arn.split(":")[4]
    athena_result_bucket = "s3://{}-{}-{}-athena-results/".format(application, environment, aws_account_id)
    athena_client = cmf_boto.client("athena")
    athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database, "Catalog": "AwsDataCatalog"},
        ResultConfiguration={
            "OutputLocation": athena_result_bucket,
        },
        WorkGroup=athena_workgroup,
    )
