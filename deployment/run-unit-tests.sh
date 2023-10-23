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
# ./run-unit-tests.sh
#

# Get reference for all important folders
template_dir="$PWD"
source_dir="$template_dir/../source"

echo "------------------------------------------------------------------------------"
echo "[Frontend] Preparing for Unit Testing"
echo "------------------------------------------------------------------------------"

cd $source_dir/frontend/
echo "  ---- NPM version"
npm --version

echo "  ---- Installing NPM Dependencies"
npm install
npm install jest --global

echo "  ---- Running NPM audit"
npm audit

npm run test -- --watchAll=false
echo "------------------------------------------------------------------------------"
echo "[Unit Tests] Running Frontend Unit Tests"
echo "------------------------------------------------------------------------------"

jest
if [ $? -eq 0 ]
  then
    echo "  ---- SUCCESS: Frontend Unit tests passed."
  else
    echo "  ---- FAILURE: Frontend Unit tests failed."
    exit 1
fi

echo "------------------------------------------------------------------------------"
echo "[Unit Tests] Frontend Unit Tests Complete"
echo "------------------------------------------------------------------------------"

echo "------------------------------------------------------------------------------"
echo "[Unit Tests] Running Backend Unit Tests"
echo "------------------------------------------------------------------------------"

cd $template_dir/../
chmod +x $template_dir/run_lambda_unit_test.sh
$template_dir/run_lambda_unit_test.sh
if [ $? -eq 0 ]
  then
    echo "  ---- SUCCESS: Backend Unit tests passed."
  else
    echo "  ---- FAILURE: Backend Unit tests failed."
    exit 1
fi

echo "------------------------------------------------------------------------------"
echo "[Unit Tests] Running Integrations Unit Tests"
echo "------------------------------------------------------------------------------"

cd $template_dir/../
chmod +x $template_dir/run_integration_unit_tests.sh
$template_dir/run_integration_unit_tests.sh
if [ $? -eq 0 ]
  then
    echo "  ---- SUCCESS: Integration Unit tests passed."
  else
    echo "  ---- FAILURE: Integration Unit tests failed."
    exit 1
fi
