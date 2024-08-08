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
input_table_var = newapp + "_" + newenv + "_waves"
db_name_var = application_name + "-" + environment_name + "-tracker"
output_table_var = application_name + "-" + environment_name + "-wave-extract-table"

datasource0 = glueContext.create_dynamic_frame.from_catalog(database=db_name_var.lower(),
                                                            table_name=input_table_var.lower(),
                                                            transformation_ctx="datasource0")

applymapping1 = ApplyMapping.apply(frame=datasource0, mappings=[("wave_id", "string", "wave_id", "string"),
                                                                ("wave_name", "string", "wave_name", "string"),
                                                                ("wave_status", "string", "wave_status", "string"),
                                                                ("wave_start_time", "string", "wave_start_time", "string"),
                                                                ("wave_end_time", "string", "wave_end_time", "string"),
                                                                ("wave_apps_baseline", "string", "wave_apps_baseline", "integer"),
                                                                ("wave_apps_forecast", "string", "wave_apps_forecast", "integer"),
                                                                ("wave_servers_baseline", "string", "wave_servers_baseline", "integer"),
                                                                ("wave_servers_forecast", "string", "wave_servers_forecast", "integer")],
                                   transformation_ctx="applymapping1")

selectfields2 = SelectFields.apply(frame=applymapping1, paths=["wave_name", "wave_id", "wave_status", "wave_start_time", "wave_end_time", "wave_apps_baseline", "wave_apps_forecast", "wave_servers_baseline", "wave_servers_forecast"],
                                   transformation_ctx="selectfields2")

resolvechoice3 = ResolveChoice.apply(frame=selectfields2, choice="MATCH_CATALOG", database=db_name_var.lower(),
                                     table_name=output_table_var.lower(), transformation_ctx="resolvechoice3")

resolvechoice4 = ResolveChoice.apply(frame=resolvechoice3, choice="make_struct", transformation_ctx="resolvechoice4")

datasink5 = glueContext.write_dynamic_frame.from_catalog(frame=resolvechoice4, database=db_name_var.lower(),
                                                         table_name=output_table_var.lower(),
                                                         transformation_ctx="datasink5")
job.commit()
