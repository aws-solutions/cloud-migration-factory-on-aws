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
cp $template_dir/*.template $template_dist_dir/
echo "copy yaml templates and rename"
cp $template_dir/*.yaml $template_dist_dir/
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

echo "------------------------------------------------------------------------------"
echo "[Packing] Lambda functions"
echo "------------------------------------------------------------------------------"
cd $source_dir
cp ./deployment-packages/lambda_ams_wig.zip $build_dist_dir/lambda_ams_wig.zip
cp ./deployment-packages/lambda_app_item.zip $build_dist_dir/lambda_app_item.zip
cp ./deployment-packages/lambda_apps.zip $build_dist_dir/lambda_apps.zip
cp ./deployment-packages/lambda_auth.zip $build_dist_dir/lambda_auth.zip
cp ./deployment-packages/lambda_build.zip $build_dist_dir/lambda_build.zip
cp ./deployment-packages/lambda_cloudendure.zip $build_dist_dir/lambda_cloudendure.zip
cp ./deployment-packages/lambda_cognitogroups.zip $build_dist_dir/lambda_cognitogroups.zip
cp ./deployment-packages/lambda_defaultschema_packaged.zip $build_dist_dir/lambda_defaultschema_packaged.zip
cp ./deployment-packages/lambda_login.zip $build_dist_dir/lambda_login.zip
cp ./deployment-packages/lambda_reset.zip $build_dist_dir/lambda_reset.zip
cp ./deployment-packages/lambda_role.zip $build_dist_dir/lambda_role.zip
cp ./deployment-packages/lambda_role_item.zip $build_dist_dir/lambda_role_item.zip
cp ./deployment-packages/lambda_schema_app.zip $build_dist_dir/lambda_schema_app.zip
cp ./deployment-packages/lambda_schema_server.zip $build_dist_dir/lambda_schema_server.zip
cp ./deployment-packages/lambda_server_item.zip $build_dist_dir/lambda_server_item.zip
cp ./deployment-packages/lambda_servers.zip $build_dist_dir/lambda_servers.zip
cp ./deployment-packages/lambda_stage.zip $build_dist_dir/lambda_stage.zip
cp ./deployment-packages/lambda_stage_attr.zip $build_dist_dir/lambda_stage_attr.zip
cp ./deployment-packages/lambda_wave_item.zip $build_dist_dir/lambda_wave_item.zip
cp ./deployment-packages/lambda_waves.zip $build_dist_dir/lambda_waves.zip
cp ./deployment-packages/v1.3.zip $build_dist_dir/v1.3.zip
cp ./deployment-packages/helper.zip $build_dist_dir/helper.zip

