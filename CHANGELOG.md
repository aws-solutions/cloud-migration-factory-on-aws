# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [3.1.0] - 2022-10-20
### Added
- Added options for deployment type into Cloud Formation Template with the option of Default (Public), Public with WAF and Private, These options allow deployment into environments with strict requirements on accessibility on the service endpoints. With Private the solution is only accessible from within the VPC, using API Gateway Private endpoints. Public with WAF automatically deploys WAF in front of CloudFront, API Gateway and Cognito, and restricts access to the CIDR ranges specified in the Stack parameter.
### Changed
- Added ability to control access to manage automation scripts via policies. Previous to this change any user with access to CMF could add and edit scripts. The policies implemented only use the create flag for the script entity type in the policy all other permissions and attribute level are not implemented.
### Fixed   
- Credentials Manager: When a dollar $ character was present in the password for any Windows Powershell command it caused the logon to fail as Powershell was seeing this as a variable declaration as the strings were double-quoted (expandable) and should have been single-quoted (verbatim or wysiwyg). Changed all occurrences to single quotes.
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
