# Cloud Migration Factory on AWS
Cloud Migration Factory on AWS is an AWS Solutions Implementation that helps migrate a large number of servers with CloudEndure Migration in a simplified and expedited way at scale. The solution automates many of the manual, time-consuming tasks that enterprises commonly face in migrating servers from on-premise to the cloud; for example, checking prerequisites on the source machine, installing/uninstalling software on the source and target machine. Thousands of servers have been migrated to AWS using this solution. When customers deploy the solution, its AWS CloudFormation template automatically provisions and configures the necessary AWS services.

The solution also deploys Amazon CloudFront, Amazon API Gateway, AWS Lambda, Amazon Cognito, Amazon S3, and Amazon DynamoDB. To learn more about AWS Cloud Migration Factory Solution, see the AWS Solutions Implementation webpage.

For more information about the implementation guide, please visit the AWS Prescriptive Guidance:
https://docs.aws.amazon.com/solutions/latest/aws-cloudendure-migration-factory-solution/welcome.html

For more information about the best practices using this solution, please visit the AWS Prescriptive Guidance:
https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-factory-cloudendure
***
## File Structure

```
|-deployment/
    |-aws-cloud-migration-factory-solution.template                          [ CloudFormation template to deploy the base solution ]
    |-aws-cloud-migration-factory-solution-automation.template               [ Nested CloudFormation template to deploy the remote automation feature ]
    |-aws-cloud-migration-factory-solution-credentialmanager.template        [ Nested CloudFormation template to deploy the credential manager feature ]
    |-aws-cloud-migration-factory-solution-mgn.template                      [ Nested CloudFormation template to deploy MGN Lambda ]
    |-aws-cloud-migration-factory-solution-replatform.template               [ Nested CloudFormation template to deploy replatform feature ]
    |-aws-cloud-migration-factory-solution-tracker.template                  [ Nested CloudFormation template to deploy migration tracker ]
    |-aws-cloud-migration-factory-solution-waf-be.template                   [ Nested CloudFormation template to deploy the optional WAF in front of API Gateway and Cognito ]
    |-aws-cloud-migration-factory-solution-waf-fe.template                   [ Nested CloudFormation template to deploy the optional WAF in front of CloudFront ]
    |-aws-cloud-migration-factory-solution-target-account.template           [ CloudFormation template to deploy target account IAM roles ]
    
|-source/
    |-backend/                     [ folder containing backend code ]
      |-lambda_functions           [ folder containing all lambda function, each sub folder is a lambda function ]
      |-lambda_layers              [ folder containing all lambda layers, each sub folder is a lambda layer used in one or more lambda functions as defined in the CloudFormation templates ]
      |-lambda_unittests           [ folder containing lambda function unit tests ]
    |-frontend/                    [ folder containing frontend code ]
    |-integrations/                [ folder containing tool integration code ]    

```
***

## Customization

The steps given below can be followed if you are looking to customize or extend the solution.

### Build

To build your customized distributable follow given steps.

- Create two S3 buckets (you can use the CLI commands below).
- First bucket with the format '<BUCKET-NAME>-reference' to deploy the templates into.
- Second bucket with the format '<BUCKET-NAME>-<AWS_REGION>' to deploy the assets into. The solution's CloudFormation
  template will expect the source code to be located in this bucket. <AWS_REGION> is where you are testing the
  customized solution.

```
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account --profile <PROFILE_NAME>)
REGION=$(aws configure get region --profile <PROFILE_NAME>)
BASE_BUCKET_NAME=cmf-deployment-$ACCOUNT_ID
TEMPLATE_BUCKET_NAME=$BASE_BUCKET_NAME-reference
ASSET_BUCKET_NAME=$BASE_BUCKET_NAME-$REGION
aws s3 mb s3://$TEMPLATE_BUCKET_NAME/
aws s3 mb s3://$ASSET_BUCKET_NAME/

# Default encryption:
aws s3api put-bucket-encryption \
  --bucket $TEMPLATE_BUCKET_NAME \
  --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

aws s3api put-bucket-encryption \
  --bucket $ASSET_BUCKET_NAME \
  --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

# Enable public access block:
aws s3api put-public-access-block \
  --bucket $TEMPLATE_BUCKET_NAME \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws s3api put-public-access-block \
  --bucket $ASSET_BUCKET_NAME \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

```

_Note: For PROFILE_NAME, substitute the name of an AWS CLI profile that contains appropriate credentials for deploying
in your preferred region. Remove `--profile <PROFILE_NAME>` from the command if you have configured the AWS CLI manually
instead of using a profile._

- Configure the solution name and version number on your terminal:

```
SOLUTION_NAME=cloud-migration-factory-on-aws
VERSION=custom001
```

- Build the distributable using build-s3-dist.sh

```
cd ./deployment
chmod +x ./build-s3-dist.sh
./build-s3-dist.sh $BASE_BUCKET_NAME $SOLUTION_NAME $VERSION
```

_✅ All assets are now built. You should see templates under deployment/global-s3-assets and other artifacts (frontend
and lambda binaries) under deployment/regional-s3-assets_

### Deployment

Deploy the distributable to an Amazon S3 bucket in your account:

```
cd ./deployment
aws s3 ls s3://$ASSET_BUCKET_NAME  # should not give an error (verifies the bucket exists)
aws s3 cp global-s3-assets/  s3://$TEMPLATE_BUCKET_NAME/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control --expected-bucket-owner $ACCOUNT_ID --profile <PROFILE_NAME>
aws s3 cp regional-s3-assets/  s3://$ASSET_BUCKET_NAME/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control --expected-bucket-owner $ACCOUNT_ID --profile <PROFILE_NAME>
```

_✅ All assets are now staged in your S3 bucket. You or any user may use S3 links for deployments_

### Frontend development

In order to run the frontend app locally for development, you need to deploy the solution to your AWS account first
and then configure the local frontend to use the deployed backend in the cloud.
To do so,

- In the S3 console, locate the S3 bucket with the name `migration-factory-test-<ACOUNT_ID>-front-end`
- Download the file `env_dev.js` from that bucket and place it under /frontend/public next to the existing `env.js` file
- Run `npm run start`. The app will become available under `http://localhost:3000` and read the settings
  from `env_dev.js`
- Use a browser extension to bypass CORS errors on localhost
- To log in, create a Cognito user in the AWS Cognito Console as described in the Implementation Guide

***

## Unit Testing Framework
The following unit testing frameworks are used in the solution.
### Javascript/frontend
Libraries jest with babel are used for all unit tests involving the front end code.
The configuration of jest and babel is maintained in the following solution files:
```
|-source/
    |-frontend/
        - babel.config.js           [ babel transformation configuration ]
        - jest.config.js            [ jest transformation configuration ]
```

All unit test scripts should be created in the same folder as the script or module that they are testing against. When naming the unit test script the format should be as follows:

[_original script name_].test.js  -  example for the script **Audit.js** the test script filename should be **Audit.test.js**

#### Coverage reporting
By default, the jest configuration will produce a coverage report when run and which will be processed using the **jest-sonar-reporter** Results Processor in order to output a generic report format that can be ingested into SonarQube.  A readable version is also output to source/frontend/test-report.xml.

#### Running the unit tests

Before running frontend unit tests, jest needs to be installed using the following command, this will install jest and enable it to be run globally from the command line:
```
npm install jest -global
```

To run the unit test, ensure the working directory is set to **/source/frontend** and run the command:
```
jest ./
```
### Python/backend
python unittest is used alongside the moto library to run unit tests against the Lambda function code within the solution.  All python unit tests for Lambda functions can be found in the following folder.
```
|-source/
    |-backend/
        |-lambda_unit_test
```
#### Run Lambda Unit Tests
To run the unit test, ensure the working directory is set to the parent directory of the repository
```
chmod +x ./deployment/run_lambda_unit_test.sh
./deployment/run_lambda_unit_test.sh

```
Confirm that all the unit test pass.
#### Coverage reporting
Coverage reports should be output to the same directory as the unit test scripts are stored in order to be picked up by the SonarQube configuration included with the solution.
## SonarQube - Code Quality
The solution is configured with a default SonarQube properties file that can be used to initialize the solution into an existing SonarQube environment along with configurations to allow coverage reports to be provided during scanning of the solution. This file is located:
```
|-/
    - sonar-project.properties           [ SonarQube project properties file ]
```
***

## License

See license [here](./LICENSE.txt)

***

## Collection of Anonymized Operational Metrics

This solution collects anonymized operational metrics to help AWS improve the quality of features of the solution. For
more information, including how to disable
this capability, please see
the [implementation guide](https://docs.aws.amazon.com/solutions/latest/cloud-migration-factory-on-aws/anonymized-data-collection.html).
***
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the the MIT-0 License. See the LICENSE file.
This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
