#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#

#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name solution-name version-code
#
# Parameters:
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda
#    code from. The template will append '-[region_name]' to this bucket name.
#    For example: ./build-s3-dist.sh solutions my-solution v1.0.0
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
#
#  - solution-name: name of the solution for consistency
#
#  - version-code: version of the package

start_time=$SECONDS

# Check to see if input has been provided:

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"
    exit 1
fi

echo "Build number: $CODEBUILD_BUILD_NUMBER Build Type: $ENV"

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
echo "Updating code source bucket in templates with $1"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template
echo "Updating solution name in templates with $2"
replace="s/%%SOLUTION_NAME%%/$2/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template
echo "Updating solution id in templates with SO0097"
replace="s/%%SOLUTION_ID%%/SO0097/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template

# set version to default for prod build.
if [ -z "$ENV" ] || [ -z "$CODEBUILD_BUILD_NUMBER" ] ; then
  cemf_version=$3
else
  # Append build and environment to deployment.
  echo "Updating version for non-prod build to: $3-$CODEBUILD_BUILD_NUMBER-$ENV"
  cemf_version="$3-$CODEBUILD_BUILD_NUMBER-$ENV"
  export VERSION="$3-$CODEBUILD_BUILD_NUMBER-$ENV"
fi

replace="s/%%VERSION%%/$cemf_version/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template

echo "------------------------------------------------------------------------------"
echo "[Packing] Core Lambda functions"
echo "------------------------------------------------------------------------------"

cd $source_dir/backend/lambda_functions/
for d in */ ; do
    echo "$d"
    cd $source_dir/backend/lambda_functions/$d
    mkdir ./.build
    cp -r ./[!.]* ./.build
    cd ./.build
    pip install -r ./requirements.txt -t . --implementation cp --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --only-binary=:all:
    d1=${d%?}
    zip -r $build_dist_dir/$d1.zip ./
    cd ..
    rm -rf ./.build
done

echo "------------------------------------------------------------------------------"
echo "[Packing] Lambda function Layers"
echo "------------------------------------------------------------------------------"

cd $source_dir/backend/lambda_layers/
for d in */ ; do
    echo "$d"
    cd $source_dir/backend/lambda_layers/$d
    mkdir ./.build
    cp -r ./[!.]* ./.build
    cd $source_dir/backend/lambda_layers/$d/.build/python
    pip install -r ./requirements.txt -t ./lib/python3.11/site-packages/ --implementation cp --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --only-binary=:all:
    cd ../
    d1=${d%?}
    zip -r $build_dist_dir/$d1.zip .
    cd $source_dir/backend/lambda_layers/$d
    rm -rf ./.build
done

echo "------------------------------------------------------------------------------"
echo "[Packing] Integration Lambda functions"
echo "------------------------------------------------------------------------------"

cd $source_dir/integrations/
for d in */ ; do
    echo "$d"
    cd $source_dir/integrations/$d/lambdas
    mkdir ./.build
    cp -r ./[!.]* ./.build
    cp $source_dir/integrations/common/* ./.build
    cd ./.build
    pip install -r ./requirements.txt -t . --implementation cp --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --only-binary=:all:
    d1=${d%?}
    zip -r $build_dist_dir/lambda_$d1.zip .
    cd ..
    rm -rf ./.build
done

echo "------------------------------------------------------------------------------"
echo "[Packing] MGN Integration Automation Scripts"
echo "------------------------------------------------------------------------------"

cd $source_dir/integrations/mgn/MGN-automation-scripts/
for d in */ ; do
    echo "$d"
    cd $source_dir/integrations/mgn/MGN-automation-scripts/$d
    cp $source_dir/integrations/common/* ./
    d1=${d%?}
    zip -r $build_dist_dir/script_mgn_$d1.zip .
    # Clean-up duplicated common libraries to reduce duplicate code reports in SonarQube
    rm -f ./mfcommon.py
    rm -f ./cmf_logger.py
    rm -f ./cmf_user_login.py
    rm -f ./cmf_get_credentials.py
    rm -f ./cmf_get_servers.py
done

cd $build_dist_dir/
zip -r $build_dist_dir/default_scripts.zip script_*.zip

echo "------------------------------------------------------------------------------"
echo "[Packing] Other Automation Scripts"
echo "------------------------------------------------------------------------------"

cd $source_dir/integrations/automation_packages/
for d in */ ; do
    echo "$d"
    cd $source_dir/integrations/automation_packages/$d
    for p in */ ; do
      cd $source_dir/integrations/automation_packages/$d/$p
      cp $source_dir/integrations/common/* ./
      p1=${p%?}
      zip -r $build_dist_dir/script_$d_$p1.zip .
          # Clean-up duplicated common libraries to reduce duplicate code reports in SonarQube
      rm -f ./mfcommon.py
      rm -f ./cmf_logger.py
      rm -f ./cmf_user_login.py
      rm -f ./cmf_get_credentials.py
      rm -f ./cmf_get_servers.py
    done
done

cd $build_dist_dir/
zip -r $build_dist_dir/default_scripts.zip script_*.zip
echo "Copying default_scripts.zip to the templates directory"
cp $build_dist_dir/default_scripts.zip $template_dist_dir

echo "------------------------------------------------------------------------------"
echo "[Packing] Migration Tracker Glue Scripts"
echo "------------------------------------------------------------------------------"

cd $source_dir/integrations/
cp ./migration-tracker/GlueScript/Migration_Tracker_App_Extract_Script.py $build_dist_dir/Migration_Tracker_App_Extract_Script.py
cp ./migration-tracker/GlueScript/Migration_Tracker_Server_Extract_Script.py $build_dist_dir/Migration_Tracker_Server_Extract_Script.py
cp ./migration-tracker/GlueScript/Migration_Tracker_Database_Extract_Script.py $build_dist_dir/Migration_Tracker_Database_Extract_Script.py
cp ./migration-tracker/GlueScript/Migration_Tracker_Wave_Extract_Script.py $build_dist_dir/Migration_Tracker_Wave_Extract_Script.py

#echo "------------------------------------------------------------------------------"
#echo "[Frontend] Preparing for Unit Testing"
#echo "------------------------------------------------------------------------------"
#
#cd $source_dir/frontend/
#echo "  ---- NPM version"
#npm --version
#
#echo "  ---- Installing NPM Dependencies"
#npm install
#npm install jest --global
#
#echo "  ---- Running NPM audit"
#npm audit
#
#echo "------------------------------------------------------------------------------"
#echo "[Unit Tests] Running Frontend Unit Tests"
#echo "------------------------------------------------------------------------------"
#
#npm run test:coverage
#if [ $? -eq 0 ]
#  then
#    echo "  ---- SUCCESS: Frontend Unit tests passed."
#  else
#    echo "  ---- FAILURE: Frontend Unit tests failed."
#    exit 1
#fi
#
#echo "------------------------------------------------------------------------------"
#echo "[Unit Tests] Frontend Unit Tests Complete"
#echo "------------------------------------------------------------------------------"
#
#echo "------------------------------------------------------------------------------"
#echo "[Unit Tests] Running Backend Unit Tests"
#echo "------------------------------------------------------------------------------"
#
#cd $template_dir/../
#chmod +x $template_dir/run_lambda_unit_test.sh
#$template_dir/run_lambda_unit_test.sh
#if [ $? -eq 0 ]
#  then
#    echo "  ---- SUCCESS: Backend Unit tests passed."
#  else
#    echo "  ---- FAILURE: Backend Unit tests failed."
#    exit 1
#fi

echo "------------------------------------------------------------------------------"
echo "[Packing] Frontend build"
echo "------------------------------------------------------------------------------"

cd $source_dir/frontend/
echo "  ---- Building React Production Application"
npm run build
if [ $? -eq 0 ]
  then
    echo "  ---- SUCCESS: Frontend build complete."
  else
    echo "  ---- FAILURE: Frontend build failed."
    exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
  security_expiry_date=$(date -v+1y +%Y-%m-%dT%H:%M:%Sz)
else
  security_expiry_date=$(date +%Y-%m-%dT%H:%M:%Sz -d +1year)
fi

# cd into /frontend/dist and zip contents. error out if /dist doesnt exist
if [ ! -d "./dist/" ]; then
    echo "Error: ./dist/ directory does not exist."
    exit 1  # Exit with a non-zero exit code to indicate an error
fi
cd ./dist/

echo "Updating security.txt expiry date to $security_expiry_date"
replace="s#%%SECURITY_EXPIRY_DATE%%#$security_expiry_date#g"
security_txt_path="./.well-known/security.txt"
echo "security.txt path: $security_txt_path"
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -e $replace $security_txt_path
else
  sed -i -e $replace $security_txt_path
fi

echo "  ---- Packaging React Production Application"
zip -r "$build_dist_dir/fe-$cemf_version.zip" .

elapsed=$(( SECONDS - start_time ))
echo "Elapsed build time : $elapsed seconds"