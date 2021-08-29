#!/bin/bash
#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name solution-name version-code
#
# Paramenters:
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda
#    code from. The template will append '-[region_name]' to this bucket name.
#    For example: ./build-s3-dist.sh solutions my-solution v1.0.0
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
#
#  - solution-name: name of the solution for consistency
#
#  - version-code: version of the package

# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"
    exit 1
fi

# Get reference for all important folders
template_dir="$PWD"
template_dist_dir="$template_dir/global-s3-assets"
build_dist_dir="$template_dir/regional-s3-assets"
source_dir="$template_dir/../source"

echo "------------------------------------------------------------------------------"
echo "[Init] Clean old dist, node_modules and bower_components folders"
echo "------------------------------------------------------------------------------"
echo "rm -rf $template_dist_dir"
rm -rf $template_dist_dir
echo "mkdir -p $template_dist_dir"
mkdir -p $template_dist_dir
echo "rm -rf $build_dist_dir"
rm -rf $build_dist_dir
echo "mkdir -p $build_dist_dir"
mkdir -p $build_dist_dir

echo "------------------------------------------------------------------------------"
echo "[Packing] Templates"
echo "------------------------------------------------------------------------------"
echo "cp $template_dir/*.template $template_dist_dir/"
cp $template_dir/CFN-templates/*.template $template_dist_dir/
echo "copy yaml templates and rename"
cp $template_dir/CFN-templates/*.yaml $template_dist_dir/
cd $template_dist_dir
# Rename all *.yaml to *.template
for f in *.yaml; do
    mv -- "$f" "${f%.yaml}.template"
done

cd ..
echo "Updating code source bucket in template with $1"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template
replace="s/%%SOLUTION_NAME%%/$2/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template
replace="s/%%VERSION%%/$3/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template
replace="s/%%SOLUTION_ID%%/SO0097/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template

echo "------------------------------------------------------------------------------"
echo "[Packing] Lambda functions"
echo "------------------------------------------------------------------------------"
cd $source_dir/backend/helper
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/helper.zip .

cd $source_dir/backend/lambda_ams_wig
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_ams_wig.zip .

cd $source_dir/backend/lambda_apps
pip install -r ./requirements.txt -t .
cp $source_dir/backend/policy/policy.py ./
zip -r $build_dist_dir/lambda_apps.zip .

cd $source_dir/backend/lambda_auth
pip install -r ./requirements.txt -t .
cp $source_dir/backend/policy/policy.py ./
zip -r $build_dist_dir/lambda_auth.zip .

cd $source_dir/backend/lambda_build
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_build.zip .

cd $source_dir/backend/lambda_cognitogroups
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_cognitogroups.zip .

cd $source_dir/backend/lambda_defaultschema
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_defaultschema_packaged.zip .

cd $source_dir/backend/lambda_login
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_login.zip .

cd $source_dir/backend/lambda_migrationtracker_glue_execute
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_migrationtracker_glue_execute.zip .

cd $source_dir/backend/lambda_migrationtracker_glue_scriptcopy
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_migrationtracker_glue_scriptcopy.zip .

cd $source_dir/backend/lambda_reset
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_reset.zip .

cd $source_dir/backend/lambda_role
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_role.zip .

cd $source_dir/backend/lambda_role_item
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_role_item.zip .

cd $source_dir/backend/lambda_run_athena_savedquery
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_run_athena_savedquery.zip .

cd $source_dir/backend/lambda_schema_app
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_schema_app.zip .

cd $source_dir/backend/lambda_schema_server
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_schema_server.zip .

cd $source_dir/backend/lambda_schema_wave
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_schema_wave.zip .

cd $source_dir/backend/lambda_server_item
pip install -r ./requirements.txt -t .
cp $source_dir/backend/policy/policy.py ./
zip -r $build_dist_dir/lambda_server_item.zip .

cd $source_dir/backend/lambda_servers
pip install -r ./requirements.txt -t .
cp $source_dir/backend/policy/policy.py ./
zip -r $build_dist_dir/lambda_servers.zip .

cd $source_dir/backend/lambda_service_account
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_service_account.zip .

cd $source_dir/backend/lambda_stage
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_stage.zip .

cd $source_dir/backend/lambda_stage_attr
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_stage_attr.zip .

cd $source_dir/backend/lambda_wave_item
pip install -r ./requirements.txt -t .
cp $source_dir/backend/policy/policy.py ./
zip -r $build_dist_dir/lambda_wave_item.zip .

cd $source_dir/backend/lambda_waves
pip install -r ./requirements.txt -t .
cp $source_dir/backend/policy/policy.py ./
zip -r $build_dist_dir/lambda_waves.zip .

cd $source_dir/backend/lambda_app_item
pip install -r ./requirements.txt -t .
cp $source_dir/backend/policy/policy.py ./
zip -r $build_dist_dir/lambda_app_item.zip .

cd $source_dir/Tools\ Integration/CE-Integration/Lambdas/
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_cloudendure.zip .

cd $source_dir/Tools\ Integration/MGN-Integration/Lambdas/
pip install -r ./requirements.txt -t .
zip -r $build_dist_dir/lambda_mgn.zip .

echo "------------------------------------------------------------------------------"
echo "[Packing] Tools Integration Scripts"
echo "------------------------------------------------------------------------------"

cd $source_dir/Tools\ Integration/MGN-Integration/
zip -r $template_dist_dir/automation-scripts-mgn.zip ./MGN-automation-scripts

cd $source_dir/Tools\ Integration/CE-Integration/
zip -r $template_dist_dir/automation-scripts-ce.zip ./CE-automation-scripts

echo "------------------------------------------------------------------------------"
echo "[Packing] Migration Tracker Glue Scripts"
echo "------------------------------------------------------------------------------"

cd $source_dir/Tools\ Integration/
cp ./migration-tracker/GlueScript/Migration_Tracker_App_Extract_Script.py $build_dist_dir/Migration_Tracker_App_Extract_Script.py
cp ./migration-tracker/GlueScript/Migration_Tracker_Server_Extract_Script.py $build_dist_dir/Migration_Tracker_Server_Extract_Script.py

cd $source_dir
zip -r "$build_dist_dir/fe-$3.zip" ./frontend
