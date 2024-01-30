#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import sys
from awsglue.transforms import ApplyMapping, SelectFields, ResolveChoice
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import boto3

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'bucket_name', 'folder_name', 'environment_name', 'application_name'])
bucket_name = args['bucket_name']
folder_name = args['folder_name']
environment_name = args['environment_name']
application_name = args['application_name']
s3 = boto3.resource('s3')
bucket = s3.Bucket(bucket_name)
for obj in bucket.objects.filter(Prefix=folder_name + '/'):
    s3.Object(bucket.name, obj.key).delete()

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)
newapp = ''
newenv = ''
if "-" in application_name:
    newapp = application_name.lower().replace("-", "_")
else:
    newapp = application_name.lower()
if "-" in environment_name:
    newenv = environment_name.lower().replace("-", "_")
else:
    newenv = environment_name.lower()
input_table_var = newapp + "_" + newenv + "_servers"
db_name_var = application_name + "-" + environment_name + "-tracker"
output_table_var = application_name + "-" + environment_name + "-server-extract-table"

datasource0 = glueContext.create_dynamic_frame.from_catalog(database=db_name_var.lower(),
                                                            table_name=input_table_var.lower(),
                                                            transformation_ctx="datasource0")

applymapping1 = ApplyMapping.apply(frame=datasource0, mappings=[("server_name", "string", "server_name", "string"), (
"server_os_version", "string", "server_os_version", "string"), ("app_name", "string", "app_name", "string"), (
                                                                "server_environment", "string", "server_environment",
                                                                "string"),
                                                                ("instancetype", "string", "instancetype", "string"), (
                                                                "migration_status", "string", "migration_status",
                                                                "string"),
                                                                ("server_id", "string", "server_id", "string"),
                                                                ("server_fqdn", "string", "server_fqdn", "string"), (
                                                                "server_os_family", "string", "server_os_family",
                                                                "string"), (
                                                                "replication_status", "string", "replication_status",
                                                                "string"), ("app_id", "string", "app_id", "string")],
                                   transformation_ctx="applymapping1")

selectfields2 = SelectFields.apply(frame=applymapping1,
                                   paths=["server_name", "app_name", "server_os_version", "instancetype",
                                          "migration_status", "server_id", "server_fqdn", "server_os_family",
                                          "replication_status", "server_environment", "app_id"],
                                   transformation_ctx="selectfields2")

resolvechoice3 = ResolveChoice.apply(frame=selectfields2, choice="MATCH_CATALOG", database=db_name_var.lower(),
                                     table_name=output_table_var.lower(), transformation_ctx="resolvechoice3")

resolvechoice4 = ResolveChoice.apply(frame=resolvechoice3, choice="make_struct", transformation_ctx="resolvechoice4")

datasink5 = glueContext.write_dynamic_frame.from_catalog(frame=resolvechoice4, database=db_name_var.lower(),
                                                         table_name=output_table_var.lower(),
                                                         transformation_ctx="datasink5")
job.commit()
