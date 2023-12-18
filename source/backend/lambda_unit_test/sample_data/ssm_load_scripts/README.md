This folder contains test data for the lambdas
- lambda_ssm_load_scripts
- lambda_ssm_scripts

### lambda_ssm_load_scripts
The tests expect a zip file with scripts.
- sample_ssm_scripts.zip, the zip file containing sample_ssm_script_1.json and sample_ssm_script_2.json
- sample_ssm_script_1.json and sample_ssm_script_2.json are the sample json files included for the convenience of checking the contents without unzipping

### lambda_ssm_scripts
- invalid_zip_file.zip - a single python source file renamed with .zip extension to be used as invalid zip in the tests


- package_valid consists of 
  - hello_world.py
  - mfcommon.py
  - Package-Structure.yml

  The test then creates a zip file containing the above files on the fly

Similarly, the following packages are used in the tests
  - package_invalid_yaml
  - package_no_yaml
  - package_incorrect_yaml_contents
  - package_no_master_file
  - package_valid_with_dependencies
  - package_missing_dependencies
  - package_schema_extensions
  - package_invalid_attributes

