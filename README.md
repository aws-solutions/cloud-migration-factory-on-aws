# AWS cloudendure migration factory solution
AWS CloudEndure Migration Factory Solution is an AWS Solutions Implementation that helps migrate a large number of servers with CloudEndure Migration in a simplified and expedited way at scale. The solution automates many of the manual, time-consuming tasks that enterprises commonly face in migrating servers from on-premise to the cloud; for example, checking prerequisites on the source machine, installing/uninstalling software on the source and target machine. Thousands of servers have been migrated to AWS using this solution. When customers deploy the solution, its AWS CloudFormation template automatically provisions and configures the necessary AWS services, starting with Amazon Elastic Container Service to build a web interface and an Amazon S3 bucket to contain the frontend code.

The solution also deploys Amazon CloudFront, Amazon API Gateway, AWS Lambda, Amazon Cognito, and Amazon DynamoDB. To learn more about AWS CloudEndure Migration Factory Solution, see the AWS Solutions Implementation webpage.

For more information about the implementation guide, please visit the AWS Prescriptive Guidance:
https://docs.aws.amazon.com/solutions/latest/aws-cloudendure-migration-factory-solution/welcome.html

For more information about the best practices using this solution, please visit the AWS Prescriptive Guidance:
https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-factory-cloudendure

## Solution Deployment

For detailed instructions on deploying this solution from the existing AWS Built solution, please refer to the implementation guide.

## Building from source code

### Environment Prerequisites

  - os running Linux or Mac OS.
  - pip installed and configured.
  - Python 3.9 installed.

### Build instructions.

1. Ensure you have created an S3 bucket where your built solution will be deployed from. You will need a bucket created in each region where you will deploy the solution (REMEMBER: AWS Lmabda functions only support deployment of code from an S3 bucket in the same region). The bucket name has to be in the format [mys3bucketname]-[region] (i.e. cemfcustombuild-us-west-2)
2. Clone this repository
    IMPORTANT NOTE: Ensure that there are no directories with spaces existing in the full path to the repository directory, and the repository directory does not include spaces. If this is the case the build script may delete items and create outputs in incorrect locations.)
3. Change directory to ./deployment
3. Run ./build-s3-dist.sh [new s3 bucket name (i.e. mys3bucketname) without region suffix] [name of solution(i.e. cemf)] [version (i.e. v1.0.0)]
4. create a folder in the new S3 bucket with the same name as the solution provided in the build script and then a folder inside this with the version number
5. Once the build script has completed copy the contents of the ./deployment/global-s3-assests and ./deployment/regional-s3-assets directories to the new S3 bucket under the version number folder
6. Make all the objects under the version folder public to allow them to be accessed during the CloudFormation deployment.
7. Follow the implementation guide provided above substituting the Template urls and other references to deployment S3 buckets with the bucket and folder structure you provided to the build script.

## File Structure

```
|-deployment/
  |-aws-cloudendure-migration-factory-solution.template                          [ CloudFormation template to deploy the base solution ]
  |-aws-cloudendure-migration-factory-solution-mgn                               [ Nested CloudFormation template to deploy MGN Lambda ]
  |-aws-cloudendure-migration-factory-solution-mgn-target-account.template       [ CloudFormation template to deploy target account IAM roles ]
  |-aws-cloudendure-migration-factory-solution-tracker.template                  [ Nested CloudFormation template to deploy migration tracker ]
  |-build-s3-dist.sh                                                               [ Main solution build script to create deployable version using 
|-source/
  |-Tools Integration/
    |-CE-Integration/                                                [ folder containing CloudEndure Integration Lambda code ]
    |-MGN-Integration/                                               [ folder containing MGN Integration Lambda code ]
    |-migration-tracker/                                             [ folder containing migration tracker Glue Scripts ]
  |-frontend/                                                        [ folder containing frontend code ]
  |-backend/
    |-helper/                                                          [ A helper function to help deploy lambda function code through S3 buckets ]
      |-helper.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_ams_wig/                                                  [ lambda function to manage AWS Managed services intergration]
      |-lambda_ams_wig.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_app_item/                                                 [ lambda function to manage Migration Factory apps ]
      |-lambda_app_item.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_apps/                                                     [ lambda function to manage Migration Factory apps ]
      |-lambda_apps.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_auth/                                                     [ lambda function to manage Migration Factory authentication ]
      |-lambda_auth.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_build/                                                    [ lambda function to build frontend code ]
      |-lambda_build.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_cognitogroups/                                            [ lambda function to manage Migration Factory groups ]
      |-lambda_cognitogroups.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_defaultschema/                                            [ lambda function to manage Migration Factory default schema ]
      |-schema/
        |-factory.py
        |-roles.py
        |-stages.py
      |-lambda_defaultschema.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_login/                                                    [ lambda function to manage Migration Factory login ]
      |-lambda_login.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_migrationtracker_glue_execute/                            [ lambda function to run migration tracker glue job ]
      |-lambda_migrationtracker_glue_execute.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_migrationtracker_glue_scriptcopy/                         [ lambda function to copy Glue scripts to local bucket ]
      |-lambda_migrationtracker_glue_scriptcopy.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_reset/                                                    [ lambda function to manage Migration Factory password reset ]
      |-lambda_reset.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_role/                                                     [ lambda function to manage Migration Factory roles ]
      |-lambda_role.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_role_item/                                                [ lambda function to manage Migration Factory roles ]
      |-lambda_role_item.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_run_athena_savedquery/                                    [ lambda function to run migration tracker Athena query ]
      |-lambda_run_athena_savedquery.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_schema_app/                                               [ lambda function to manage Migration Factory app schema ]
      |-lambda_schema_app.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_schema_server/                                            [ lambda function to manage Migration Factory server schema ]
      |-lambda_schema_server.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_schema_wave/                                              [ lambda function to manage Migration Factory wave schema ]
      |-lambda_schema_wave.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_server_item/                                              [ lambda function to manage Migration Factory servers ]
      |-lambda_server_item.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_service_account/                                          [ lambda function to create a factory service account ]
      |-lambda_service_account.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-policy/                                                          [ Migration Factory authorization policy ]
      |-policy.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_stage/                                                    [ lambda function to manage Migration Factory stage ]
      |-lambda_stage.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_stage_attr/                                               [ lambda function to manage Migration Factory stage ]
      |-lambda_stage_attr.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_wave_item/                                                [ lambda function to manage Migration Factory waves ]
      |-lambda_wave_item.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-lambda_waves/                                                    [ lambda function to manage Migration Factory waves ]
      |-lambda_waves.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]
    |-policy/                                                          [ Migration Factory authorization policy ]
      |-policy.py
      |-requirements.txt                                               [ pip install requirements file for lambda function dependencies ]

```

This solution collects anonymous operational metrics to help AWS improve the quality of features of the solution. For more information, including how to disable this capability, please see the [implementation guide](https://docs.aws.amazon.com/solutions/latest/aws-cloudendure-migration-factory-solution/appendix-b.html).


***

Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the the MIT-0 License. See the LICENSE file.
This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.