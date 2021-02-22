# AWS cloudendure migration factory solution
AWS CloudEndure Migration Factory Solution is an AWS Solutions Implementation that helps migrate a large number of servers with CloudEndure Migration in a simplified and expedited way at scale. The solution automates many of the manual, time-consuming tasks that enterprises commonly face in migrating servers from on-premise to the cloud; for example, checking prerequisites on the source machine, installing/uninstalling software on the source and target machine. Thousands of servers have been migrated to AWS using this solution. When customers deploy the solution, its AWS CloudFormation template automatically provisions and configures the necessary AWS services, starting with Amazon Elastic Container Service to build a web interface and an Amazon S3 bucket to contain the frontend code.

The solution also deploys Amazon CloudFront, Amazon API Gateway, AWS Lambda, Amazon Cognito, and Amazon DynamoDB. To learn more about AWS CloudEndure Migration Factory Solution, see the AWS Solutions Implementation webpage. 

For more information about the implementation guide, please visit the AWS Prescriptive Guidance:
https://docs.aws.amazon.com/solutions/latest/aws-cloudendure-migration-factory-solution/welcome.html 

For more information about the best practices using this solution, please visit the AWS Prescriptive Guidance:
https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-factory-cloudendure

## File Structure

```
|-deployment/
  |-aws-cloudendure-migration-factory-solution.template            [ CloudFormation template to deploy the base solution ]
  |-aws-cloudendure-migration-factory-solution-tracker.template    [ Nested CloudFormation template to deploy migration tracker ]
|-source/
  |-CE-Integration/                                                [ folder containing CloudEndure Integration Lambda code ]
  |-frontend/                                                      [ folder containing frontend code ]
  |-migration-tracker/                                             [ folder containing migration tracker Glue Scripts ]
  |-helper.py                                                      [ A helper function to help deploy lambda function code through S3 buckets ]
  |-lambda_ams_wig.py                                              [ lambda function to manage AWS Managed services intergration]
  |-lambda_app_item.py                                             [ lambda function to manage Migration Factory apps ]
  |-lambda_apps.py                                                 [ lambda function to manage Migration Factory apps ]
  |-lambda_auth.py                                                 [ lambda function to manage Migration Factory authentication ]
  |-lambda_build.py                                                [ lambda function to build frontend code ]
  |-lambda_cognitogroups.py                                        [ lambda function to manage Migration Factory groups ]
  |-lambda_defaultschema.py                                        [ lambda function to manage Migration Factory default schema ]
  |-lambda_login.py                                                [ lambda function to manage Migration Factory login ]
  |-lambda_migrationtracker_glue_execute.py                        [ lambda function to run migration tracker glue job ]
  |-lambda_migrationtracker_glue_scriptcopy.py                     [ lambda function to copy Glue scripts to local bucket ]
  |-lambda_reset.py                                                [ lambda function to manage Migration Factory password reset ]
  |-lambda_role.py                                                 [ lambda function to manage Migration Factory roles ]
  |-lambda_role_item.py                                            [ lambda function to manage Migration Factory roles ]
  |-lambda_run_athena_savedquery.py                                [ lambda function to run migration tracker Athena query ]
  |-lambda_schema_app.py                                           [ lambda function to manage Migration Factory app schema ]
  |-lambda_schema_server.py                                        [ lambda function to manage Migration Factory server schema ]
  |-lambda_schema_wave.py                                          [ lambda function to manage Migration Factory wave schema ]
  |-lambda_server_item.py                                          [ lambda function to manage Migration Factory servers ]
  |-lambda_servers.py                                              [ lambda function to manage Migration Factory servers ]
  |-lambda_stage.py                                                [ lambda function to manage Migration Factory stage ]
  |-lambda_stage_attr.py                                           [ lambda function to manage Migration Factory stage ]
  |-lambda_wave_item.py                                            [ lambda function to manage Migration Factory waves ]
  |-lambda_waves.py                                                [ lambda function to manage Migration Factory waves ]
  |-policy.py                                                      [ Migration Factory authorization policy ]

```


***


Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the the MIT-0 License. See the LICENSE file.
This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
