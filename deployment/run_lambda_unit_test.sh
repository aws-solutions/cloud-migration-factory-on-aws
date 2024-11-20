#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#

# This script must be executed from the package root directory
#
# To run unittests against a subset of the tests for development testing,
# the script accepts a single optional argument, this is string pattern
# for the tests required to be run i.e. test_lambda_ssm*
# If not provided all tests will be run.

set -e

if [ ! -d "testing-venv" ]; then
    echo "Creating testing-venv..."
    python3 -m venv testing-venv
fi


echo "  ---- Rebuilding package locally before testing..."
source testing-venv/bin/activate
echo "  ---- Using python: `type python3`"
echo "  ---- Python version: `python3 --version`"
echo "  ---- Installing pip"
pip3 install --quiet -U pip
echo "  ---- Installing dependency"
source_code="$PWD"
echo "  ---- Changing working directory to the test directory"
cd source/backend/lambda_unit_test/
"$POETRY_HOME"/bin/poetry install
echo "Updating source path $source_code"
replace="s#%%SOURCE_PATH%%#$source_code#g"
tox_path="$PWD/tox.ini"
echo "tox.ini path: $tox_path"
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -e $replace $tox_path
else
  sed -i -e $replace $tox_path
fi

if [ -z "$1" ]; then
  echo "  ---- Running all tests..."
  test_scope=discover
else
  echo "  ---- Running tests based on the pattern $1..."
  test_scope=$1
fi
coverage run --data-file=./coverage/.coverage -m unittest $test_scope
echo "  ---- Please make sure all the test cases above pass"
echo
echo
echo "  ---- Unit test Coverage report"
coverage report --data-file=./coverage/.coverage
coverage xml --data-file=./coverage/.coverage -o./coverage/coverage.xml
deactivate
echo "Removing source path $source_code"
replace="s#$source_code#%%SOURCE_PATH%%#g"
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -e $replace $tox_path
else
  sed -i -e $replace $tox_path
fi

echo "------------------------------------------------------------------------------"
echo "[Unit Tests] Backend Unit Tests Complete"
echo "------------------------------------------------------------------------------"