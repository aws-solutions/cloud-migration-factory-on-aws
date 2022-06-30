# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
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
