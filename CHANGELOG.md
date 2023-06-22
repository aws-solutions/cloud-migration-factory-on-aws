# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [3.3.0] - 2023-06/22
### Changed
- FEATURE-RETIRED: AMS WIG feature code has now been retired from CMF. Creation of RFC for onboarding instances to AMS is now managed directly via RFCs to the AMS team and not possible through CMF.
- MGN: Added ability to specify tags for test and live launched instances that are appended to the master tags for a server record.
- MGN: Launch templates updates to allow clearing of private IP address and also termination protection, if the server was set and user required to remove them.
- Added private IP address to be set during the validation action as this was not done previously. This caused checking for a valid IP address was not being performed.
- MGN: Automation scripts for MGN pre-requisites checking and agent installation now support private endpoints; agent installation now by default uses temporary credentials to install MGN agents; instead of using the IAM User credentials.
- Migration Tracker: Athena Engine version moved to version 3. This is due to version 2 being deprecated on October 16, 2023 in US-EAST-1 region.
- Automation>Jobs table now by default displays only the last 30 days of logs. This is to reduce the amount of data requested and also speed up the load time. This option can be changed in the table settings to display all logs. In future releases we will update the APIS to support pagination.
- All Lambda function using Python as their runtime have been updated to use version 3.10.
### Added
- Improved unit test coverage for backend and frontend codebase through additional test creation.
- REHOST-MGN added the ability to set the server boot mode from a new CMF attribute server_boot_mode_uefi defined as a checkbox in the server schema; this will be passed to the launch template in EC2 by CMF and allow UEFI servers to be migrated without manually updating MGN.
- New dashboard to display replication status attribute for all servers, this is used with the MGN automation scripts that update the replication status attribute when run.
### Fixed
- SSM Automation jobs were timing out after 1 hour as it was using the default timeout for the AWS-RunPowerShellScript document. Updated step to provide/override executionTimeout for this step to 43200(12 Hours as per other SSM timeout values).
- Frontend: Updated JS module xlsx to 0.19.3 to resolve security issue described here https://github.com/advisories/GHSA-4r6h-8v6p-xvw6. With this release of the xlsx module they have also moved to their own CDN from NPM so added the module source into local repo.
- SSO logins performing Admin functions for some providers were providing a Capitalized header key name. Policy now supports both lowercase and capitalized checking for authorization-access token header.
- Added validation of script arguments within uploaded script packages to ensure they are formatted correctly before upload. This was causing errors in the script run as they were not validated before use. UI update allows user to see errors found in the flash bar.
- SCRIPTS-FIX: Updated MGN agent installation download to force using TLS1.2 for download as it was failing for some customers where they do not allow anything below tls 1.2 to be used.
- Updated python modules requests, boto3, botocore and coverage to latest versions.
- Resolve bug in Migration Tracker that was causing the Athena tables to be missing on deployment. This issue was introduced in version 3.2.1.
- Import errors created after committing to the API were not being displayed in a readable format in the UI, this has now been resolved.
- When importing boolean/checkbox values from a CSV it was incorrectly assigning the key a string value instead of boolean. Corrected import script to parse string boolean of true, 1 or on to boolean.
## [3.2.2] - 2023-04-20
### Fixed
- Resolved issue caused by S3 changes to new bucket permissions described in the following release notes https://aws.amazon.com/about-aws/whats-new/2022/12/amazon-s3-automatically-enable-block-public-access-disable-access-control-lists-buckets-april-2023/. This change is now being rolled out across all regions and causes a failure in the stack deployment if this new setting is not applied.
- Updated AWS Amplify to the latest in order to resolve dependency and upgrade @sideway/formula module to 3.0.1 to protect against vulnerability described here https://nvd.nist.gov/vuln/detail/CVE-2023-25166.
- Simplejson python library updated from 3.18.0 to 3.19.1 (Used by in all CMF Lambda functions).
- Troposphere python library updated from 4.2.0 to 4.3.2 (Used by EC2 Platform functions).
- Coverage python library updated from 7.0.0 to 7.2.2 (Used only for unit testing).
- Application Registry - Update to logicalId for the Attribute group to fix CFN error "AttributeGroup name update feature has been deprecated. (Service: ServiceCatalogAppRegistry, Status Code: 400)". This error would occur when a stack update is performed and caused by changes to the AppRegistry service.
- MGN Rehost - IMDSv2 settings on EC2 launch profile were incorrectly setting the values to enabled and disabled, the only options now are optional and required.
- EC2 Replatform - resolved issue where Build template incorrectly including all servers with the Replatform r_type without verifying that the application was within the wave selected.
- Fixed issue when deploying CMF stack with the optional private deployment, and specifying multiple subnet IDs to the PrivateEndpointSubnets parameter. When multiple subnets were provided the VPC endpoint would fail to create as the list was provided as a string and not a list as expected.
## [3.2.1] - 2023-01-12
### Fixed
- Updated python requests to 2.28.1 due to security patch required for certifi module which is a dependency. Using the latest requests version 2.28.1 installs the latest patched version of certifi v2022.12.07. For details please refer to https://nvd.nist.gov/vuln/detail/cve-2022-23491.
## [3.2.0] - 2022-12-22
### Added
- Security: Allowed customers to use corporate credentials/SSO to login to the CMF web interface; this ability enables federated sign in using any SAML identity provider that can be integrated with Cognito.
- Administration: Management(add/remove) of Cognito groups and group membership is now provided in the CMF web interface; CMF administrators no longer need access to the Cognito console to manage CMF access.
- Deployment: On deployment of the stack it now automatically registers the Cloud Migration Factory as an application in AppRegistry to allow customers to track costs and resource usage.
### Changed
- Schema: Updated existing default schema attributes for Rehost and Replatform to include UI grouping to align with other attributes.
- General: Updated all external libraries used frontend JS and backend Python to the latest versions.
- Credentials Manager: Removed code that allowed any secret to be returned from Secrets Manager that was not functional and not used.
### Fixed
- Deployment-WAF: When WAF is enabled automation scripts could not log in to the /prod/login due to the Lambda function not being granted access to the Cognito due to WAF rules. Updated mfcommon.py Factorylogin function so it no longer uses the login API and Lambda function to get an access token from Lambda and calls directly to Cognito using the boto3 library; this resolves the issue as the automation server has to be in the WAF rules and the Lambda no longer needs access to Cognito. We will keep the login Lambda for this release but may review in future releases. IMPORTANT: Any customized scripts will need to have the mfcommon.py module updated to work with this updated version if using WAF.
- Rehost MGN: Resolved issue causing the use of private IP address to be ignored when used with MGN Rehost migrations actions.
- Security: Resolved issues with forgotten password reset screens. Moved all reset functions to the same screen, user can now request the reset code and also use it on the same screen, previously this function was hidden in the forgotten password link click.
## [3.1.0] - 2022-10-20
### Added
- Added options for deployment type into Cloud Formation Template with the option of Default (Public), Public with WAF and Private, These options allow deployment into environments with strict requirements on accessibility on the service endpoints. With Private the solution is only accessible from within the VPC, using API Gateway Private endpoints. Public with WAF automatically deploys WAF in front of CloudFront, API Gateway and Cognito, and restricts access to the CIDR ranges specified in the Stack parameter.
### Changed
- Added ability to control access to manage automation scripts via policies. Previous to this change any user with access to CMF could add and edit scripts. The policies implemented only use the create flag for the script entity type in the policy all other permissions and attribute level are not implemented.
### Fixed
- Credentials Manager: When a dollar $ character was present in the password for any Wind ows Powershell command it caused the logon to fail as Powershell was seeing this as a variable declaration as the strings were double-quoted (expandable) and should have been single-quoted (verbatim or wysiwyg). Changed all occurrences to single quotes.
- Credentials Manager: When an ssh private key is used to authenticate to a Linux OS the script aborts with an exception as the key string was being passed to the method from_private_key_file function and this only accepts a file path, not File Object, changed the method to from_private_key as this accepts a File like object.
- API: Permissions mapping in the UI failed when user is not in Cognito admin group, as only admin members could retrieve group lists from API. This update adds a new authorizer to the Login API that provides authorization of the user if they have a valid token in the CMF user pool (used currently in Admin API too), this authorizer has been configured for the /login/groups resource only, allowing any authenticated user to access this resource.
- Schema/Attribute Validation: When importing data through the UI list field values were case-sensitive in the backend but not in frontend validation; this caused the API to return validation errors after the data had been validated by the frontend code. Updated BE API Lambda layer for validation of list values to be case-insensitive to match FE validation.
- Replatform to EC2: Various fixes and clarifications in help text.
- Automation: Resolved issue with log output not being processed where the word Content was present in the output text.
- Automation: Updated log output processing to detect save conflicts when multiple updates are mad to the same log record.
### Removed
- Rehost AMS integration removed as CloudEndure Migration is no longer available to new workloads.
## [3.0.0] - 2022-06-30
### Added
- FEATURE: New user interface - UI has been completely redesigned to provide a better user experience. UI is now based on the awsui-components library see: https://github.com/aws/awsui-documentation for more information.
- FEATURE: Remote Automation - Ability to run and monitor automation jobs remote from with the CMF UI. Along with this CMF can now secure store credentials for use in Automation jobs, through integration with AWS Secrets Manager. An integrated automation scripts library that can be used by engineers to upload new scripts for running via this new feature and also manage and update existing scripts.
- FEATURE: Role based access - Role based access policies can now be created and applied to users with CMF. This allows granular levels of access to be applied to different users.
- FEATURE: Import and Export data - the new Ui provides a more advanced import process allowing users to perform updates of existing records via the import process, the import process provides a differences/comparison on import to ensure that the user knows the exact impact of uploading a file on the existing data. Along with uploads, users can now download Excel spreadsheets of the data held.
- FEATURE: Migration Dashboard - On open the CMF home page users will now be presented with a dashboard containing the status of the migration and inventory held in the Cloud Migration Factory.
- FEATURE: MFA Support - Logins to the CMF solution can now be protected with Multi-Factor Authentication, this is enabled through Amazon Cognito per user.
- FEATURE: Replatform EC2 - Allows the definition of new EC2 instances that will be automatically deployed by CMF through automatically generated CloudFormation templates. This allows migration waves to have a mixture of Rehost and Replatform servers if required.
- FEATURE: Database entity - New database record types have been introduced, allowing a richer portfolio of application metadata to be stored in CMF. This data can be used in automation scripts to incorporate database migration aspects into the work that CMF performs.
- UPDATE: Removed the requirement to have outbound internet access to deploy the solution. All components are now prebuilt and provided via the build S3 buckets to the end user.
## [2.0.2] - 2021-10-05
### Fixed
- Fixed a frontend UI bug

## [2.0.1] - 2021-9-20
### Fixed
- Fixed a bug that will affect private_ip and iamRole attributes if these two attributes are used

## [2.0.0] - 2021-08-30
### Added
- new integration to support Application Migration Service (MGN) migration

## [1.1.1] - 2021-05-10
### Fixed
- upgraded two Lambda functions from Python 2.7 to Python 3.7

## [1.1.0] - 2021-02-15
### Added
- New Migration Tracker Dashboard component
- Support for Wave schema extension

### Fixed
- bug fixed CloudEndure Lambda, improved blueprint update process
- bug fixed in servers and apps Lambda, improved performance of data query

## [1.0.0] - 2020-06
### Added
Solution first release

## [0.0.1] - 2019-04-15
### Added
- CHANGELOG templated file
- README templated file
- NOTICE file
- LICENSE file
